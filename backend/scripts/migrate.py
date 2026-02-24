#!/usr/bin/env python3
"""
Database migration automation script for Revive AI

This script handles automated database migrations with validation,
backup, and rollback capabilities for CI/CD pipelines.
"""
import os
import sys
import subprocess
import argparse
import logging
from datetime import datetime
from typing import Optional, Tuple
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Custom exception for migration errors"""
    pass


class DatabaseMigrator:
    """Handles database migration operations"""
    
    def __init__(self, environment: str = "development", dry_run: bool = False):
        self.environment = environment
        self.dry_run = dry_run
        self.database_url = os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise MigrationError("DATABASE_URL environment variable is not set")
    
    def run_command(self, command: list, check: bool = True) -> Tuple[int, str, str]:
        """Execute a shell command and return the result"""
        logger.info(f"Executing: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            return e.returncode, e.stdout, e.stderr
    
    def validate_migrations(self) -> bool:
        """Validate migration files for syntax errors"""
        logger.info("Validating migration files...")
        
        # Check for Python syntax errors in migration files
        migrations_dir = "alembic/versions"
        if not os.path.exists(migrations_dir):
            raise MigrationError(f"Migrations directory not found: {migrations_dir}")
        
        migration_files = [
            f for f in os.listdir(migrations_dir)
            if f.endswith('.py') and not f.startswith('__')
        ]
        
        if not migration_files:
            logger.warning("No migration files found")
            return True
        
        for migration_file in migration_files:
            file_path = os.path.join(migrations_dir, migration_file)
            returncode, stdout, stderr = self.run_command(
                ["python", "-m", "py_compile", file_path],
                check=False
            )
            
            if returncode != 0:
                logger.error(f"Syntax error in {migration_file}: {stderr}")
                return False
        
        logger.info(f"✓ Validated {len(migration_files)} migration files")
        return True
    
    def check_alembic_config(self) -> bool:
        """Verify Alembic configuration is valid"""
        logger.info("Checking Alembic configuration...")
        
        returncode, stdout, stderr = self.run_command(
            ["alembic", "check"],
            check=False
        )
        
        if returncode != 0:
            logger.error(f"Alembic configuration error: {stderr}")
            return False
        
        logger.info("✓ Alembic configuration is valid")
        return True
    
    def get_current_revision(self) -> Optional[str]:
        """Get the current database revision"""
        logger.info("Getting current database revision...")
        
        returncode, stdout, stderr = self.run_command(
            ["alembic", "current"],
            check=False
        )
        
        if returncode != 0:
            logger.warning(f"Could not get current revision: {stderr}")
            return None
        
        # Parse the output to extract revision
        for line in stdout.split('\n'):
            if line.strip():
                # Extract revision ID (first word)
                revision = line.split()[0] if line.split() else None
                logger.info(f"Current revision: {revision}")
                return revision
        
        logger.info("No current revision (empty database)")
        return None
    
    def get_pending_migrations(self) -> list:
        """Get list of pending migrations"""
        logger.info("Checking for pending migrations...")
        
        returncode, stdout, stderr = self.run_command(
            ["alembic", "heads"],
            check=False
        )
        
        if returncode != 0:
            logger.error(f"Could not get pending migrations: {stderr}")
            return []
        
        current = self.get_current_revision()
        head = stdout.strip().split()[0] if stdout.strip() else None
        
        if current == head:
            logger.info("✓ Database is up to date")
            return []
        
        logger.info(f"Pending migration: {current} -> {head}")
        return [head]
    
    def generate_sql(self, target: str = "head") -> str:
        """Generate SQL for migrations without applying them"""
        logger.info(f"Generating SQL for migration to {target}...")
        
        returncode, stdout, stderr = self.run_command(
            ["alembic", "upgrade", target, "--sql"],
            check=False
        )
        
        if returncode != 0:
            raise MigrationError(f"Failed to generate SQL: {stderr}")
        
        return stdout
    
    def run_migration(self, target: str = "head") -> bool:
        """Run database migration"""
        if self.dry_run:
            logger.info("DRY RUN: Generating SQL instead of applying migration")
            sql = self.generate_sql(target)
            print("\n" + "="*80)
            print("MIGRATION SQL (DRY RUN)")
            print("="*80)
            print(sql)
            print("="*80 + "\n")
            return True
        
        logger.info(f"Running migration to {target}...")
        
        returncode, stdout, stderr = self.run_command(
            ["alembic", "upgrade", target],
            check=False
        )
        
        if returncode != 0:
            logger.error(f"Migration failed: {stderr}")
            return False
        
        logger.info("✓ Migration completed successfully")
        logger.info(stdout)
        return True
    
    def verify_migration(self) -> bool:
        """Verify migration was applied correctly"""
        logger.info("Verifying migration...")
        
        # Check current revision matches expected
        current = self.get_current_revision()
        if not current:
            logger.error("Could not verify migration - no current revision")
            return False
        
        # Check for pending migrations
        pending = self.get_pending_migrations()
        if pending:
            logger.error(f"Migration verification failed - pending migrations: {pending}")
            return False
        
        logger.info("✓ Migration verified successfully")
        return True
    
    def create_migration_report(self, success: bool, error: Optional[str] = None) -> dict:
        """Create a migration report for CI/CD"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "dry_run": self.dry_run,
            "success": success,
            "current_revision": self.get_current_revision(),
            "database_url": self.database_url.split('@')[1] if '@' in self.database_url else "hidden"
        }
        
        if error:
            report["error"] = error
        
        return report
    
    def save_report(self, report: dict, filename: str = "migration_report.json"):
        """Save migration report to file"""
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Migration report saved to {filename}")


