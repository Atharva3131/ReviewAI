#!/bin/bash

# Database Migration Rollback Script
# Safely rollback Alembic database migrations

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Rollback database migrations safely.

OPTIONS:
    -e, --environment ENV    Target environment (staging|production) [required]
    -s, --steps STEPS       Number of migration steps to rollback [default: 1]
    -t, --target REVISION   Target migration revision to rollback to
    -b, --backup            Create database backup before rollback
    -d, --dry-run          Show what would be rolled back without executing
    -f, --force            Force rollback without confirmation
    -h, --help             Display this help message

EXAMPLES:
    # Rollback one migration
    $0 -e production -s 1

    # Rollback to specific revision
    $0 -e production -t abc123def456

    # Rollback with backup
    $0 -e production -s 1 -b

    # Dry run
    $0 -e production -s 1 -d

EOF
    exit 1
}

# Parse arguments
ENVIRONMENT=""
STEPS=1
TARGET_REVISION=""
CREATE_BACKUP=false
DRY_RUN=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -s|--steps)
            STEPS="$2"
            shift 2
            ;;
        -t|--target)
            TARGET_REVISION="$2"
            shift 2
            ;;
        -b|--backup)
            CREATE_BACKUP=true
            shift
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

if [ -z "$ENVIRONMENT" ]; then
    print_error "Environment is required"
    usage
fi

print_info "=== Database Migration Rollback ==="
print_info "Environment: $ENVIRONMENT"
print_info "Steps: $STEPS"
print_info "Dry Run: $DRY_RUN"
echo ""

# Set database URL based on environment
case $ENVIRONMENT in
    staging)
        if [ -z "$STAGING_DATABASE_URL" ]; then
            print_error "STAGING_DATABASE_URL environment variable not set"
            exit 1
        fi
        DATABASE_URL="$STAGING_DATABASE_URL"
        ;;
    production)
        if [ -z "$DATABASE_URL" ]; then
            print_error "DATABASE_URL environment variable not set"
            exit 1
        fi
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Change to backend directory
cd "$(dirname "$0")/../backend" || exit 1

# Check current migration status
check_migration_status() {
    print_info "Checking current migration status..."
    
    CURRENT_REVISION=$(alembic current 2>/dev/null | grep -oP '\w+(?= \(head\))' || echo "")
    
    if [ -z "$CURRENT_REVISION" ]; then
        print_error "Could not determine current migration revision"
        exit 1
    fi
    
    print_success "Current revision: $CURRENT_REVISION"
    
    # Show migration history
    print_info "Recent migration history:"
    alembic history --verbose | head -n 20
    echo ""
}

# Create database backup
create_database_backup() {
    if [ "$CREATE_BACKUP" = false ]; then
        return 0
    fi
    
    print_info "Creating database backup..."
    
    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY RUN] Would create database backup"
        return 0
    fi
    
    BACKUP_DIR="../.db-backups"
    mkdir -p "$BACKUP_DIR"
    
    BACKUP_FILE="$BACKUP_DIR/backup-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).sql"
    
    # Extract database connection details
    DB_HOST=$(echo "$DATABASE_URL" | grep -oP '(?<=@)[^:/]+')
    DB_PORT=$(echo "$DATABASE_URL" | grep -oP '(?<=:)\d+(?=/)')
    DB_NAME=$(echo "$DATABASE_URL" | grep -oP '(?<=/)[^?]+$')
    DB_USER=$(echo "$DATABASE_URL" | grep -oP '(?<=://)[^:]+')
    
    print_info "Backing up database: $DB_NAME"
    
    # Use pg_dump to create backup
    if command -v pg_dump &> /dev/null; then
        PGPASSWORD=$(echo "$DATABASE_URL" | grep -oP '(?<=:)[^@]+(?=@)') \
        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            -F c -f "$BACKUP_FILE" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            print_success "Backup created: $BACKUP_FILE"
        else
            print_error "Backup failed"
            exit 1
        fi
    else
        print_warning "pg_dump not found - skipping backup"
        print_warning "Install PostgreSQL client tools to enable backups"
    fi
}

