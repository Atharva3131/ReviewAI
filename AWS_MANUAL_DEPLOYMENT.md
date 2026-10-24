# ReviewAI AWS deployment

This runbook deploys the existing FastAPI backend only. Terraform creates one ECR repository, an ECS Fargate service behind a public HTTP ALB, private RDS PostgreSQL, a VPC with private task/database subnets, Secrets Manager secrets, Bedrock task permissions, and CloudWatch logs/alarms. Redis and the frontend are intentionally not deployed.

## Commands, in order

Install AWS CLI v2, Terraform 1.5+, Docker, `psql`, and Python 3.11. Choose a region where the selected Bedrock model is enabled. Set shell variables; do not commit a file containing them.

```bash
export AWS_REGION=us-east-1
export PROJECT=reviewai
export TF_STATE_BUCKET="replace-with-a-globally-unique-reviewai-state-bucket"
export TF_STATE_KEY="production/terraform.tfstate"
export IMAGE_TAG="$(git rev-parse --short HEAD)"
```

1. Verify identity, region, and Bedrock access:

```bash
aws sts get-caller-identity
aws configure get region || true
aws ec2 describe-availability-zones --region "$AWS_REGION" --query 'AvailabilityZones[?State==`available`].ZoneName' --output text
aws bedrock list-foundation-models --region "$AWS_REGION" --query 'modelSummaries[?contains(modelId, `claude-3-haiku`)].modelId' --output text
```

2. Bootstrap the remote state bucket once. This is the only manual AWS resource bootstrap and creates no application resources. For `us-east-1`, omit the location constraint.

```bash
aws s3api create-bucket --bucket "$TF_STATE_BUCKET" --region "$AWS_REGION" \
  --create-bucket-configuration LocationConstraint="$AWS_REGION"
aws s3api put-bucket-versioning --bucket "$TF_STATE_BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$TF_STATE_BUCKET" --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

For `us-east-1`, rerun the first command without `--create-bucket-configuration` if needed.

3. Initialize, format, and validate Terraform:

```bash
cd aws/terraform
terraform init -backend-config="bucket=$TF_STATE_BUCKET" -backend-config="key=$TF_STATE_KEY" -backend-config="region=$AWS_REGION" -backend-config="encrypt=true"
terraform fmt -check -recursive
terraform validate
```

4. Create only ECR first. This handles the bootstrap dependency explicitly: ECS must not start before an image exists.

```bash
terraform plan -target=aws_ecr_repository.backend -target=aws_ecr_lifecycle_policy.backend -var="aws_region=$AWS_REGION" -var="project_name=$PROJECT"
terraform apply -target=aws_ecr_repository.backend -target=aws_ecr_lifecycle_policy.backend -var="aws_region=$AWS_REGION" -var="project_name=$PROJECT"
```

Review the targeted plan and approve it interactively. Do not use `-auto-approve`.

5. Build and push the backend image:

```bash
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT-backend"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
docker build -t "$ECR_URI:$IMAGE_TAG" ./backend
docker push "$ECR_URI:$IMAGE_TAG"
```

6. Plan, review, and apply all remaining resources:

```bash
terraform plan -out=reviewai.tfplan -var="aws_region=$AWS_REGION" -var="project_name=$PROJECT" -var="image_tag=$IMAGE_TAG"
terraform show reviewai.tfplan
terraform apply reviewai.tfplan
```

7. Run the one-time Alembic migration against private RDS. Use a private CI runner or an SSM port-forwarding path through a temporary managed host. Never use the local default database.

```bash
test -n "$(find ../../backend/alembic/versions -type f -name '*.py' -not -name '__init__.py' -print -quit)" || { echo 'No Alembic revision exists; create and review the initial migration first.'; exit 1; }
RDS_MASTER_SECRET_ARN="$(terraform output -raw rds_master_secret_arn)"
export RDS_SECRET_JSON="$(aws secretsmanager get-secret-value --secret-id "$RDS_MASTER_SECRET_ARN" --region "$AWS_REGION" --query SecretString --output text)"
export DATABASE_URL="$(python3 -c 'import json, os; from urllib.parse import quote; s=json.loads(os.environ["RDS_SECRET_JSON"]); print(f"postgresql://{quote(s[\"username\"])}:{quote(s[\"password\"])}@{s[\"host\"]}:{s[\"port\"]}/{s[\"dbname\"]}?sslmode=require")')"
cd ../../backend
APP_ENV=production DATABASE_URL="$DATABASE_URL" alembic upgrade head
unset RDS_SECRET_JSON
unset DATABASE_URL
cd ../aws/terraform
```

Do not put `alembic upgrade head` in the Dockerfile, ECS command, or FastAPI startup lifecycle.

8. Inspect ECS and CloudWatch:

```bash
aws ecs describe-services --cluster "$PROJECT-cluster" --services "$PROJECT-backend" --region "$AWS_REGION" --query 'services[0].{running:runningCount,desired:desiredCount,status:status,events:events[0:5]}'
aws logs tail "/ecs/$PROJECT/backend" --since 15m --follow --region "$AWS_REGION"
```

9. Test the public API end to end:

```bash
ALB_DNS="$(terraform output -raw alb_dns_name)"
curl --fail --show-error "http://$ALB_DNS/health"
curl --fail --show-error "http://$ALB_DNS/ready"
```

The frontend is not deployed by Terraform. Build it separately with `NEXT_PUBLIC_API_URL=http://$ALB_DNS npm run build` only after the API passes these checks, using the existing frontend hosting setup.

## Current blocker

At preparation time, `backend/alembic/versions/` contained only `.gitkeep`. Generate and review an initial migration from the complete model set, commit it, and rerun the revision check before sending production traffic. Terraform/app deployment is not database readiness.

## Cost risks

Always-on costs are primarily one NAT Gateway, one internet-facing ALB, one `db.t4g.micro` RDS instance with 20 GiB gp3 storage, and one 0.25 vCPU/512 MiB Fargate task. CloudWatch logs, ECR storage, RDS backups, public IPv4, and Bedrock token usage add variable cost; Bedrock can dominate at high volume. RDS deletion protection and final snapshots are enabled.

## Unavoidable console/manual steps

Enable Bedrock model access if the account requires it. Provide a private network path for the migration command. The Terraform stack does not deploy the frontend or configure a domain/TLS certificate.