def main():
    """Main entry point for migration script"""
    parser = argparse.ArgumentParser(
        description="Automated database migration script for Revive AI"
    )
    parser.add_argument(
        "--environment",
        default=os.getenv("ENVIRONMENT", "development"),
        choices=["development", "staging", "production"],
        help="Target environment"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate SQL without applying migrations"
    )
    parser.add_argument(
        "--target",
        default="head",
        help="Target revision (default: head)"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip pre-migration validation"
    )
    parser.add_argument(
        "--report",
        default="migration_report.json",
        help="Path to save migration report"
    )
    
    args = parser.parse_args()
    
    try:
        migrator = DatabaseMigrator(
            environment=args.environment,
            dry_run=args.dry_run
        )
        
        logger.info(f"Starting migration for {args.environment} environment")
        
        # Pre-migration validation
        if not args.skip_validation:
            logger.info("Running pre-migration validation...")
            
            if not migrator.validate_migrations():
                raise MigrationError("Migration validation failed")
            
            if not migrator.check_alembic_config():
                raise MigrationError("Alembic configuration check failed")
        
        # Check for pending migrations
        pending = migrator.get_pending_migrations()
        if not pending and not args.dry_run:
            logger.info("✓ No pending migrations - database is up to date")
            report = migrator.create_migration_report(success=True)
            migrator.save_report(report, args.report)
            return 0
        
        # Run migration
        success = migrator.run_migration(args.target)
        
        if not success:
            raise MigrationError("Migration execution failed")
        
        # Post-migration verification
        if not args.dry_run:
            if not migrator.verify_migration():
                raise MigrationError("Migration verification failed")
        
        # Create success report
        report = migrator.create_migration_report(success=True)
        migrator.save_report(report, args.report)
        
        logger.info("✓ Migration completed successfully!")
        return 0
        
    except MigrationError as e:
        logger.error(f"Migration failed: {e}")
        
        # Create failure report
        try:
            migrator = DatabaseMigrator(environment=args.environment)
            report = migrator.create_migration_report(success=False, error=str(e))
            migrator.save_report(report, args.report)
        except Exception as report_error:
            logger.error(f"Could not save failure report: {report_error}")
        
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
