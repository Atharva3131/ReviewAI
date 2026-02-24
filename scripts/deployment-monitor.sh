#!/bin/bash

# Deployment monitoring script
# Monitors deployment health and triggers rollback if needed

set -e

ENVIRONMENT=$1
DEPLOYMENT_ID=$2
MONITORING_DURATION=${3:-600}  # Default 10 minutes

if [ -z "$ENVIRONMENT" ] || [ -z "$DEPLOYMENT_ID" ]; then
    echo "Usage: $0 <environment> <deployment-id> [monitoring-duration-seconds]"
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

# Metrics thresholds
ERROR_RATE_THRESHOLD=5  # 5% error rate
RESPONSE_TIME_THRESHOLD=2000  # 2 seconds
CPU_THRESHOLD=80  # 80% CPU
MEMORY_THRESHOLD=80  # 80% memory

log_info "Starting deployment monitoring for $DEPLOYMENT_ID"
log_info "Environment: $ENVIRONMENT"
log_info "Monitoring duration: ${MONITORING_DURATION}s"

START_TIME=$(date +%s)
END_TIME=$((START_TIME + MONITORING_DURATION))
CHECK_INTERVAL=30

HEALTH_CHECK_FAILURES=0
MAX_FAILURES=3

while [ $(date +%s) -lt $END_TIME ]; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    REMAINING=$((END_TIME - CURRENT_TIME))
    
    log_info "Monitoring progress: ${ELAPSED}s elapsed, ${REMAINING}s remaining"
    
    # Check ECS service health
    log_info "Checking ECS service health..."
    
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
    
    DEPLOYMENT_STATUS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --query 'services[0].deployments[?status==`PRIMARY`].rolloutState' \
        --output text)
    
    log_info "Tasks: $RUNNING_COUNT/$DESIRED_COUNT | Status: $DEPLOYMENT_STATUS"
    
    if [ "$RUNNING_COUNT" != "$DESIRED_COUNT" ]; then
        log_warning "Running count doesn't match desired count"
        HEALTH_CHECK_FAILURES=$((HEALTH_CHECK_FAILURES + 1))
    else
        log_success "All tasks are running"
        HEALTH_CHECK_FAILURES=0
    fi
    
    # Check deployment status
    if [ "$DEPLOYMENT_STATUS" = "FAILED" ]; then
        log_error "Deployment has failed"
        exit 1
    fi
    
    # Check application health endpoint
    log_info "Checking application health endpoint..."
    
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names "${PROJECT_NAME}-${ENVIRONMENT}-alb" \
        --query 'LoadBalancers[0].DNSName' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$ALB_DNS" ]; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://${ALB_DNS}/health" || echo "000")
        
        if [ "$HTTP_CODE" = "200" ]; then
            log_success "Health endpoint returned 200"
        else
            log_warning "Health endpoint returned $HTTP_CODE"
            HEALTH_CHECK_FAILURES=$((HEALTH_CHECK_FAILURES + 1))
        fi
    fi
    
    # Check CloudWatch metrics
    log_info "Checking CloudWatch metrics..."
    
    # Get CPU utilization
    CPU_UTILIZATION=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/ECS \
        --metric-name CPUUtilization \
        --dimensions Name=ServiceName,Value=$SERVICE_NAME Name=ClusterName,Value=$CLUSTER_NAME \
        --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
        --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
        --period 300 \
        --statistics Average \
        --query 'Datapoints[0].Average' \
        --output text 2>/dev/null || echo "0")
    
    if [ "$CPU_UTILIZATION" != "None" ] && [ "$CPU_UTILIZATION" != "0" ]; then
        CPU_INT=$(printf "%.0f" "$CPU_UTILIZATION")
        log_info "CPU Utilization: ${CPU_INT}%"
        
        if [ "$CPU_INT" -gt "$CPU_THRESHOLD" ]; then
            log_warning "CPU utilization above threshold (${CPU_INT}% > ${CPU_THRESHOLD}%)"
            HEALTH_CHECK_FAILURES=$((HEALTH_CHECK_FAILURES + 1))
        fi
    fi
    
    # Get memory utilization
    MEMORY_UTILIZATION=$(aws cloudwatch get-metric-statistics \
        --namespace AWS/ECS \
        --metric-name MemoryUtilization \
        --dimensions Name=ServiceName,Value=$SERVICE_NAME Name=ClusterName,Value=$CLUSTER_NAME \
        --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
        --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
        --period 300 \
        --statistics Average \
        --query 'Datapoints[0].Average' \
        --output text 2>/dev/null || echo "0")
    
    if [ "$MEMORY_UTILIZATION" != "None" ] && [ "$MEMORY_UTILIZATION" != "0" ]; then
        MEMORY_INT=$(printf "%.0f" "$MEMORY_UTILIZATION")
        log_info "Memory Utilization: ${MEMORY_INT}%"
        
        if [ "$MEMORY_INT" -gt "$MEMORY_THRESHOLD" ]; then
            log_warning "Memory utilization above threshold (${MEMORY_INT}% > ${MEMORY_THRESHOLD}%)"
            HEALTH_CHECK_FAILURES=$((HEALTH_CHECK_FAILURES + 1))
        fi
    fi
    
    # Check for errors in logs
    log_info "Checking application logs for errors..."
    
    LOG_GROUP="/ecs/${PROJECT_NAME}-${ENVIRONMENT}-backend"
    ERROR_COUNT=$(aws logs filter-log-events \
        --log-group-name $LOG_GROUP \
        --start-time $(($(date +%s) - 300))000 \
        --filter-pattern "ERROR" \
        --query 'length(events)' \
        --output text 2>/dev/null || echo "0")
    
    log_info "Error count in last 5 minutes: $ERROR_COUNT"
    
    if [ "$ERROR_COUNT" -gt 10 ]; then
        log_warning "High error count detected: $ERROR_COUNT"
        HEALTH_CHECK_FAILURES=$((HEALTH_CHECK_FAILURES + 1))
    fi
    
    # Check if we've exceeded failure threshold
    if [ $HEALTH_CHECK_FAILURES -ge $MAX_FAILURES ]; then
        log_error "Health check failures exceeded threshold ($HEALTH_CHECK_FAILURES >= $MAX_FAILURES)"
        log_error "Deployment is unhealthy - rollback recommended"
        exit 1
    fi
    
    # Wait before next check
    sleep $CHECK_INTERVAL
done

log_success "Monitoring completed successfully"
log_success "Deployment $DEPLOYMENT_ID is healthy"
exit 0
