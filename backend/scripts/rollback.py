#!/usr/bin/env python3
"""
Database migration rollback script for Revive AI

This script handles automated rollback of database migrations
with safety checks and verification.
"""
import os
import sys
import subprocess
import argparse
import logging
from datetime import datetime
from typing import Optional
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RollbackError(Exception):
    """Custom exception for rollback errors"""
    pass


class DatabaseRollback:
    """Handles database rollback operations"""
    
    def __init__(self, environment: str = "development", dry_run: bool = False):
        self.environment = environment
        self.dry_run = dry_run
        self.database_url = os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise RollbackError("DATABASE_URL environment variable is not set")
        
        # Production safety check
        if environment == "production" and not dry_run:
            logger.warning("⚠️  PRODUCTION ROLLBACK - This is a critical operation!")
    
    def run_command(self, command: list, check: bool = True) -> tuple:
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
        
        for line in stdout.split('\n'):
            if line.strip():
                revision = line.split()[0] if line.split() else None
                logger.info(f"Current revision: {revision}")
                return revision
        
        return None
    
    def get_migration_history(self, limit: int = 10) -> list:
        """Get migration history"""
        logger.info("Getting migration history...")
        
        returncode, stdout, stderr = self.run_command(
            ["alembic", "history", "--verbose"],
            check=False
        )
        
        if returncode != 0:
            logger.error(f"Could not get migration history: {stderr}")
            return []
        
        # Parse history output
        history = []
        for line in stdout.split('\n'):
            if '->' in line:
                parts = line.split('->')
                if len(parts) >= 2:
                    from_rev = parts[0].strip()
                    to_rev = parts[1].strip().split()[0] if parts[1].strip() else None
                    history.append((from_rev, to_rev))
        
        return history[:limit]
    
    def validate_target_revision(self, target: str) -> bool:
        """Validate that target revision exists"""
        logger.info(f"Validating target revision: {target}")
        
        returncode, stdout, stderr = self.run_command(
            ["alembic", "show", target],
            check=False
        )
        
        if returncode != 0:
            logger.error(f"Invalid target revision: {stderr}")
            return False
        
        logger.info("✓ Target revision is valid")
        return True
    
    def generate_rollback_sql(self, target: str) -> str:
        """Generate SQL for rollback without applying it"""
        logger.info(f"Generating rollback SQL to {target}...")
        
        returncode, stdout, stderr = self.run_command(
            ["alembic", "downgrade", target, "--sql"],
            check=False
        )
        
        if returncode != 0:
            raise RollbackError(f"Failed to generate rollback SQL: {stderr}")
        
        return stdout
    
    def confirm_rollback(self, current: str, target: str) -> bool:
        """Ask for user confirmation for rollback"""
        if self.dry_run:
            return True
        
        print("\n" + "="*80)
        print("⚠️  DATABASE ROLLBACK CONFIRMATION")
        print("="*80)
        print(f"Environment: {self.environment}")
        print(f"Current revision: {current}")
        print(f"Target revision: {target}")
        print(f"Database: {self.database_url.split('@')[1] if '@' in self.database_url else 'hidden'}")
        print("="*80)
        
        if self.environment == "production":
            print("\n⚠️  THIS IS A PRODUCTION DATABASE ROLLBACK!")
            print("This operation will modify production data.")
            response = input("\nType 'ROLLBACK PRODUCTION' to confirm: ")
            return response == "ROLLBACK PRODUCTION"
        else:
            response = input("\nType 'yes' to confirm rollback: ")
            return response.lower() == "yes"
    
    def run_rollback(self, target: str, force: bool = False) -> bool:
        """Run database rollback"""
        current = self.get_current_revision()
        
        if not current:
            raise RollbackError("Could not determine current revision")
        
        if current == target:
            logger.info("✓ Database is already at target revision")
            return True
        
        # Validate target
        if not self.validate_target_revision(target):
            raise RollbackError(f"Invalid target revision: {target}")
        
        # Confirm rollback
        if not force and not self.confirm_rollback(current, target):
            logger.info("Rollback cancelled by user")
            return False
        
        if self.dry_run:
            logger.info("DRY RUN: Generating rollback SQL")
            sql = self.generate_rollback_sql(target)
            print("\n" + "="*80)
            print("ROLLBACK SQL (DRY RUN)")
            print("="*80)
            print(sql)
            print("="*80 + "\n")
            return True
        
        logger.info(f"Rolling back from {current} to {target}...")
        
        returncode, stdout, stderr = self.run_command(
            ["alembic", "downgrade", target],
            check=False
        )
        
        if returncode != 0:
            logger.error(f"Rollback failed: {stderr}")
            return False
        
        logger.info("✓ Rollback completed successfully")
        logger.info(stdout)
        return True
    
    def verify_rollback(self, expected_revision: str) -> bool:
        """Verify rollback was applied correctly"""
        logger.info("Verifying rollback...")
        
        current = self.get_current_revision()
        if current != expected_revision:
            logger.error(f"Rollback verification failed: expected {expected_revision}, got {current}")
            return False
        
        logger.info("✓ Rollback verified successfully")
        return True
    
    def create_rollback_report(self, success: bool, target: str, error: Optional[str] = None) -> dict:
        """Create a rollback report"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "dry_run": self.dry_run,
            "success": success,
            "target_revision": target,
            "current_revision": self.get_current_revision(),
            "database_url": self.database_url.split('@')[1] if '@' in self.database_url else "hidden"
        }
        
        if error:
            report["error"] = error
        
        return report
    
    def save_report(self, report: dict, filename: str = "rollback_report.json"):
        """Save rollback report to file"""
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Rollback report saved to {filename}")


def main():
    """Main entry point for rollback script"""
    parser = argparse.ArgumentParser(
        description="Automated database rollback script for Revive AI"
    )
    parser.add_argument(
        "target",
        help="Target revision to rollback to (e.g., -1 for previous, or specific revision ID)"
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
        help="Generate SQL without applying rollback"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt (use with caution!)"
    )
    parser.add_argument(
        "--report",
        default="rollback_report.json",
        help="Path to save rollback report"
    )
    
    args = parser.parse_args()
    
    try:
        rollback = DatabaseRollback(
            environment=args.environment,
            dry_run=args.dry_run
        )
        
        logger.info(f"Starting rollback for {args.environment} environment")
        
        # Show migration history
        history = rollback.get_migration_history()
        if history:
            logger.info("Recent migration history:")
            for i, (from_rev, to_rev) in enumerate(history[:5]):
                logger.info(f"  {i+1}. {from_rev} -> {to_rev}")
        
        # Run rollback
        success = rollback.run_rollback(args.target, force=args.force)
        
        if not success:
            raise RollbackError("Rollback execution failed or was cancelled")
        
        # Verify rollback
        if not args.dry_run:
            if not rollback.verify_rollback(args.target):
                raise RollbackError("Rollback verification failed")
        
        # Create success report
        report = rollback.create_rollback_report(success=True, target=args.target)
        rollback.save_report(report, args.report)
        
        logger.info("✓ Rollback completed successfully!")
        return 0
        
    except RollbackError as e:
        logger.error(f"Rollback failed: {e}")
        
        try:
            rollback = DatabaseRollback(environment=args.environment)
            report = rollback.create_rollback_report(
                success=False,
                target=args.target,
                error=str(e)
            )
            rollback.save_report(report, args.report)
        except Exception as report_error:
            logger.error(f"Could not save failure report: {report_error}")
        
        return 1
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
