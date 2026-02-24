# Database Migration Automation

This directory contains automated scripts for managing database migrations in the Revive AI platform.

## Scripts

### seed_demo_data.py

Automated demo data seeding script for testing and demonstration purposes.

**Features:**
- Creates realistic demo organizations, users, and data
- Generates reviews with varying sentiment and urgency
- Creates customers with different risk profiles
- Generates support tickets and recovery actions
- Produces agent decisions for testing workflows
- Safety checks to prevent production seeding
- Clear and reseed functionality

**Usage:**

```bash
# Seed demo data
python scripts/seed_demo_data.py --environment development

# Clear existing data and reseed
python scripts/seed_demo_data.py --clear --environment development

# Clear data only
python scripts/seed_demo_data.py --clear
```

**What Gets Created:**
- 3 Organizations (Restaurant, SaaS, Logistics)
- 6 Users (2 per organization: admin + user)
- 15 Customers (5 per organization with varying risk levels)
- ~24 Reviews (mix of positive, moderate, negative)
- ~15 Support Tickets (different priorities)
- ~6 Recovery Actions (email, discount, call)
- ~15 Agent Decisions (various decision types)

**Login Credentials:**
- Bella's Restaurant: `admin@bellas-restaurant.com` / `demo123`
- TechSupport Pro: `admin@techsupportpro.com` / `demo123`
- QuickShip Logistics: `admin@quickship.com` / `demo123`

**Safety Features:**
- Blocks execution in production environment
- Requires explicit environment specification
- Clear confirmation for data deletion

**Environment Variables:**
- `DATABASE_URL` (required): PostgreSQL connection string
- `ENVIRONMENT` (optional): Target environment (development/staging only)

**Exit Codes:**
- `0`: Success
- `1`: Failure or production environment detected

**Documentation:**
- Quick Start: `scripts/DEMO_QUICK_START.md`
- Full Scenarios: `docs/DEMO_SCENARIOS.md`

### migrate.py

Automated database migration script with validation, reporting, and safety checks.

**Features:**
- Pre-migration validation of migration files
- Alembic configuration verification
- Dry-run mode for SQL generation
- Post-migration verification
- JSON reporting for CI/CD integration
- Environment-specific execution

**Usage:**

```bash
# Run migration to latest version
python scripts/migrate.py --environment production

# Dry run (generate SQL without applying)
python scripts/migrate.py --environment staging --dry-run

# Migrate to specific revision
python scripts/migrate.py --environment development --target abc123

# Skip validation (not recommended)
python scripts/migrate.py --environment staging --skip-validation

# Custom report path
python scripts/migrate.py --environment production --report /path/to/report.json
```

**Environment Variables:**
- `DATABASE_URL` (required): PostgreSQL connection string
- `ENVIRONMENT` (optional): Target environment (development/staging/production)

**Exit Codes:**
- `0`: Success
- `1`: Failure

### rollback.py

Automated database rollback script with safety confirmations and verification.

**Features:**
- Interactive confirmation prompts
- Production safety checks
- Dry-run mode for SQL generation
- Rollback verification
- Migration history display
- JSON reporting

**Usage:**

```bash
# Rollback to previous migration
python scripts/rollback.py -1 --environment staging

# Rollback to specific revision
python scripts/rollback.py abc123 --environment production

# Dry run (generate SQL without applying)
python scripts/rollback.py -1 --environment staging --dry-run

# Force rollback without confirmation (use with caution!)
python scripts/rollback.py -1 --environment staging --force

# Custom report path
python scripts/rollback.py -1 --environment production --report /path/to/report.json
```

**Safety Features:**
- Production rollbacks require typing "ROLLBACK PRODUCTION" to confirm
- Non-production rollbacks require typing "yes" to confirm
- Force flag bypasses confirmation (use only in automated environments)

**Environment Variables:**
- `DATABASE_URL` (required): PostgreSQL connection string
- `ENVIRONMENT` (optional): Target environment (development/staging/production)

**Exit Codes:**
- `0`: Success
- `1`: Failure or cancelled

## CI/CD Integration

### GitHub Actions Workflows

The migration scripts are integrated into the following workflows:

#### 1. Continuous Integration (ci.yml)

Automatically runs migrations during integration tests:

```yaml
- name: Run automated database migration
  run: |
    cd backend
    python scripts/migrate.py --environment development --report migration_report_ci.json
```

#### 2. Production Deployment (deploy-production.yml)

Runs automated migrations during production deployment:

