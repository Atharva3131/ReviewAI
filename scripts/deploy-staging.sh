#!/bin/bash
# Staging Environment Deployment Script
# This script deploys the Revive AI application to the staging environment

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="revive-ai"
ENVIRONMENT="staging"
AWS_REGION="${AWS_REGION:-us-east-1}"
TERRAFORM_DIR="aws/terraform"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials are not configured. Please run 'aws configure'."
        exit 1
    fi
    
    log_info "All prerequisites met."
}

create_terraform_backend() {
    log_info "Setting up Terraform backend..."
    
    # Create S3 bucket for Terraform state if it doesn't exist
    if ! aws s3 ls "s3://${PROJECT_NAME}-terraform-state" 2>/dev/null; then
        log_info "Creating S3 bucket for Terraform state..."
        aws s3 mb "s3://${PROJECT_NAME}-terraform-state" --region "$AWS_REGION"
        aws s3api put-bucket-versioning \
            --bucket "${PROJECT_NAME}-terraform-state" \
            --versioning-configuration Status=Enabled
        aws s3api put-bucket-encryption \
            --bucket "${PROJECT_NAME}-terraform-state" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'
    fi
    
    # Create DynamoDB table for state locking if it doesn't exist
    if ! aws dynamodb describe-table --table-name "${PROJECT_NAME}-terraform-locks" --region "$AWS_REGION" 2>/dev/null; then
        log_info "Creating DynamoDB table for Terraform state locking..."
        aws dynamodb create-table \
            --table-name "${PROJECT_NAME}-terraform-locks" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$AWS_REGION"
    fi
    
    log_info "Terraform backend is ready."
}

deploy_infrastructure() {
    log_info "Deploying infrastructure to staging..."
    
    cd "$TERRAFORM_DIR"
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init -reconfigure
    
    # Select or create staging workspace
    log_info "Selecting staging workspace..."
    terraform workspace select staging || terraform workspace new staging
    
    # Plan infrastructure changes
    log_info "Planning infrastructure changes..."
    terraform plan \
        -var-file="staging.tfvars" \
        -out=staging.tfplan
    
    # Apply infrastructure changes
    log_info "Applying infrastructure changes..."
    terraform apply -auto-approve staging.tfplan
    
    # Get outputs
    log_info "Retrieving infrastructure outputs..."
    ECR_REPOSITORY_URL=$(terraform output -raw ecr_repository_url)
    ECS_CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
    
    cd - > /dev/null
    
    log_info "Infrastructure deployment completed."
}

build_and_push_images() {
    log_info "Building and pushing Docker images..."
    
    # Login to ECR
    log_info "Logging in to Amazon ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ECR_REPOSITORY_URL"
    
    # Build backend image
    log_info "Building backend Docker image..."
    docker build -t "${PROJECT_NAME}-backend:staging" ./backend
    
    # Tag image
    IMAGE_TAG="staging-$(date +%Y%m%d-%H%M%S)"
    docker tag "${PROJECT_NAME}-backend:staging" "${ECR_REPOSITORY_URL}:${IMAGE_TAG}"
    docker tag "${PROJECT_NAME}-backend:staging" "${ECR_REPOSITORY_URL}:staging-latest"
    
    # Push images
    log_info "Pushing images to ECR..."
    docker push "${ECR_REPOSITORY_URL}:${IMAGE_TAG}"
    docker push "${ECR_REPOSITORY_URL}:staging-latest"
    
    log_info "Docker images pushed successfully."
    echo "$IMAGE_TAG"
}

