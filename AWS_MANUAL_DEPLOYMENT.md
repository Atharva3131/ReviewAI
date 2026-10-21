# ReviewAI — AWS Manual Deployment Guide

This guide provides step-by-step instructions to manually deploy the ReviewAI application to AWS using Amazon ECS Fargate, RDS PostgreSQL, Amazon Bedrock, Amazon S3, AWS Secrets Manager, and AWS CloudWatch.

---

## Architecture Overview

```
Frontend (S3 + CloudFront / Vercel / Amplify)
       ↓ (HTTPS)
Application Load Balancer (ALB)
       ↓
ECS Fargate (FastAPI Backend Container)
       ├── RDS PostgreSQL (Database & Schema via Alembic)
       ├── ElastiCache Redis (Optional Caching / Celery Broker)
       ├── Amazon S3 (Knowledge Base & Artifacts)
       ├── AWS Secrets Manager (Production Credentials)
       ├── Amazon Bedrock (Production LLM — Claude 3 / Titan)
       └── Amazon CloudWatch (Application Logs & Metrics)
```

---

## STEP 1 — Create RDS PostgreSQL

1. Go to **AWS RDS Console** → **Create database**.
2. **Engine type**: PostgreSQL (Version 15 or 16).
3. **Templates**: Free Tier / Dev/Test (or Production single-AZ for cost optimization).
4. **Settings**:
   - DB instance identifier: `reviewai-db`
   - Master username: `reviewai_user`
   - Master password: `(secure-password)`
5. **DB Instance class**: `db.t4g.micro` (cost conscious).
6. **Storage**: 20 GB gp3.
7. **Connectivity**:
   - VPC: Default VPC or `reviewai-vpc`
   - Public access: **No** (Private subnet access only)
   - VPC Security Group: Create new `reviewai-rds-sg` allowing **Inbound TCP 5432** only from `reviewai-ecs-sg`.
8. **Additional Configuration**:
   - Initial database name: `revive_ai`
9. **Connection String Format**:
   `postgresql://reviewai_user:<password>@<rds-endpoint>:5432/revive_ai`

---

## STEP 2 — Create Amazon S3 Bucket

1. Go to **AWS S3 Console** → **Create bucket**.
2. **Bucket name**: `reviewai-data-<your-account-id>` (must be globally unique).
3. **Region**: `us-east-1` (matching Bedrock & ECS).
4. **Block Public Access**: Enable all public access blocks.
5. **Prefix convention**: All non-transactional application data will be stored under `reviewai/` (e.g. `reviewai/knowledge/`, `reviewai/artifacts/`).

---

## STEP 3 — Configure Amazon Bedrock

1. Go to **AWS Bedrock Console** → **Model access** in `us-east-1`.
2. Request access for **Anthropic Claude 3 Haiku** (`anthropic.claude-3-haiku-20240307-v1:0`) or **Amazon Titan Text Express**.
3. Ensure your ECS Task Role (see Step 7) has the following IAM policy attached:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel",
           "bedrock:InvokeModelWithResponseStream"
         ],
         "Resource": "*"
       }
     ]
   }
   ```
4. Configuration variables to set:
   - `LLM_PROVIDER`: `bedrock`
   - `BEDROCK_MODEL_ID`: `anthropic.claude-3-haiku-20240307-v1:0`
   - `BEDROCK_REGION`: `us-east-1`

---

## STEP 4 — Create Secrets Manager Secret

1. Go to **AWS Secrets Manager** → **Store a new secret**.
2. **Secret type**: Other type of secret (Key/value pairs).
3. Secret name: `reviewai/production/secrets`
4. Add key-value pairs:
   - `DATABASE_URL`: `postgresql://reviewai_user:<password>@<rds-endpoint>:5432/revive_ai`
   - `SECRET_KEY`: `<random-long-secret-key>` *(Generic application secret for internal cryptography and session security; JWT authentication is disabled/removed)*
   - `REDIS_URL`: `redis://<elasticache-endpoint>:6379` (if using ElastiCache, else leave default)

