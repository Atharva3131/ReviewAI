#!/bin/bash

# Production deployment script for Revive AI
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="revive-ai"
AWS_REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="production"

# Functions
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

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if required tools are installed
    command -v aws >/dev/null 2>&1 || { log_error "AWS CLI is required but not installed. Aborting."; exit 1; }
    command -v docker >/dev/null 2>&1 || { log_error "Docker is required but not installed. Aborting."; exit 1; }
    command -v terraform >/dev/null 2>&1 || { log_error "Terraform is required but not installed. Aborting."; exit 1; }
    
    # Check AWS credentials
    aws sts get-caller-identity >/dev/null 2>&1 || { log_error "AWS credentials not configured. Aborting."; exit 1; }
    
    log_success "Prerequisites check passed"
}

deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."
    
    cd aws/terraform
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan -var-file="production.tfvars" -out=tfplan
    
    # Apply deployment
    log_warning "About to deploy infrastructure. This may take 10-15 minutes."
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        terraform apply tfplan
        log_success "Infrastructure deployed successfully"
    else
        log_warning "Infrastructure deployment cancelled"
        exit 1
    fi
    
    cd ../..
}

build_and_push_images() {
    log_info "Building and pushing Docker images..."
    
    # Get ECR repository URL
    ECR_REPO=$(aws ecr describe-repositories --repository-names ${PROJECT_NAME}-backend --query 'repositories[0].repositoryUri' --output text --region ${AWS_REGION})
    
    if [ -z "$ECR_REPO" ]; then
        log_error "ECR repository not found. Make sure infrastructure is deployed first."
        exit 1
    fi
    
    # Login to ECR
    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}
    
    # Build backend image
    log_info "Building backend image..."
    cd backend
    docker build -t ${PROJECT_NAME}-backend:latest .
    docker tag ${PROJECT_NAME}-backend:latest ${ECR_REPO}:latest
    docker tag ${PROJECT_NAME}-backend:latest ${ECR_REPO}:prod-$(date +%Y%m%d-%H%M%S)
    
    # Push backend image
    log_info "Pushing backend image..."
    docker push ${ECR_REPO}:latest
    docker push ${ECR_REPO}:prod-$(date +%Y%m%d-%H%M%S)
    
    cd ..
    
    log_success "Docker images built and pushed successfully"
}

deploy_ecs_services() {
    log_info "Deploying ECS services..."
    
    # Get cluster name
    CLUSTER_NAME="${PROJECT_NAME}-cluster"
    
    # Register task definition
    log_info "Registering ECS task definition..."
    TASK_DEFINITION_ARN=$(aws ecs register-task-definition \
        --cli-input-json file://aws/ecs-task-definition.json \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text \
        --region ${AWS_REGION})
    
    if [ -z "$TASK_DEFINITION_ARN" ]; then
        log_error "Failed to register task definition"
        exit 1
    fi
    
    log_success "Task definition registered: $TASK_DEFINITION_ARN"
    
    # Update or create ECS service
    log_info "Updating ECS service..."
    
    # Check if service exists
    SERVICE_EXISTS=$(aws ecs describe-services \
        --cluster ${CLUSTER_NAME} \
        --services ${PROJECT_NAME}-backend \
        --query 'services[0].serviceName' \
        --output text \
        --region ${AWS_REGION} 2>/dev/null || echo "None")
    
    if [ "$SERVICE_EXISTS" = "None" ]; then
        # Create new service
        log_info "Creating new ECS service..."
        aws ecs create-service \
            --cluster ${CLUSTER_NAME} \
            --service-name ${PROJECT_NAME}-backend \
            --task-definition ${TASK_DEFINITION_ARN} \
            --desired-count 2 \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=DISABLED}" \
            --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:${AWS_REGION}:xxx:targetgroup/${PROJECT_NAME}-backend-tg/xxx,containerName=${PROJECT_NAME}-backend,containerPort=8000" \
            --region ${AWS_REGION}
    else
        # Update existing service
        log_info "Updating existing ECS service..."
        aws ecs update-service \
            --cluster ${CLUSTER_NAME} \
            --service ${PROJECT_NAME}-backend \
            --task-definition ${TASK_DEFINITION_ARN} \
            --desired-count 2 \
            --region ${AWS_REGION}
    fi
    
    # Wait for service to stabilize
    log_info "Waiting for service to stabilize..."
    aws ecs wait services-stable \
        --cluster ${CLUSTER_NAME} \
        --services ${PROJECT_NAME}-backend \
        --region ${AWS_REGION}
    
    log_success "ECS service deployed successfully"
}