run_database_migrations() {
    log_info "Running database migrations..."
    
    # Get network configuration
    SUBNET_ID=$(aws ec2 describe-subnets \
        --filters "Name=tag:Name,Values=${PROJECT_NAME}-staging-private-subnet-1" \
        --query 'Subnets[0].SubnetId' --output text --region "$AWS_REGION")
    
    SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
        --filters "Name=tag:Name,Values=${PROJECT_NAME}-staging-ecs-sg" \
        --query 'SecurityGroups[0].GroupId' --output text --region "$AWS_REGION")
    
    # Run migration task
    log_info "Starting migration task..."
    TASK_ARN=$(aws ecs run-task \
        --cluster "${PROJECT_NAME}-staging-cluster" \
        --task-definition "${PROJECT_NAME}-staging-backend" \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=DISABLED}" \
        --overrides '{"containerOverrides":[{"name":"'${PROJECT_NAME}'-staging-backend","command":["alembic","upgrade","head"]}]}' \
        --query 'tasks[0].taskArn' --output text --region "$AWS_REGION")
    
    log_info "Waiting for migration to complete..."
    aws ecs wait tasks-stopped \
        --cluster "${PROJECT_NAME}-staging-cluster" \
        --tasks "$TASK_ARN" \
        --region "$AWS_REGION"
    
    # Check result
    EXIT_CODE=$(aws ecs describe-tasks \
        --cluster "${PROJECT_NAME}-staging-cluster" \
        --tasks "$TASK_ARN" \
        --query 'tasks[0].containers[0].exitCode' --output text --region "$AWS_REGION")
    
    if [ "$EXIT_CODE" != "0" ]; then
        log_error "Migration failed with exit code: $EXIT_CODE"
        exit 1
    fi
    
    log_info "Database migrations completed successfully."
}

update_ecs_service() {
    log_info "Updating ECS service..."
    
    # Update service with new task definition
    aws ecs update-service \
        --cluster "${PROJECT_NAME}-staging-cluster" \
        --service "${PROJECT_NAME}-staging-backend" \
        --force-new-deployment \
        --region "$AWS_REGION" > /dev/null
    
    log_info "Waiting for service to stabilize..."
    aws ecs wait services-stable \
        --cluster "${PROJECT_NAME}-staging-cluster" \
        --services "${PROJECT_NAME}-staging-backend" \
        --region "$AWS_REGION"
    
    log_info "ECS service updated successfully."
}

run_health_checks() {
    log_info "Running health checks..."
    
    # Get ALB DNS name
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names "${PROJECT_NAME}-staging-alb" \
        --query 'LoadBalancers[0].DNSName' --output text --region "$AWS_REGION")
    
    # Wait for service to be healthy
    log_info "Waiting for service to be healthy..."
    for i in {1..30}; do
        if curl -f -s "https://${ALB_DNS}/health" > /dev/null 2>&1; then
            log_info "✅ Health check passed!"
            return 0
        else
            log_warn "Waiting for service... (attempt $i/30)"
            sleep 10
        fi
    done
    
    log_error "Health check failed after 5 minutes"
    exit 1
}

deploy_frontend() {
    log_info "Deploying frontend to staging..."
    
    # Get S3 bucket name
    S3_BUCKET=$(aws s3api list-buckets \
        --query "Buckets[?contains(Name, '${PROJECT_NAME}-staging-frontend')].Name" \
        --output text)
    
    if [ -z "$S3_BUCKET" ]; then
        log_error "Frontend S3 bucket not found"
        exit 1
    fi
    
    # Build frontend
    log_info "Building frontend..."
    cd frontend
    npm ci
    NEXT_PUBLIC_API_URL="https://staging-api.revive-ai.com" npm run build
    
    # Upload to S3
    log_info "Uploading to S3..."
    aws s3 sync out/ "s3://${S3_BUCKET}/" --delete
    
    # Invalidate CloudFront
    DISTRIBUTION_ID=$(aws cloudfront list-distributions \
        --query "DistributionList.Items[?Comment=='${PROJECT_NAME} staging frontend distribution'].Id" \
        --output text)
    
    if [ -n "$DISTRIBUTION_ID" ]; then
        log_info "Invalidating CloudFront cache..."
        aws cloudfront create-invalidation \
            --distribution-id "$DISTRIBUTION_ID" \
            --paths "/*" > /dev/null
    fi
    
    cd - > /dev/null
    
    log_info "Frontend deployed successfully."
}

print_summary() {
    log_info "========================================="
    log_info "Staging Deployment Summary"
    log_info "========================================="
    log_info "Environment: staging"
    log_info "Region: $AWS_REGION"
    log_info "API URL: https://staging-api.revive-ai.com"
    log_info "App URL: https://staging.revive-ai.com"
    log_info "========================================="
}

# Main deployment flow
main() {
    log_info "Starting staging deployment..."
    
    check_prerequisites
    create_terraform_backend
    deploy_infrastructure
    IMAGE_TAG=$(build_and_push_images)
    run_database_migrations
    update_ecs_service
    run_health_checks
    deploy_frontend
    print_summary
    
    log_info "✅ Staging deployment completed successfully!"
}

# Run main function
main "$@"