---

## STEP 5 — Create Amazon ECR Repository & Push Container

1. Go to **AWS ECR Console** → **Create repository**.
   - Name: `reviewai-backend`
2. Run build and push commands locally:
   ```bash
   # 1. Authenticate Docker to your ECR registry
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws-account-id>.dkr.ecr.us-east-1.amazonaws.com

   # 2. Build the production Docker image
   docker build -t reviewai-backend ./backend

   # 3. Tag the image for ECR
   docker tag reviewai-backend:latest <aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/reviewai-backend:latest

   # 4. Push to ECR
   docker push <aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/reviewai-backend:latest
   ```

---

## STEP 6 — Create ECS Cluster

1. Go to **AWS ECS Console** → **Clusters** → **Create Cluster**.
2. **Cluster name**: `reviewai-cluster`
3. **Infrastructure**: AWS Fargate (serverless).

---

## STEP 7 — Create ECS Task Definition

1. Go to **ECS Console** → **Task definitions** → **Create new task definition**.
2. **Family name**: `reviewai-backend-task`
3. **Infrastructure**: AWS Fargate
4. **CPU**: `0.5 vCPU` (512) | **Memory**: `1 GB` (1024)
5. **Task Execution Role** (`ecsTaskExecutionRole` - used by AWS ECS agent to launch container):
   - Policy `AmazonECSTaskExecutionRolePolicy` (ECR pull & CloudWatch `awslogs` stream creation)
   - Inline policy for `secretsmanager:GetSecretValue` on secret `reviewai/production/secrets` to inject environment variables into the container at startup.
6. **Task Role** (`reviewai-ecs-task-role` - used directly by backend Python code / boto3 at runtime):
   - **Amazon Bedrock Policy**:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "bedrock:InvokeModel",
             "bedrock:InvokeModelWithResponseStream"
           ],
           "Resource": "*"
         }
       ]
     }
     ```
   - **Amazon S3 Policy** (for knowledge base / storage operations):
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "s3:GetObject",
             "s3:PutObject",
             "s3:ListBucket"
           ],
           "Resource": [
             "arn:aws:s3:::reviewai-data-*",
             "arn:aws:s3:::reviewai-data-*/*"
           ]
         }
       ]
     }
     ```
   - *(Note: Direct CloudWatch logging permissions are handled by `awslogs` driver via Task Execution Role since stdout/stderr are captured automatically. If application code reads Secrets Manager directly at runtime via boto3 instead of ECS secret injection, attach `secretsmanager:GetSecretValue` to the Task Role as well).*
7. **Container Details**:
   - Name: `backend`
   - Image URI: `<aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/reviewai-backend:latest`
   - Port mapping: `8000` TCP
8. **Environment Variables**:
   - `APP_ENV`: `production`
   - `DEBUG`: `false`
   - `LOG_LEVEL`: `INFO`
   - `LLM_PROVIDER`: `bedrock`
   - `BEDROCK_MODEL_ID`: `anthropic.claude-3-haiku-20240307-v1:0`
   - `BEDROCK_REGION`: `us-east-1`
   - `AWS_REGION`: `us-east-1`
   - `AWS_S3_BUCKET`: `reviewai-data-<your-account-id>`
   - `AWS_SECRETS_MANAGER_SECRET_NAME`: `reviewai/production/secrets`
   - `CORS_ALLOWED_ORIGINS`: `https://<your-frontend-domain>`
9. **Health Check**:
   - Command: `CMD-SHELL, curl -f http://localhost:8000/health || exit 1`
   - Interval: 30s | Timeout: 5s | Start period: 10s | Retries: 3
10. **Log Configuration**:
   - Log driver: `awslogs`
   - Log group: `/ecs/reviewai-backend` (Auto-created)

---

## STEP 8 — Create Application Load Balancer (ALB)

