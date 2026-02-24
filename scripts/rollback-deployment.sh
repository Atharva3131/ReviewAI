#!/bin/bash

# Automated rollback script
# Rolls back to previous stable deployment

set -e

ENVIRONMENT=$1
REASON=${2:-"Manual rollback"}

if [ -z "$ENVIRONMENT" ]; then
    echo "Usage: $0 <environment> [reason]"
    exit 1
fi

PROJECT_NAME="revive-ai"
CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}-cluster"
SERVICE_NAME="${PROJECT_NAME}-${ENVIRONMENT}-backend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning "🔄 Initiating rollback for $ENVIRONMENT environment"
log_info "Reason: $REASON"

# Get current deployment information
log_info "Gathering current deployment information..."

CURRENT_TASK_DEF=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --query 'services[0].taskDefinition' \
    --output text)

log_info "Current task definition: $CURRENT_TASK_DEF"

# Get task definition history
log_info "Retrieving task definition history..."

TASK_DEF_FAMILY=$(echo $CURRENT_TASK_DEF | cut -d':' -f6 | cut -d'/' -f2)
CURRENT_REVISION=$(echo $CURRENT_TASK_DEF | cut -d':' -f7)

log_info "Task definition family: $TASK_DEF_FAMILY"
log_info "Current revision: $CURRENT_REVISION"

# Calculate previous revision
PREVIOUS_REVISION=$((CURRENT_REVISION - 1))

if [ $PREVIOUS_REVISION -lt 1 ]; then
    log_error "No previous revision available for rollback"
    exit 1
fi

PREVIOUS_TASK_DEF="${TASK_DEF_FAMILY}:${PREVIOUS_REVISION}"

log_info "Previous task definition: $PREVIOUS_TASK_DEF"

# Verify previous task definition exists
TASK_DEF_EXISTS=$(aws ecs describe-task-definition \
    --task-definition $PREVIOUS_TASK_DEF \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text 2>/dev/null || echo "None")

if [ "$TASK_DEF_EXISTS" = "None" ]; then
    log_error "Previous task definition not found: $PREVIOUS_TASK_DEF"
    exit 1
fi

log_success "Previous task definition verified: $TASK_DEF_EXISTS"

# Create rollback snapshot
log_info "Creating rollback snapshot..."

cat > rollback-snapshot.json <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "$ENVIRONMENT",
  "reason": "$REASON",
  "from_task_definition": "$CURRENT_TASK_DEF",
  "to_task_definition": "$PREVIOUS_TASK_DEF",
  "cluster": "$CLUSTER_NAME",
  "service": "$SERVICE_NAME"
}
EOF

log_info "Rollback snapshot created"

# Confirm rollback
log_warning "⚠️  About to rollback from revision $CURRENT_REVISION to $PREVIOUS_REVISION"
log_warning "This will replace the current deployment with the previous version"

if [ -t 0 ]; then
    # Interactive mode
    read -p "Continue with rollback? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Rollback cancelled by user"
        exit 0
    fi
else
    # Non-interactive mode (CI/CD)
    log_info "Running in non-interactive mode - proceeding with rollback"
fi

# Perform rollback
log_info "🔄 Executing rollback..."

aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --task-definition $PREVIOUS_TASK_DEF \
    --force-new-deployment

log_success "Rollback initiated"

# Monitor rollback progress
log_info "⏳ Monitoring rollback progress..."

TIMEOUT=600  # 10 minutes
START_TIME=$(date +%s)

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    if [ $ELAPSED -gt $TIMEOUT ]; then
        log_error "Rollback timeout after ${TIMEOUT}s"
        exit 1
    fi
    
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
    
    log_info "Status: $DEPLOYMENT_STATUS | Tasks: $RUNNING_COUNT/$DESIRED_COUNT | Elapsed: ${ELAPSED}s"
    
    if [ "$DEPLOYMENT_STATUS" = "COMPLETED" ] && [ "$RUNNING_COUNT" = "$DESIRED_COUNT" ]; then
        log_success "Rollback completed successfully"
        break
    elif [ "$DEPLOYMENT_STATUS" = "FAILED" ]; then
        log_error "Rollback failed"
        exit 1
    fi
    
    sleep 15
done

# Wait for service stability
log_info "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME

# Verify rollback
log_info "🔍 Verifying rollback..."

FINAL_TASK_DEF=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --query 'services[0].taskDefinition' \
    --output text)

if [[ "$FINAL_TASK_DEF" == *"$PREVIOUS_REVISION"* ]]; then
    log_success "✅ Rollback verified - service is running revision $PREVIOUS_REVISION"
else
    log_error "❌ Rollback verification failed - unexpected task definition: $FINAL_TASK_DEF"
    exit 1
fi

# Health check
log_info "🔍 Performing health check..."

ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names "${PROJECT_NAME}-${ENVIRONMENT}-alb" \
    --query 'LoadBalancers[0].DNSName' \
    --output text 2>/dev/null || echo "")

if [ -n "$ALB_DNS" ]; then
    for i in {1..10}; do
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://${ALB_DNS}/health" || echo "000")
        
        if [ "$HTTP_CODE" = "200" ]; then
            log_success "✅ Health check passed"
            break
        else
            log_info "⏳ Waiting for health check... (attempt $i/10, HTTP $HTTP_CODE)"
            sleep 10
        fi
        
        if [ $i -eq 10 ]; then
            log_error "❌ Health check failed after rollback"
            exit 1
        fi
    done
fi

# Save rollback record
ROLLBACK_RECORD="rollback-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).json"
mv rollback-snapshot.json $ROLLBACK_RECORD

log_success "🎉 Rollback completed successfully!"
log_info "📝 Rollback record saved: $ROLLBACK_RECORD"
log_info "Service is now running revision $PREVIOUS_REVISION"

# Send notification (placeholder)
log_info "📧 Sending rollback notification..."
echo "Rollback completed for $ENVIRONMENT environment"
echo "From: $CURRENT_TASK_DEF"
echo "To: $PREVIOUS_TASK_DEF"
echo "Reason: $REASON"

exit 0