# Display rollback plan
display_rollback_plan() {
    print_info "=== Rollback Plan ==="
    echo ""
    
    if [ -n "$TARGET_REVISION" ]; then
        print_info "Target: Rollback to revision $TARGET_REVISION"
        
        # Show migrations that will be rolled back
        print_info "Migrations to be rolled back:"
        alembic history -r "$TARGET_REVISION:current" 2>/dev/null || true
    else
        print_info "Target: Rollback $STEPS step(s)"
        
        # Calculate target revision
        TARGET_REV=$(alembic history | grep -A "$STEPS" "$CURRENT_REVISION" | tail -n 1 | grep -oP '^\w+')
        
        if [ -n "$TARGET_REV" ]; then
            print_info "Will rollback to: $TARGET_REV"
            print_info "Migrations to be rolled back:"
            alembic history -r "$TARGET_REV:current" 2>/dev/null || true
        fi
    fi
    
    echo ""
}

# Confirm rollback
confirm_rollback() {
    if [ "$FORCE" = true ]; then
        print_warning "Force flag set - skipping confirmation"
        return 0
    fi
    
    if [ "$DRY_RUN" = true ]; then
        print_info "Dry run mode - no changes will be made"
        return 0
    fi
    
    print_warning "⚠️  WARNING: Database rollback is a destructive operation!"
    print_warning "This may result in data loss if migrations included data transformations."
    echo ""
    print_warning "Are you sure you want to rollback $ENVIRONMENT database?"
    read -p "Type 'yes' to confirm: " -r
    echo
    
    if [[ ! $REPLY =~ ^yes$ ]]; then
        print_info "Rollback cancelled"
        exit 0
    fi
}

# Perform rollback
perform_rollback() {
    print_info "Performing database rollback..."
    
    if [ "$DRY_RUN" = true ]; then
        if [ -n "$TARGET_REVISION" ]; then
            print_info "[DRY RUN] Would execute: alembic downgrade $TARGET_REVISION"
        else
            print_info "[DRY RUN] Would execute: alembic downgrade -$STEPS"
        fi
        return 0
    fi
    
    # Execute rollback
    if [ -n "$TARGET_REVISION" ]; then
        print_info "Rolling back to revision: $TARGET_REVISION"
        alembic downgrade "$TARGET_REVISION"
    else
        print_info "Rolling back $STEPS step(s)"
        alembic downgrade "-$STEPS"
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Rollback completed successfully"
    else
        print_error "Rollback failed"
        exit 1
    fi
}

# Verify rollback
verify_rollback() {
    print_info "Verifying rollback..."
    
    NEW_REVISION=$(alembic current 2>/dev/null | grep -oP '\w+(?= \(head\))' || echo "")
    
    if [ -z "$NEW_REVISION" ]; then
        print_error "Could not verify new revision"
        return 1
    fi
    
    print_success "New revision: $NEW_REVISION"
    
    if [ "$NEW_REVISION" != "$CURRENT_REVISION" ]; then
        print_success "Database successfully rolled back"
    else
        print_warning "Database revision unchanged"
    fi
}

# Log rollback
log_rollback() {
    LOG_DIR="../.migration-logs"
    mkdir -p "$LOG_DIR"
    
    LOG_FILE="$LOG_DIR/rollback-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).log"
    
    cat > "$LOG_FILE" << EOF
Migration Rollback Log
======================
Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Environment: $ENVIRONMENT
From Revision: $CURRENT_REVISION
To Revision: $NEW_REVISION
Steps: $STEPS
Backup Created: $CREATE_BACKUP
Performed by: $(whoami)
EOF
    
    print_success "Rollback logged: $LOG_FILE"
}

# Main execution
main() {
    check_migration_status
    display_rollback_plan
    confirm_rollback
    create_database_backup
    perform_rollback
    
    if [ "$DRY_RUN" = false ]; then
        verify_rollback
        log_rollback
        
        echo ""
        print_success "=== Migration Rollback Completed ==="
        print_info "Environment: $ENVIRONMENT"
        print_info "Previous revision: $CURRENT_REVISION"
        print_info "Current revision: $NEW_REVISION"
        echo ""
    else
        echo ""
        print_info "=== Dry Run Completed ==="
        print_info "No changes were made"
        echo ""
    fi
}

main
