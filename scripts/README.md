# Deployment Scripts

This directory contains deployment and operational scripts for the Revive AI platform.

## Available Scripts

### deploy-staging.sh

Automated deployment script for the staging environment.

**Usage:**
```bash
chmod +x scripts/deploy-staging.sh
./scripts/deploy-staging.sh
```

**What it does:**
1. Checks prerequisites (AWS CLI, Terraform, Docker)
2. Sets up Terraform backend (S3 + DynamoDB)
3. Deploys infrastructure using Terraform
4. Builds and pushes Docker images to ECR
5. Runs database migrations
6. Updates ECS service
7. Runs health checks
8. Deploys frontend to S3/CloudFront

**Requirements:**
- AWS CLI v2.x or later
- Terraform v1.0 or later
- Docker v20.x or later
- Node.js v18.x or later
- Python v3.11 or later
- Configured AWS credentials with appropriate permissions

**Environment Variables:**
- `AWS_REGION` (default: us-east-1)
- `PROJECT_NAME` (default: revive-ai)
- `ENVIRONMENT` (default: staging)

**Example:**
```bash
# Deploy to staging in us-west-2
AWS_REGION=us-west-2 ./scripts/deploy-staging.sh
```

## Script Permissions

On Unix-like systems (Linux, macOS), make scripts executable:

```bash
chmod +x scripts/*.sh
```

On Windows, use Git Bash or WSL to run bash scripts.

## Adding New Scripts

When adding new scripts:

1. Use descriptive names (e.g., `deploy-production.sh`, `backup-database.sh`)
2. Add shebang line: `#!/bin/bash`
3. Include error handling: `set -e` and `set -u`
4. Add usage documentation in comments
5. Update this README with script description
6. Make script executable: `chmod +x scripts/your-script.sh`

## Best Practices

1. **Error Handling**: Always use `set -e` to exit on errors
2. **Variables**: Use `set -u` to catch undefined variables
3. **Logging**: Use colored output for better readability
4. **Validation**: Check prerequisites before running operations
5. **Idempotency**: Scripts should be safe to run multiple times
6. **Documentation**: Include inline comments for complex operations
7. **Testing**: Test scripts in staging before using in production

## Common Issues

### Permission Denied

```bash
# Fix: Make script executable
chmod +x scripts/deploy-staging.sh
```

### AWS Credentials Not Found

```bash
# Fix: Configure AWS credentials
aws configure
```

### Docker Not Running

```bash
# Fix: Start Docker daemon
# On Linux: sudo systemctl start docker
# On macOS: Open Docker Desktop
# On Windows: Start Docker Desktop
```

## Related Documentation

- [Staging Deployment Guide](../docs/STAGING_DEPLOYMENT.md)
- [Staging Quick Start](../docs/STAGING_QUICK_START.md)
- [Environment Comparison](../docs/ENVIRONMENT_COMPARISON.md)

## Support

For issues with scripts:
1. Check script output for error messages
2. Verify prerequisites are installed
3. Check AWS credentials and permissions
4. Review related documentation
5. Contact DevOps team or create GitHub issue