1. Go to **EC2 Console** → **Load Balancers** → **Create Load Balancer** (Application Load Balancer).
2. Name: `reviewai-alb` | Scheme: **Internet-facing**
3. Listeners: HTTP 80 (and HTTPS 443 if ACM certificate attached).
4. Target Group:
   - Target type: **IP**
   - Protocol: HTTP | Port: 8000
   - Health check path: `/health`
   - Success code: `200`

---

## STEP 9 — Create ECS Service

1. In `reviewai-cluster`, click **Services** → **Create**.
2. **Launch type**: Fargate
3. **Task definition**: `reviewai-backend-task:1`
4. **Service name**: `reviewai-backend-service`
5. **Desired tasks**: `1`
6. **Networking**:
   - VPC & Subnets: Select public or private subnets
   - Security Group: `reviewai-ecs-sg` allowing TCP 8000 from `reviewai-alb`
7. **Load balancing**: Select `reviewai-alb` and attach target group on port 8000.

---

## STEP 10 — Run Database Migrations

Run Alembic migration against the production RDS PostgreSQL database from a task runner or local workstation connected to RDS:

```bash
# Option A: Run via temporary ECS Task or One-Time Command
docker run --rm \
  -e DATABASE_URL="postgresql://reviewai_user:<password>@<rds-endpoint>:5432/revive_ai" \
  <aws-account-id>.dkr.ecr.us-east-1.amazonaws.com/reviewai-backend:latest \
  alembic upgrade head

# Option B: Run locally inside virtualenv pointing to RDS
export DATABASE_URL="postgresql://reviewai_user:<password>@<rds-endpoint>:5432/revive_ai"
alembic upgrade head
```

---

## STEP 11 — Frontend Production Configuration & Deployment

1. Set production environment variable in frontend build:
   `NEXT_PUBLIC_API_URL=http://<alb-dns-name>` (or `https://api.yourdomain.com`)
2. Build static bundle or deploy to Vercel/S3+CloudFront:
   ```bash
   cd frontend
   npm run build
   ```
3. If hosting on S3 + CloudFront:
   - Upload `.next` or static build output to frontend S3 bucket.
   - Configure CloudFront distribution pointing to S3 origin with fallback to `index.html`.

---

## STEP 12 — Health & Service Verification

Run verification requests against the deployed ALB URL (`http://<alb-dns-name>`):

1. **Process Health Check**:
   ```bash
   curl http://<alb-dns-name>/health
   # Expected response: {"status":"healthy","environment":"production","service":"ReviewAI"}
   ```

2. **Readiness & Service Check**:
   ```bash
   curl http://<alb-dns-name>/ready
   # Expected response: {"status":"ready","database":"ok","llm_provider":"bedrock",...}
   ```

3. **Demo Ingestion Test**:
   ```bash
   curl -X POST http://<alb-dns-name>/api/v1/demo/ingest-demo-review \
     -H "Content-Type: application/json" \
     -d '{
       "customer_name": "Public Demo User",
       "rating": 1,
       "review_text": "The service was terrible and support never responded to my ticket!"
     }'
   ```

---

## STEP 13 — Complete End-to-End Demo Flow

1. Open Deployed Frontend Dashboard in browser: `http://<frontend-url>`
2. Click **"Simulate Google Review"**.
3. Submit a 1-star Google Review.
4. Verify complete automated AI pipeline execution:
   - **Ingestion**: Google Review recorded in RDS PostgreSQL.
   - **Sentiment & Urgency**: Analyzed and scored.
   - **Decision Model**: Category determined (`PRODUCT_QUALITY` / `SERVICE_ISSUE`).
   - **ML Risk**: Churn probability computed.
   - **Bedrock LLM**: Empathetic recovery response generated via Amazon Bedrock.
   - **Policy Engine**: Strategy assigned (`AUTO_EXECUTE` / `APPROVAL_REQUIRED`).
   - **Dashboard**: Real-time update showing persisted results in metrics & tables.