deploy_frontend() {
    log_info "Deploying frontend to S3 and CloudFront..."
    
    # Get S3 bucket name and CloudFront distribution ID
    S3_BUCKET=$(aws s3api list-buckets --query "Buckets[?contains(Name, '${PROJECT_NAME}-frontend')].Name" --output text --region ${AWS_REGION})
    CLOUDFRONT_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='${PROJECT_NAME} frontend distribution'].Id" --output text --region ${AWS_REGION})
    
    if [ -z "$S3_BUCKET" ] || [ -z "$CLOUDFRONT_ID" ]; then
        log_error "S3 bucket or CloudFront distribution not found. Make sure infrastructure is deployed first."
        exit 1
    fi
    
    # Build frontend
    log_info "Building frontend..."
    cd frontend
    npm ci
    npm run build
    
    # Upload to S3
    log_info "Uploading frontend to S3..."
    aws s3 sync out/ s3://${S3_BUCKET}/ --delete --region ${AWS_REGION}
    
    # Invalidate CloudFront cache
    log_info "Invalidating CloudFront cache..."
    aws cloudfront create-invalidation \
        --distribution-id ${CLOUDFRONT_ID} \
        --paths "/*" \
        --region ${AWS_REGION}
    
    cd ..
    
    log_success "Frontend deployed successfully"
}

run_database_migrations() {
    log_info "Running database migrations..."
    
    # Get ECS cluster and task definition
    CLUSTER_NAME="${PROJECT_NAME}-cluster"
    TASK_DEFINITION="${PROJECT_NAME}-backend"
    
    # Get subnet and security group for migration task
    SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=${PROJECT_NAME}-private-subnet-1" --query 'Subnets[0].SubnetId' --output text --region ${AWS_REGION})
    SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters "Name=tag:Name,Values=${PROJECT_NAME}-ecs-sg" --query 'SecurityGroups[0].GroupId' --output text --region ${AWS_REGION})
    
    # Run migration task
    log_info "Starting migration task..."
    TASK_ARN=$(aws ecs run-task \
        --cluster ${CLUSTER_NAME} \
        --task-definition ${TASK_DEFINITION} \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ID}],securityGroups=[${SECURITY_GROUP_ID}],assignPublicIp=DISABLED}" \
        --overrides '{"containerOverrides":[{"name":"'${PROJECT_NAME}'-backend","command":["alembic","upgrade","head"]}]}' \
        --query 'tasks[0].taskArn' \
        --output text \
        --region ${AWS_REGION})
    
    if [ -z "$TASK_ARN" ]; then
        log_error "Failed to start migration task"
        exit 1
    fi
    
    # Wait for migration to complete
    log_info "Waiting for migration to complete..."
    aws ecs wait tasks-stopped \
        --cluster ${CLUSTER_NAME} \
        --tasks ${TASK_ARN} \
        --region ${AWS_REGION}
    
    # Check migration result
    EXIT_CODE=$(aws ecs describe-tasks \
        --cluster ${CLUSTER_NAME} \
        --tasks ${TASK_ARN} \
        --query 'tasks[0].containers[0].exitCode' \
        --output text \
        --region ${AWS_REGION})
    
    if [ "$EXIT_CODE" = "0" ]; then
        log_success "Database migrations completed successfully"
    else
        log_error "Database migrations failed with exit code: $EXIT_CODE"
        exit 1
    fi
}

health_check() {
    log_info "Performing health checks..."
    
    # Get ALB DNS name
    ALB_DNS=$(aws elbv2 describe-load-balancers --names ${PROJECT_NAME}-alb --query 'LoadBalancers[0].DNSName' --output text --region ${AWS_REGION})
    
    if [ -z "$ALB_DNS" ]; then
        log_error "Load balancer not found"
        exit 1
    fi
    
    # Check backend health
    log_info "Checking backend health..."
    for i in {1..30}; do
        if curl -f -s "https://${ALB_DNS}/health" > /dev/null; then
            log_success "Backend health check passed"
            break
        else
            log_info "Waiting for backend to be healthy... (attempt $i/30)"
            sleep 10
        fi
        
        if [ $i -eq 30 ]; then
            log_error "Backend health check failed after 5 minutes"
            exit 1
        fi
    done
    
    # Check frontend
    log_info "Checking frontend..."
    DOMAIN_NAME=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='${PROJECT_NAME}.com.'].Name" --output text | sed 's/\.$//')
    
    if [ -n "$DOMAIN_NAME" ]; then
        if curl -f -s "https://app.${DOMAIN_NAME}" > /dev/null; then
            log_success "Frontend health check passed"
        else
            log_warning "Frontend health check failed, but this might be due to DNS propagation"
        fi
    fi
}

cleanup() {
    log_info "Cleaning up temporary files..."
    
    # Remove terraform plan file
    rm -f aws/terraform/tfplan
    
    # Clean up Docker images
    docker system prune -f
    
    log_success "Cleanup completed"
}

main() {
    log_info "Starting production deployment for ${PROJECT_NAME}"
    log_info "AWS Region: ${AWS_REGION}"
    log_info "Environment: ${ENVIRONMENT}"
    
    # Deployment steps
    check_prerequisites
    deploy_infrastructure
    build_and_push_images
    run_database_migrations
    deploy_ecs_services
    deploy_frontend
    health_check
    cleanup
    
    log_success "🎉 Production deployment completed successfully!"
    log_info "Your application should be available at:"
    log_info "  - API: https://api.${PROJECT_NAME}.com"
    log_info "  - App: https://app.${PROJECT_NAME}.com"
    log_info "  - Root: https://${PROJECT_NAME}.com"
}

# Run main function
main "$@"