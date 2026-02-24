#!/bin/bash

# Rollback Script for Revive AI Deployment
# This script provides comprehensive rollback capabilities for ECS deployments

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="${PROJECT_NAME:-revive-ai}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Rollback Revive AI deployment to a previous version.

OPTIONS:
    -e, --environment ENV       Target environment (staging|production) [required]
    -t, --target TARGET         Rollback target:
                                  - previous: Roll back to previous deployment (default)
                                  - version: Roll back to specific version
                                  - revision: Roll back to specific task definition revision
    -v, --version VERSION       Specific version to roll back to (required if target=version)
    -r, --revision REVISION     Specific task definition revision (required if target=revision)
    -c, --component COMPONENT   Component to rollback (backend|frontend|database|all) [default: all]
    -d, --dry-run              Perform a dry run without making changes
    -f, --force                Force rollback without confirmation
    -h, --help                 Display this help message

EXAMPLES:
    # Rollback production backend to previous version
    $0 -e production -c backend

    # Rollback staging to specific version
    $0 -e staging -t version -v v1.2.3

    # Rollback to specific task definition revision
    $0 -e production -t revision -r 42

    # Dry run for production rollback
    $0 -e production -d

    # Force rollback without confirmation
    $0 -e production -f

EOF
    exit 1
}

# Parse command line arguments
ENVIRONMENT=""
TARGET="previous"
VERSION=""
REVISION=""
COMPONENT="all"
DRY_RUN=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -r|--revision)
            REVISION="$2"
            shift 2
            ;;
        -c|--component)
            COMPONENT="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [ -z "$ENVIRONMENT" ]; then
    print_error "Environment is required"
    usage
fi

if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "production" ]; then
    print_error "Environment must be 'staging' or 'production'"
    exit 1
fi

if [ "$TARGET" = "version" ] && [ -z "$VERSION" ]; then
    print_error "Version is required when target is 'version'"
    exit 1
fi

if [ "$TARGET" = "revision" ] && [ -z "$REVISION" ]; then
    print_error "Revision is required when target is 'revision'"
    exit 1
fi

# Set cluster and service names
CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}-cluster"
SERVICE_NAME="${PROJECT_NAME}-${ENVIRONMENT}-backend"
TASK_FAMILY="${PROJECT_NAME}-${ENVIRONMENT}-backend"

print_info "=== Revive AI Rollback Script ==="
print_info "Environment: $ENVIRONMENT"
print_info "Target: $TARGET"
print_info "Component: $COMPONENT"
print_info "Dry Run: $DRY_RUN"
echo ""

# Function to check AWS CLI and credentials
check_aws_cli() {
    print_info "Checking AWS CLI..."
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials are not configured or invalid"
        exit 1
    fi
    
    print_success "AWS CLI configured"
}

# Function to get current deployment info
get_current_deployment() {
    print_info "Fetching current deployment information..."
    
    CURRENT_TASK_DEF=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text 2>/dev/null)
    
    if [ -z "$CURRENT_TASK_DEF" ] || [ "$CURRENT_TASK_DEF" = "None" ]; then
        print_error "Could not fetch current task definition"
        exit 1
    fi
    
    CURRENT_REVISION=$(echo "$CURRENT_TASK_DEF" | grep -oP ':\K[0-9]+$')
    
    print_success "Current task definition: $CURRENT_TASK_DEF (revision $CURRENT_REVISION)"
}

