# Revive AI

### Turn customer feedback into customer recovery

Revive AI is an AI-powered customer recovery platform for teams that want to understand public reviews, identify churn risk, and take the right recovery action before a dissatisfied customer is lost.

It combines review intelligence, customer-risk prediction, agent orchestration, and response generation in one multi-tenant SaaS application.

![Revive AI platform](https://img.shields.io/badge/status-active%20development-22c55e?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=next.js&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Terraform-FF9900?style=for-the-badge&logo=amazon-aws&logoColor=white)

## What it does

- **Review intelligence** — sentiment analysis, urgency detection, issue categorization, and suggested responses.
- **Customer recovery** — churn-risk scoring, bad-review likelihood assessment, and recommended recovery actions.
- **Agent orchestration** — combines rules, confidence scores, and LLM reasoning to choose the next best action.
- **Multi-tenant operations** — organization isolation, role-based access, audit trails, and privacy tooling.
- **Operational visibility** — health checks, request metrics, rate limiting, structured logging, and optional Sentry error tracking.
- **Billing-ready product** — Stripe integration for subscription and checkout workflows.

## Architecture

```mermaid
flowchart LR
    User[Customer success team] --> Web[Next.js frontend]
    Web --> ALB[AWS Application Load Balancer]
    ALB --> ECS[AWS ECS Fargate\nFastAPI backend]
    ECS --> RDS[(Amazon RDS\nPostgreSQL 15)]
    ECS --> Bedrock[Amazon Bedrock\nClaude model]
    ECS --> Redis[(Redis\noptional for local/dev)]
    ECS --> Secrets[AWS Secrets Manager]
    ECS --> Logs[CloudWatch Logs & Alarms]
    ECR[Amazon ECR] --> ECS
    TF[Terraform] -. provisions .-> ALB
    TF -. provisions .-> ECS
    TF -. provisions .-> RDS
    TF -. provisions .-> ECR
```

## Cloud and platform services

### AWS — production infrastructure

Terraform in [`aws/terraform`](aws/terraform) provisions the current backend deployment:

| Service | Purpose |
| --- | --- |
| **Amazon ECS on Fargate** | Runs the containerized FastAPI backend without managing servers |
| **Amazon ECR** | Stores scanned backend container images with lifecycle cleanup |
| **Amazon RDS for PostgreSQL 15** | Managed, encrypted application database in private subnets |
| **Amazon Bedrock** | LLM inference; the Terraform default is Anthropic Claude 3 Haiku |
| **AWS Secrets Manager** | Stores application and RDS credentials injected into ECS |
| **Application Load Balancer** | Public HTTP entry point and ECS health-check routing |
| **Amazon VPC** | Public/private subnets, route tables, internet gateway, and security groups |
| **AWS IAM** | Separate ECS execution and task roles with least-purpose permissions |
| **Amazon CloudWatch** | ECS log groups plus CPU and ALB 5xx alarms |
| **Amazon S3** | Optional remote Terraform state; bootstrap instructions are in the deployment runbook |

### Application and external integrations

| Service | Use |
| --- | --- |
| **Redis** | Cache, rate limiting, sessions, metrics, and Celery broker/result backend; configurable for local or managed Redis |
| **OpenAI, Google Gemini, Mistral AI** | Optional alternative LLM providers supported by the application |
| **Stripe** | Payments and subscription checkout |
| **SendGrid** | Optional email delivery |
| **Sentry** | Optional application error tracking |

> The current Terraform ECS task uses **Amazon Bedrock** and sets `REDIS_ENABLED=false`. Redis remains available for local development and alternate deployments. The Terraform stack deploys the backend only; the frontend needs its own hosting setup.

## Technology stack

- **Frontend:** Next.js 14, React 18, TypeScript, Tailwind CSS, Radix UI, Recharts
- **Backend:** FastAPI, Python, SQLAlchemy, Pydantic, async PostgreSQL, Alembic
- **AI/ML:** Amazon Bedrock, OpenAI, Gemini, Mistral, XGBoost, LightGBM, scikit-learn, pgvector
- **Async work:** Celery with Redis
- **Infrastructure:** Docker, AWS, Terraform 1.5+, AWS provider 5.x
- **Quality:** pytest, Jest, Playwright, axe, Black, isort, Flake8, Bandit

## Repository layout

```text
.
├── backend/                 # FastAPI API, services, models, migrations, and tests
├── frontend/                # Next.js dashboard and customer-facing UI
├── aws/terraform/           # AWS infrastructure as code
├── scripts/                 # Local, staging, production, and rollback scripts
├── database/                # Database initialization assets
├── AWS_MANUAL_DEPLOYMENT.md # Step-by-step AWS deployment runbook
├── DEMO_SETUP.md            # Demo environment setup
└── ARCHITECTURE_INTERVIEW_PREP.md
```

## Run locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (with pgvector if vector features are enabled)
- Redis 7+ for caching, rate limiting, and background tasks
- API credentials for the LLM provider you want to use

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Edit .env, then run migrations and start the API
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) for the dashboard. The API is available at [http://localhost:8000](http://localhost:8000), with Swagger at [`/docs`](http://localhost:8000/docs) and ReDoc at [`/redoc`](http://localhost:8000/redoc).

## Configuration

The backend template is [`backend/.env.example`](backend/.env.example), and the frontend template is [`frontend/.env.example`](frontend/.env.example).

At minimum, configure:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/revive_ai
REDIS_URL=redis://localhost:6379
SECRET_KEY=generate-a-long-random-secret
DEFAULT_LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
BEDROCK_REGION=us-east-1
```

For local non-AWS development, set `DEFAULT_LLM_PROVIDER` to `openai`, `mistral`, or `gemini` and provide the matching API key. Never commit credentials, `.env` files, Terraform state, or production variable files containing secrets.

## Deploy with Terraform and AWS

The supported AWS deployment path is documented in [`AWS_MANUAL_DEPLOYMENT.md`](AWS_MANUAL_DEPLOYMENT.md). It covers state bootstrapping, ECR image publishing, Terraform validation, RDS migrations, ECS rollout, and health checks.

Quick outline:

```bash
# Prerequisites: AWS CLI, Terraform >= 1.5, Docker, Python, and psql
aws sts get-caller-identity

cd aws/terraform
terraform init
terraform fmt -check -recursive
terraform validate

# Review values first; never put secrets in *.tfvars files
terraform plan -var-file=staging.tfvars -out=reviewai.tfplan
terraform apply reviewai.tfplan
```

The first deployment must create and push the backend image to ECR before ECS can start it. For the complete bootstrap sequence, use the runbook rather than applying the abbreviated commands above blindly.

Useful deployment assets:

- [`aws/terraform`](aws/terraform) — VPC, ECS, ECR, RDS, Bedrock permissions, secrets, and monitoring
- [`scripts/`](scripts) — deployment, rollout, monitoring, and rollback helpers
- [`aws/ecs-task-definition.json`](aws/ecs-task-definition.json) — standalone ECS task-definition reference
- [`aws/THIRD_PARTY_LICENSES`](aws/THIRD_PARTY_LICENSES) — AWS CLI bundle license information

## Testing and quality checks

```bash
# Backend
cd backend
pytest
pytest --cov=app --cov-report=html

# Frontend
cd frontend
npm run type-check
npm test
npm run test:e2e
```

Repository-wide checks are also available through [`scripts/quality-check-all.sh`](scripts/quality-check-all.sh) and [`scripts/quality-check-all.ps1`](scripts/quality-check-all.ps1).

## Documentation

- [AWS deployment runbook](AWS_MANUAL_DEPLOYMENT.md)
- [Demo setup](DEMO_SETUP.md)
- [Backend API documentation](backend/docs/API_DOCUMENTATION.md)
- [API quick reference](backend/docs/QUICK_REFERENCE.md)
- [cURL examples](backend/docs/API_DOCUMENTATION_CURL.md)
- [Backend guide](backend/README.md)
- [Deployment scripts guide](scripts/README.md)
- [Architecture interview preparation](ARCHITECTURE_INTERVIEW_PREP.md)

## Security notes

Revive AI includes JWT authentication, password hashing, CSRF and XSS protections, input validation, SQL-injection defenses, security headers, rate limiting, encrypted RDS storage, private database subnets, and secrets injection through AWS Secrets Manager.

Before production traffic:

- use HTTPS with a certificate and a domain in front of the load balancer;
- restrict CORS to trusted frontend origins;
- review IAM and security-group rules;
- enable durable Terraform remote state and state locking;
- run migrations from a private, controlled network path;
- rotate application and provider credentials regularly.

## License

Proprietary — all rights reserved.