```yaml
- name: Run automated database migration
  run: |
    # Runs migration in ECS task
    python scripts/migrate.py --environment production --report migration_report.json
```

#### 3. Database Migration Workflow (database-migration.yml)

Dedicated workflow for manual and automated migrations:

**Manual Trigger:**
- Go to Actions → Database Migration
- Select environment (staging/production)
- Choose migration type (upgrade/downgrade/reset)
- Optionally specify target revision
- Enable dry-run for preview

**Automatic Trigger:**
- Automatically runs on push to main when migration files change
- Targets staging environment by default
- Includes validation, backup (production only), execution, and verification

### Migration Reports

Both scripts generate JSON reports for CI/CD integration:

```json
{
  "timestamp": "2024-02-15T10:30:00.000000",
  "environment": "production",
  "dry_run": false,
  "success": true,
  "current_revision": "001",
  "database_url": "revive-ai-production-db.xxx.rds.amazonaws.com:5432/revive_ai"
}
```

Reports are uploaded as artifacts in GitHub Actions for audit trails.

## Local Development

### Running Migrations Locally

```bash
# Set up environment
export DATABASE_URL="postgresql://user:pass@localhost:5432/revive_ai"
export ENVIRONMENT="development"

# Run migration
cd backend
python scripts/migrate.py --environment development

# Check current revision
alembic current

# View migration history
alembic history --verbose
```

### Creating New Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column to users table"

# Create empty migration
alembic revision -m "Custom migration"

# Edit the generated file in alembic/versions/
# Then run migration
python scripts/migrate.py --environment development
```

### Testing Migrations

```bash
# Test migration with dry-run
python scripts/migrate.py --environment development --dry-run

# Apply migration
python scripts/migrate.py --environment development

# Test rollback with dry-run
python scripts/rollback.py -1 --environment development --dry-run

# Apply rollback
python scripts/rollback.py -1 --environment development
```

## Best Practices

### 1. Always Test Migrations

- Run migrations in development first
- Use dry-run mode to preview SQL
- Test rollback procedures
- Verify data integrity after migration

### 2. Production Migrations

- Always create RDS snapshot before production migrations (automated in workflow)
- Use staging environment to test migrations first
- Schedule migrations during low-traffic periods
- Have rollback plan ready
- Monitor application health after migration

### 3. Migration File Guidelines

- Keep migrations small and focused
- Include both upgrade() and downgrade() functions
- Test migrations in both directions
- Document complex migrations
- Avoid data migrations in schema migrations when possible

### 4. Rollback Procedures

- Test rollback in staging before production
- Understand data loss implications
- Document rollback steps
- Have communication plan for users
- Monitor application after rollback

### 5. CI/CD Integration

- Migrations run automatically in CI for testing
- Production migrations require manual approval (via GitHub environment protection)
- All migrations are logged and reported
- Failed migrations trigger alerts

## Troubleshooting

### Migration Fails

1. Check migration logs in GitHub Actions artifacts
2. Review migration report JSON
3. Verify database connectivity
4. Check for syntax errors in migration files
5. Ensure database user has required permissions

### Rollback Fails

1. Check current database revision: `alembic current`
2. Verify target revision exists: `alembic show <revision>`
3. Review rollback SQL: `python scripts/rollback.py <target> --dry-run`
4. Check for data dependencies
5. Consider manual intervention if automated rollback fails

### Common Issues

**Issue:** "DATABASE_URL environment variable is not set"
- **Solution:** Set DATABASE_URL before running scripts

**Issue:** "Migration validation failed"
- **Solution:** Check migration files for syntax errors using `python -m py_compile`

**Issue:** "Alembic configuration error"
- **Solution:** Verify alembic.ini and env.py are properly configured

**Issue:** "Could not determine current revision"
- **Solution:** Database may be empty or alembic_version table missing

## Security Considerations

- Never commit DATABASE_URL to version control
- Use environment-specific credentials
- Rotate database passwords regularly
- Limit database user permissions to minimum required
- Audit all production migrations
- Encrypt migration reports if they contain sensitive data

## Monitoring and Alerts

- Migration success/failure is reported in GitHub Actions
- Production migrations trigger CloudWatch alarms
- Failed migrations send notifications to alert email
- Migration reports are stored as artifacts for 30 days
- Application health checks run after migrations

## Support

For issues or questions about database migrations:
1. Check this README
2. Review migration logs in GitHub Actions
3. Check application logs in CloudWatch
4. Contact DevOps team for production issues