# Function to determine rollback target
determine_rollback_target() {
    print_info "Determining rollback target..."
    
    case $TARGET in
        previous)
            # Get previous task definition revision
            if [ "$CURRENT_REVISION" -le 1 ]; then
                print_error "No previous revision available (current is revision 1)"
                exit 1
            fi
            
            TARGET_REVISION=$((CURRENT_REVISION - 1))
            TARGET_TASK_DEF="${TASK_FAMILY}:${TARGET_REVISION}"
            ;;
        
        version)
            # Find task definition by version tag
            print_info "Searching for version $VERSION..."
            
            # List task definitions and find the one with matching version
            TARGET_TASK_DEF=$(aws ecs list-task-definitions \
                --family-prefix "$TASK_FAMILY" \
                --region "$AWS_REGION" \
                --query "taskDefinitionArns[-10:]" \
                --output text | tr '\t' '\n' | while read -r task_def; do
                    # Check if this task definition has the version tag
                    TAGS=$(aws ecs list-tags-for-resource \
                        --resource-arn "$task_def" \
                        --region "$AWS_REGION" \
                        --query "tags[?key=='version'].value" \
                        --output text 2>/dev/null)
                    
                    if [ "$TAGS" = "$VERSION" ]; then
                        echo "$task_def"
                        break
                    fi
                done)
            
            if [ -z "$TARGET_TASK_DEF" ]; then
                print_error "Could not find task definition for version $VERSION"
                exit 1
            fi
            
            TARGET_REVISION=$(echo "$TARGET_TASK_DEF" | grep -oP ':\K[0-9]+$')
            ;;
        
        revision)
            TARGET_REVISION="$REVISION"
            TARGET_TASK_DEF="${TASK_FAMILY}:${TARGET_REVISION}"
            
            # Verify the revision exists
            if ! aws ecs describe-task-definition \
                --task-definition "$TARGET_TASK_DEF" \
                --region "$AWS_REGION" &> /dev/null; then
                print_error "Task definition revision $TARGET_REVISION does not exist"
                exit 1
            fi
            ;;
        
        *)
            print_error "Invalid target: $TARGET"
            exit 1
            ;;
    esac
    
    print_success "Rollback target: $TARGET_TASK_DEF (revision $TARGET_REVISION)"
}

# Function to get task definition details
get_task_definition_details() {
    local task_def=$1
    
    aws ecs describe-task-definition \
        --task-definition "$task_def" \
        --region "$AWS_REGION" \
        --query 'taskDefinition.{Image:containerDefinitions[0].image,CreatedAt:registeredAt}' \
        --output json
}

# Function to display rollback plan
display_rollback_plan() {
    print_info "=== Rollback Plan ==="
    echo ""
    
    print_info "Current Deployment:"
    CURRENT_DETAILS=$(get_task_definition_details "$CURRENT_TASK_DEF")
    echo "$CURRENT_DETAILS" | jq -r '"  Task Definition: \(.)"'
    echo ""
    
    print_info "Target Deployment:"
    TARGET_DETAILS=$(get_task_definition_details "$TARGET_TASK_DEF")
    echo "$TARGET_DETAILS" | jq -r '"  Task Definition: \(.)"'
    echo ""
    
    print_warning "This will:"
    echo "  1. Update ECS service to use task definition: $TARGET_TASK_DEF"
    echo "  2. Force a new deployment"
    echo "  3. Wait for service to stabilize"
    
    if [ "$COMPONENT" = "all" ] || [ "$COMPONENT" = "database" ]; then
        echo "  4. Rollback database migrations (if applicable)"
    fi
    
    if [ "$COMPONENT" = "all" ] || [ "$COMPONENT" = "frontend" ]; then
        echo "  5. Rollback frontend deployment"
    fi
    
    echo ""
}

# Function to confirm rollback
confirm_rollback() {
    if [ "$FORCE" = true ]; then
        print_warning "Force flag set - skipping confirmation"
        return 0
    fi
    
    if [ "$DRY_RUN" = true ]; then
        print_info "Dry run mode - no changes will be made"
        return 0
    fi
    
    print_warning "Are you sure you want to rollback $ENVIRONMENT environment?"
    read -p "Type 'yes' to confirm: " -r
    echo
    
    if [[ ! $REPLY =~ ^yes$ ]]; then
        print_info "Rollback cancelled"
        exit 0
    fi
}

