# Database Migration Automation - Quick Reference

## Common Commands

### Run Migration
```bash
# Development
python scripts/migrate.py --environment development

# Staging
python scripts/migrate.py --environment staging

# Production
python scripts/migrate.py --environment production
```

### Preview Migration (Dry Run)
```bash
python scripts/migrate.py --environment <env> --dry-run
```

### Rollback
```bash
# Rollback to previous migration
python scripts/rollback.py -1 --environment <env>

# Rollback to specific revision
python scripts/rollback.py <revision_id> --environment <env>

# Preview rollback
python scripts/rollback.py -1 --environment <env> --dry-run
```

### Check Status
```bash
# Current revision
alembic current

# Migration history
alembic history --verbose

# Pending migrations
alembic heads
```

### Create Migration
```bash
# Auto-generate from models
alembic revision --autogenerate -m "Description"

# Empty migration
alembic revision -m "Description"
```

## Environment Variables

```bash
# Required
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# Optional
export ENVIRONMENT="development"  # or staging, production
```

## GitHub Actions

### Manual Migration
1. Go to: Actions → Database Migration
2. Click: "Run workflow"
3. Select: Environment, Migration type
4. Click: "Run workflow"

### Automatic Migration
- Pushes to `main` with migration file changes
- Automatically runs in staging
- Validates and executes migration

## Exit Codes

- `0` = Success
- `1` = Failure

## Reports

Migration reports saved to:
- Local: `migration_report.json` or `rollback_report.json`
- CI/CD: GitHub Actions artifacts (30 days retention)

## Safety Features

### Development
- ✅ Validation only
- ✅ No confirmation required

### Staging
- ✅ Validation + verification
- ✅ Confirmation for rollback

### Production
- ✅ Full validation + RDS snapshot
- ✅ Requires "ROLLBACK PRODUCTION" for rollback
- ✅ Health checks after migration
- ✅ Automatic rollback on failure

## Troubleshooting

### Migration Fails
```bash
# Check current state
alembic current

# View logs
cat migration_report.json

# Rollback if needed
python scripts/rollback.py -1 --environment <env>
```

### Can't Connect to Database
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check environment variable
echo $DATABASE_URL
```

### Syntax Error in Migration
```bash
# Validate migration files
python -m py_compile alembic/versions/*.py

# Check Alembic config
alembic check
```

## Support

- Documentation: `backend/scripts/README.md`
- Full Guide: `MIGRATION_AUTOMATION.md`
- Tests: `backend/tests/test_migration_automation.py`

## Emergency Contacts

- DevOps Team: devops@revive-ai.com
- On-Call: See PagerDuty
