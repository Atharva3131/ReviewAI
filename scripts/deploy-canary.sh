#!/bin/bash

# Canary deployment strategy for ECS
# Gradually shifts traffic to new version while monitoring metrics

set -e

ENVIRONMENT=$1
IMAGE_URI=$2
CANARY_PERCENTAGE=${3:-10}  # Default 10% canary traffic

if [ -z "$ENVIRONMENT" ] || [ -z "$IMAGE_URI" ]; then
    echo "Usage: $0 <environment> <image-uri> [canary-percentage]"
    exit 1
fi

PROJECT_NAME="revive-ai"
CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}-cluster"
PRIMARY_SERVICE="${PROJECT_NAME}-${ENVIRONMENT}-backend"
CANARY_SERVICE="${PROJECT_NAME}-${ENVIRONMENT}-backend-canary"

echo "🐤 Starting canary deployment..."
echo "Environment: $ENVIRONMENT"
echo "Image: $IMAGE_URI"
echo "Canary Traffic: ${CANARY_PERCENTAGE}%"

# Get current task definition
CURRENT_TASK_DEF=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $PRIMARY_SERVICE \
    --query 'services[0].taskDefinition' \
    --output text)

echo "📋 Current task definition: $CURRENT_TASK_DEF"

# Create new task definition for canary
aws ecs describe-task-definition \
    --task-definition $CURRENT_TASK_DEF \
    --query 'taskDefinition' > task-def.json

# Update image URI
jq --arg IMAGE_URI "$IMAGE_URI" \
   '.containerDefinitions[0].image = $IMAGE_URI' \
   task-def.json > updated-task-def.json

# Remove unnecessary fields
jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' \
   updated-task-def.json > final-task-def.json

# Register canary task definition
echo "📝 Registering canary task definition..."
CANARY_TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://final-task-def.json \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "✅ Canary task definition registered: $CANARY_TASK_DEF_ARN"

# Calculate canary task count
PRIMARY_COUNT=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $PRIMARY_SERVICE \
    --query 'services[0].desiredCount' \
    --output text)

CANARY_COUNT=$(echo "scale=0; $PRIMARY_COUNT * $CANARY_PERCENTAGE / 100" | bc)
if [ "$CANARY_COUNT" -lt 1 ]; then
    CANARY_COUNT=1
fi

echo "📊 Primary tasks: $PRIMARY_COUNT, Canary tasks: $CANARY_COUNT"

# Check if canary service exists
CANARY_EXISTS=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $CANARY_SERVICE \
    --query 'services[0].serviceName' \
    --output text 2>/dev/null || echo "None")

if [ "$CANARY_EXISTS" = "None" ]; then
    echo "🐤 Creating canary service..."
    
    # Get network configuration from primary service
    SUBNETS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $PRIMARY_SERVICE \
        --query 'services[0].networkConfiguration.awsvpcConfiguration.subnets' \
        --output json)
    
    SECURITY_GROUPS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $PRIMARY_SERVICE \
        --query 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups' \
        --output json)
    
    TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
        --names "${PROJECT_NAME}-${ENVIRONMENT}-backend-tg" \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)
    
    # Create canary service
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $CANARY_SERVICE \
        --task-definition $CANARY_TASK_DEF_ARN \
        --desired-count $CANARY_COUNT \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=$SUBNETS,securityGroups=$SECURITY_GROUPS,assignPublicIp=DISABLED}" \
        --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=${PROJECT_NAME}-${ENVIRONMENT}-backend,containerPort=8000"
else
    echo "🐤 Updating existing canary service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $CANARY_SERVICE \
        --task-definition $CANARY_TASK_DEF_ARN \
        --desired-count $CANARY_COUNT \
        --force-new-deployment
fi

# Wait for canary service to be stable
echo "⏳ Waiting for canary service to be stable..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $CANARY_SERVICE

# Monitor canary metrics
echo "📊 Monitoring canary metrics..."
MONITORING_DURATION=300  # 5 minutes
MONITORING_INTERVAL=30   # 30 seconds
ITERATIONS=$((MONITORING_DURATION / MONITORING_INTERVAL))

for i in $(seq 1 $ITERATIONS); do
    echo "⏳ Monitoring iteration $i/$ITERATIONS..."
    
    # Check canary service health
    CANARY_RUNNING=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $CANARY_SERVICE \
        --query 'services[0].runningCount' \
        --output text)
    
    CANARY_DESIRED=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $CANARY_SERVICE \
        --query 'services[0].desiredCount' \
        --output text)
    
    echo "Canary tasks: $CANARY_RUNNING/$CANARY_DESIRED"
    
    if [ "$CANARY_RUNNING" != "$CANARY_DESIRED" ]; then
        echo "❌ Canary service is unhealthy"
        echo "🔄 Rolling back canary deployment..."
        aws ecs update-service --cluster $CLUSTER_NAME --service $CANARY_SERVICE --desired-count 0
        aws ecs delete-service --cluster $CLUSTER_NAME --service $CANARY_SERVICE --force
        exit 1
    fi
    
    # Check error rates (would integrate with CloudWatch in production)
    # For now, just check if service is running
    
    sleep $MONITORING_INTERVAL
done

echo "✅ Canary monitoring completed - no issues detected"

# Promote canary to primary
echo "🚀 Promoting canary to primary..."

# Update primary service with canary task definition
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $PRIMARY_SERVICE \
    --task-definition $CANARY_TASK_DEF_ARN \
    --force-new-deployment

# Wait for primary service to update
echo "⏳ Waiting for primary service to update..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $PRIMARY_SERVICE

# Scale down and remove canary service
echo "🧹 Cleaning up canary service..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $CANARY_SERVICE \
    --desired-count 0

sleep 30

aws ecs delete-service \
    --cluster $CLUSTER_NAME \
    --service $CANARY_SERVICE \
    --force

echo "🎉 Canary deployment completed successfully!"
echo "✅ New version promoted to primary service"

# Cleanup
rm -f task-def.json updated-task-def.json final-task-def.json