# Function to create rollback snapshot
create_rollback_snapshot() {
    print_info "Creating rollback snapshot..."
    
    SNAPSHOT_DIR="$SCRIPT_DIR/../.rollback-snapshots"
    mkdir -p "$SNAPSHOT_DIR"
    
    SNAPSHOT_FILE="$SNAPSHOT_DIR/rollback-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).json"
    
    cat > "$SNAPSHOT_FILE" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "$ENVIRONMENT",
  "current_task_definition": "$CURRENT_TASK_DEF",
  "current_revision": $CURRENT_REVISION,
  "target_task_definition": "$TARGET_TASK_DEF",
  "target_revision": $TARGET_REVISION,
  "rollback_type": "$TARGET",
  "component": "$COMPONENT"
}
EOF
    
    print_success "Snapshot saved: $SNAPSHOT_FILE"
}

# Function to rollback backend
rollback_backend() {
    print_info "Rolling back backend service..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would update service to: $TARGET_TASK_DEF"
        return 0
    fi
    
    # Update ECS service
    aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$SERVICE_NAME" \
        --task-definition "$TARGET_TASK_DEF" \
        --force-new-deployment \
        --region "$AWS_REGION" \
        > /dev/null
    
    print_success "Service update initiated"
    
    # Wait for service to stabilize
    print_info "Waiting for service to stabilize (this may take several minutes)..."
    
    if aws ecs wait services-stable \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION"; then
        print_success "Service is stable"
    else
        print_error "Service failed to stabilize"
        return 1
    fi
    
    # Verify deployment
    RUNNING_COUNT=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION" \
        --query 'services[0].runningCount' \
        --output text)
    
    DESIRED_COUNT=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION" \
        --query 'services[0].desiredCount' \
        --output text)
    
    if [ "$RUNNING_COUNT" = "$DESIRED_COUNT" ]; then
        print_success "All tasks are running ($RUNNING_COUNT/$DESIRED_COUNT)"
    else
        print_warning "Task count mismatch: $RUNNING_COUNT/$DESIRED_COUNT"
    fi
}

# Function to rollback database
rollback_database() {
    print_info "Rolling back database migrations..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would rollback database migrations"
        return 0
    fi
    
    print_warning "Database rollback requires manual intervention"
    print_info "To rollback database migrations:"
    echo "  1. Connect to the database"
    echo "  2. Run: alembic downgrade -1"
    echo "  3. Or use: python scripts/rollback-migration.sh"
    echo ""
    
    read -p "Have you completed the database rollback? (yes/no): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        print_warning "Database rollback not confirmed"
        return 1
    fi
    
    print_success "Database rollback confirmed"
}

# Function to rollback frontend
rollback_frontend() {
    print_info "Rolling back frontend deployment..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would rollback frontend deployment"
        return 0
    fi
    
    # Get S3 bucket name
    S3_BUCKET=$(aws s3api list-buckets \
        --query "Buckets[?contains(Name, '${PROJECT_NAME}-${ENVIRONMENT}-frontend')].Name" \
        --output text)
    
    if [ -z "$S3_BUCKET" ]; then
        print_error "Frontend S3 bucket not found"
        return 1
    fi
    
    print_info "Frontend bucket: $S3_BUCKET"
    
    # Check if versioning is enabled
    VERSIONING=$(aws s3api get-bucket-versioning \
        --bucket "$S3_BUCKET" \
        --query 'Status' \
        --output text)
    
    if [ "$VERSIONING" != "Enabled" ]; then
        print_error "S3 versioning is not enabled - cannot rollback frontend"
        print_info "Manual frontend rollback required"
        return 1
    fi
    
    print_info "Restoring previous S3 versions..."
    
    # This is a simplified approach - in production, you'd want to restore from a specific backup
    print_warning "Frontend rollback requires manual restoration from S3 versioning"
    print_info "Use AWS Console or CLI to restore previous versions"
    
    # Invalidate CloudFront cache
    DISTRIBUTION_ID=$(aws cloudfront list-distributions \
        --query "DistributionList.Items[?Comment=='${PROJECT_NAME} ${ENVIRONMENT} frontend distribution'].Id" \
        --output text)
    
    if [ -n "$DISTRIBUTION_ID" ]; then
        print_info "Invalidating CloudFront cache..."
        aws cloudfront create-invalidation \
            --distribution-id "$DISTRIBUTION_ID" \
            --paths "/*" \
            > /dev/null
        print_success "CloudFront cache invalidated"
    fi
}

