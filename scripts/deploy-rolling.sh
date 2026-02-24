#!/bin/bash

# Rolling deployment strategy for ECS
# Gradually replaces old tasks with new ones

set -e

ENVIRONMENT=$1
IMAGE_URI=$2

if [ -z "$ENVIRONMENT" ] || [ -z "$IMAGE_URI" ]; then
    echo "Usage: $0 <environment> <image-uri>"
    exit 1
fi

PROJECT_NAME="revive-ai"
CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}-cluster"
SERVICE_NAME="${PROJECT_NAME}-${ENVIRONMENT}-backend"

echo "🔄 Starting rolling deployment..."
echo "Environment: $ENVIRONMENT"
echo "Image: $IMAGE_URI"

# Get current task definition
CURRENT_TASK_DEF=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --query 'services[0].taskDefinition' \
    --output text)

echo "📋 Current task definition: $CURRENT_TASK_DEF"

# Describe current task definition
aws ecs describe-task-definition \
    --task-definition $CURRENT_TASK_DEF \
    --query 'taskDefinition' > task-def.json

# Update image URI in task definition
jq --arg IMAGE_URI "$IMAGE_URI" \
   '.containerDefinitions[0].image = $IMAGE_URI' \
   task-def.json > updated-task-def.json

# Remove unnecessary fields
jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' \
   updated-task-def.json > final-task-def.json

# Register new task definition
echo "📝 Registering new task definition..."
NEW_TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://final-task-def.json \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "✅ New task definition registered: $NEW_TASK_DEF_ARN"

# Update service with rolling deployment
echo "🚀 Updating ECS service..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --task-definition $NEW_TASK_DEF_ARN \
    --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100" \
    --force-new-deployment

# Monitor deployment progress
echo "⏳ Monitoring deployment progress..."
while true; do
    DEPLOYMENT_STATUS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --query 'services[0].deployments[?status==`PRIMARY`].rolloutState' \
        --output text)
    
    RUNNING_COUNT=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --query 'services[0].runningCount' \
        --output text)
    
    DESIRED_COUNT=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --query 'services[0].desiredCount' \
        --output text)
    
    echo "Status: $DEPLOYMENT_STATUS | Running: $RUNNING_COUNT/$DESIRED_COUNT"
    
    if [ "$DEPLOYMENT_STATUS" = "COMPLETED" ]; then
        echo "✅ Rolling deployment completed successfully"
        break
    elif [ "$DEPLOYMENT_STATUS" = "FAILED" ]; then
        echo "❌ Rolling deployment failed"
        exit 1
    fi
    
    sleep 15
done

# Wait for service stability
echo "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME

echo "🎉 Rolling deployment completed successfully!"

# Cleanup
rm -f task-def.json updated-task-def.json final-task-def.json
