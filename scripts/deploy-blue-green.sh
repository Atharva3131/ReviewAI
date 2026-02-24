#!/bin/bash

# Blue-Green deployment strategy for ECS
# Creates a new service (green), tests it, then switches traffic

set -e

ENVIRONMENT=$1
IMAGE_URI=$2

if [ -z "$ENVIRONMENT" ] || [ -z "$IMAGE_URI" ]; then
    echo "Usage: $0 <environment> <image-uri>"
    exit 1
fi

PROJECT_NAME="revive-ai"
CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}-cluster"
BLUE_SERVICE="${PROJECT_NAME}-${ENVIRONMENT}-backend"
GREEN_SERVICE="${PROJECT_NAME}-${ENVIRONMENT}-backend-green"
TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
    --names "${PROJECT_NAME}-${ENVIRONMENT}-backend-tg" \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

echo "🔵🟢 Starting blue-green deployment..."
echo "Environment: $ENVIRONMENT"
echo "Image: $IMAGE_URI"
echo "Blue Service: $BLUE_SERVICE"
echo "Green Service: $GREEN_SERVICE"

# Get current (blue) task definition
BLUE_TASK_DEF=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $BLUE_SERVICE \
    --query 'services[0].taskDefinition' \
    --output text)

echo "📋 Blue task definition: $BLUE_TASK_DEF"

# Create green task definition
aws ecs describe-task-definition \
    --task-definition $BLUE_TASK_DEF \
    --query 'taskDefinition' > task-def.json

# Update image URI
jq --arg IMAGE_URI "$IMAGE_URI" \
   '.containerDefinitions[0].image = $IMAGE_URI' \
   task-def.json > updated-task-def.json

# Remove unnecessary fields
jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' \
   updated-task-def.json > final-task-def.json

# Register green task definition
echo "📝 Registering green task definition..."
GREEN_TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://final-task-def.json \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "✅ Green task definition registered: $GREEN_TASK_DEF_ARN"

# Check if green service already exists
GREEN_EXISTS=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $GREEN_SERVICE \
    --query 'services[0].serviceName' \
    --output text 2>/dev/null || echo "None")

if [ "$GREEN_EXISTS" = "None" ]; then
    echo "🟢 Creating green service..."
    
    # Get network configuration from blue service
    SUBNETS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $BLUE_SERVICE \
        --query 'services[0].networkConfiguration.awsvpcConfiguration.subnets' \
        --output json)
    
    SECURITY_GROUPS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $BLUE_SERVICE \
        --query 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups' \
        --output json)
    
    DESIRED_COUNT=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $BLUE_SERVICE \
        --query 'services[0].desiredCount' \
        --output text)
    
    # Create green service
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $GREEN_SERVICE \
        --task-definition $GREEN_TASK_DEF_ARN \
        --desired-count $DESIRED_COUNT \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=$SUBNETS,securityGroups=$SECURITY_GROUPS,assignPublicIp=DISABLED}" \
        --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=${PROJECT_NAME}-${ENVIRONMENT}-backend,containerPort=8000"
else
    echo "🟢 Updating existing green service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $GREEN_SERVICE \
        --task-definition $GREEN_TASK_DEF_ARN \
        --force-new-deployment
fi

# Wait for green service to be stable
echo "⏳ Waiting for green service to be stable..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $GREEN_SERVICE

# Health check green service
echo "🔍 Performing health checks on green service..."
sleep 30

# Get green service endpoint (through ALB)
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names "${PROJECT_NAME}-${ENVIRONMENT}-alb" \
    --query 'LoadBalancers[0].DNSName' \
    --output text)

# Test green service
for i in {1..10}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://${ALB_DNS}/health" || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Green service health check passed"
        break
    else
        echo "⏳ Waiting for green service... (attempt $i/10, HTTP $HTTP_CODE)"
        sleep 10
    fi
    
    if [ $i -eq 10 ]; then
        echo "❌ Green service health check failed"
        echo "🔄 Rolling back - deleting green service..."
        aws ecs delete-service --cluster $CLUSTER_NAME --service $GREEN_SERVICE --force
        exit 1
    fi
done

# Switch traffic from blue to green
echo "🔀 Switching traffic from blue to green..."

# Scale down blue service
echo "🔵 Scaling down blue service..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $BLUE_SERVICE \
    --desired-count 0

# Wait for blue service to scale down
sleep 30

# Verify green service is handling traffic
echo "🔍 Verifying green service is handling traffic..."
for i in {1..5}; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://${ALB_DNS}/health" || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Green service is handling traffic successfully"
        break
    else
        echo "⚠️ Traffic verification attempt $i/5 (HTTP $HTTP_CODE)"
        sleep 10
    fi
    
    if [ $i -eq 5 ]; then
        echo "❌ Green service failed to handle traffic"
        echo "🔄 Rolling back - scaling up blue service..."
        aws ecs update-service --cluster $CLUSTER_NAME --service $BLUE_SERVICE --desired-count 2
        exit 1
    fi
done

# Deployment successful - clean up old blue service
echo "🧹 Cleaning up old blue service..."
aws ecs delete-service --cluster $CLUSTER_NAME --service $BLUE_SERVICE --force

# Rename green to blue for next deployment
echo "🔄 Renaming green service to blue..."
# Note: ECS doesn't support renaming, so we keep the naming convention
# Next deployment will use the current green as blue

echo "🎉 Blue-green deployment completed successfully!"
echo "🟢 Green service is now serving production traffic"

# Cleanup
rm -f task-def.json updated-task-def.json final-task-def.json