# Function to verify rollback
verify_rollback() {
    print_info "Verifying rollback..."
    
    # Check service health
    print_info "Checking service health..."
    
    # Get ALB endpoint
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names "${PROJECT_NAME}-${ENVIRONMENT}-alb" \
        --region "$AWS_REGION" \
        --query 'LoadBalancers[0].DNSName' \
        --output text 2>/dev/null)
    
    if [ -n "$ALB_DNS" ] && [ "$ALB_DNS" != "None" ]; then
        print_info "Testing health endpoint..."
        
        for i in {1..10}; do
            if curl -f -s "http://$ALB_DNS/health" > /dev/null 2>&1; then
                print_success "Health check passed"
                break
            else
                if [ $i -eq 10 ]; then
                    print_error "Health check failed after 10 attempts"
                    return 1
                fi
                print_info "Waiting for health check... (attempt $i/10)"
                sleep 10
            fi
        done
    else
        print_warning "Could not determine ALB endpoint - skipping health check"
    fi
    
    # Verify task definition
    CURRENT_TASK_DEF_AFTER=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text)
    
    if [ "$CURRENT_TASK_DEF_AFTER" = "$TARGET_TASK_DEF" ]; then
        print_success "Service is using target task definition"
    else
        print_error "Service is not using target task definition"
        print_error "Expected: $TARGET_TASK_DEF"
        print_error "Actual: $CURRENT_TASK_DEF_AFTER"
        return 1
    fi
}

# Function to log rollback
log_rollback() {
    print_info "Logging rollback..."
    
    LOG_DIR="$SCRIPT_DIR/../.rollback-logs"
    mkdir -p "$LOG_DIR"
    
    LOG_FILE="$LOG_DIR/rollback-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).log"
    
    cat > "$LOG_FILE" << EOF
Rollback Log
============
Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Environment: $ENVIRONMENT
Component: $COMPONENT
Target: $TARGET
From: $CURRENT_TASK_DEF (revision $CURRENT_REVISION)
To: $TARGET_TASK_DEF (revision $TARGET_REVISION)
Status: Success
Performed by: $(aws sts get-caller-identity --query 'Arn' --output text)
EOF
    
    print_success "Rollback logged: $LOG_FILE"
}

# Main execution
main() {
    check_aws_cli
    get_current_deployment
    determine_rollback_target
    display_rollback_plan
    confirm_rollback
    create_rollback_snapshot
    
    # Perform rollback based on component
    ROLLBACK_SUCCESS=true
    
    if [ "$COMPONENT" = "backend" ] || [ "$COMPONENT" = "all" ]; then
        if ! rollback_backend; then
            ROLLBACK_SUCCESS=false
        fi
    fi
    
    if [ "$COMPONENT" = "database" ] || [ "$COMPONENT" = "all" ]; then
        if ! rollback_database; then
            ROLLBACK_SUCCESS=false
        fi
    fi
    
    if [ "$COMPONENT" = "frontend" ] || [ "$COMPONENT" = "all" ]; then
        if ! rollback_frontend; then
            ROLLBACK_SUCCESS=false
        fi
    fi
    
    if [ "$ROLLBACK_SUCCESS" = true ] && [ "$DRY_RUN" = false ]; then
        verify_rollback
        log_rollback
        
        echo ""
        print_success "=== Rollback Completed Successfully ==="
        print_info "Environment: $ENVIRONMENT"
        print_info "Rolled back to: $TARGET_TASK_DEF"
        echo ""
    elif [ "$DRY_RUN" = true ]; then
        echo ""
        print_info "=== Dry Run Completed ==="
        print_info "No changes were made"
        echo ""
    else
        echo ""
        print_error "=== Rollback Failed ==="
        print_error "Please check the logs and fix any issues"
        echo ""
        exit 1
    fi
}

# Run main function
main
