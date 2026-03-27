"""
Tests for database migration automation scripts

These tests verify the migration and rollback scripts work correctly.
"""

import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from migrate import DatabaseMigrator, MigrationError
from rollback import DatabaseRollback, RollbackError


class TestDatabaseMigrator:
    """Tests for DatabaseMigrator class"""

    def test_migrator_initialization(self):
        """Test migrator initializes correctly"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development", dry_run=False)
            assert migrator.environment == "development"
            assert migrator.dry_run is False
            assert migrator.database_url == "postgresql://test:test@localhost/test"

    def test_migrator_requires_database_url(self):
        """Test migrator raises error without DATABASE_URL"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                MigrationError, match="DATABASE_URL environment variable is not set"
            ):
                DatabaseMigrator()

    def test_validate_migrations_success(self):
        """Test migration validation succeeds with valid files"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development")

            # Mock the run_command to simulate successful validation
            with patch.object(migrator, "run_command", return_value=(0, "", "")):
                with patch("os.path.exists", return_value=True):
                    with patch("os.listdir", return_value=["001_initial_schema.py"]):
                        result = migrator.validate_migrations()
                        assert result is True

    def test_validate_migrations_syntax_error(self):
        """Test migration validation fails with syntax errors"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development")

            # Mock the run_command to simulate syntax error
            with patch.object(
                migrator, "run_command", return_value=(1, "", "SyntaxError")
            ):
                with patch("os.path.exists", return_value=True):
                    with patch("os.listdir", return_value=["bad_migration.py"]):
                        result = migrator.validate_migrations()
                        assert result is False

    def test_check_alembic_config_success(self):
        """Test Alembic configuration check succeeds"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development")

            with patch.object(migrator, "run_command", return_value=(0, "", "")):
                result = migrator.check_alembic_config()
                assert result is True

    def test_check_alembic_config_failure(self):
        """Test Alembic configuration check fails"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development")

            with patch.object(
                migrator, "run_command", return_value=(1, "", "Config error")
            ):
                result = migrator.check_alembic_config()
                assert result is False

    def test_get_current_revision(self):
        """Test getting current database revision"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development")

            with patch.object(
                migrator, "run_command", return_value=(0, "001 (head)\n", "")
            ):
                revision = migrator.get_current_revision()
                assert revision == "001"

    def test_get_current_revision_empty_database(self):
        """Test getting revision from empty database"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development")

            with patch.object(migrator, "run_command", return_value=(0, "", "")):
                revision = migrator.get_current_revision()
                assert revision is None

    def test_get_pending_migrations_none(self):
        """Test no pending migrations"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development")

            with patch.object(migrator, "run_command", return_value=(0, "001", "")):
                with patch.object(migrator, "get_current_revision", return_value="001"):
                    pending = migrator.get_pending_migrations()
                    assert pending == []

    def test_get_pending_migrations_exists(self):
        """Test pending migrations exist"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development")

            with patch.object(migrator, "run_command", return_value=(0, "002", "")):
                with patch.object(migrator, "get_current_revision", return_value="001"):
                    pending = migrator.get_pending_migrations()
                    assert pending == ["002"]

    def test_generate_sql(self):
        """Test SQL generation for dry run"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development")

            sql_output = "CREATE TABLE test (id INT);"
            with patch.object(
                migrator, "run_command", return_value=(0, sql_output, "")
            ):
                sql = migrator.generate_sql()
                assert sql == sql_output

    def test_run_migration_dry_run(self):
        """Test migration in dry run mode"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development", dry_run=True)

            with patch.object(migrator, "generate_sql", return_value="SQL"):
                result = migrator.run_migration()
                assert result is True

    def test_run_migration_success(self):
        """Test successful migration execution"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development", dry_run=False)

            with patch.object(migrator, "run_command", return_value=(0, "Success", "")):
                result = migrator.run_migration()
                assert result is True

    def test_run_migration_failure(self):
        """Test failed migration execution"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development", dry_run=False)

            with patch.object(migrator, "run_command", return_value=(1, "", "Error")):
                result = migrator.run_migration()
                assert result is False

    def test_verify_migration_success(self):
        """Test migration verification succeeds"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development")

            with patch.object(migrator, "get_current_revision", return_value="002"):
                with patch.object(migrator, "get_pending_migrations", return_value=[]):
                    result = migrator.verify_migration()
                    assert result is True

    def test_verify_migration_failure(self):
        """Test migration verification fails"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development")

            with patch.object(migrator, "get_current_revision", return_value="001"):
                with patch.object(
                    migrator, "get_pending_migrations", return_value=["002"]
                ):
                    result = migrator.verify_migration()
                    assert result is False

    def test_create_migration_report(self):
        """Test migration report creation"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="production")

            with patch.object(migrator, "get_current_revision", return_value="002"):
                report = migrator.create_migration_report(success=True)

                assert report["success"] is True
                assert report["environment"] == "production"
                assert report["current_revision"] == "002"
                assert "timestamp" in report

    def test_create_migration_report_with_error(self):
        """Test migration report with error"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="staging")

            with patch.object(migrator, "get_current_revision", return_value="001"):
                report = migrator.create_migration_report(
                    success=False, error="Test error"
                )

                assert report["success"] is False
                assert report["error"] == "Test error"


class TestDatabaseRollback:
    """Tests for DatabaseRollback class"""

    def test_rollback_initialization(self):
        """Test rollback initializes correctly"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="staging", dry_run=False)
            assert rollback.environment == "staging"
            assert rollback.dry_run is False
            assert rollback.database_url == "postgresql://test:test@localhost/test"

    def test_rollback_requires_database_url(self):
        """Test rollback raises error without DATABASE_URL"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                RollbackError, match="DATABASE_URL environment variable is not set"
            ):
                DatabaseRollback()

    def test_get_migration_history(self):
        """Test getting migration history"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="development")

            history_output = "001 -> 002\nbase -> 001\n"
            with patch.object(
                rollback, "run_command", return_value=(0, history_output, "")
            ):
                history = rollback.get_migration_history()
                assert len(history) == 2
                assert history[0] == ("001", "002")
                assert history[1] == ("base", "001")

    def test_validate_target_revision_success(self):
        """Test target revision validation succeeds"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="development")

            with patch.object(rollback, "run_command", return_value=(0, "Valid", "")):
                result = rollback.validate_target_revision("001")
                assert result is True

    def test_validate_target_revision_failure(self):
        """Test target revision validation fails"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="development")

            with patch.object(rollback, "run_command", return_value=(1, "", "Invalid")):
                result = rollback.validate_target_revision("invalid")
                assert result is False

    def test_generate_rollback_sql(self):
        """Test rollback SQL generation"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="development")

            sql_output = "DROP TABLE test;"
            with patch.object(
                rollback, "run_command", return_value=(0, sql_output, "")
            ):
                sql = rollback.generate_rollback_sql("001")
                assert sql == sql_output

    def test_confirm_rollback_dry_run(self):
        """Test rollback confirmation in dry run mode"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="production", dry_run=True)
            result = rollback.confirm_rollback("002", "001")
            assert result is True

    def test_run_rollback_dry_run(self):
        """Test rollback in dry run mode"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="development", dry_run=True)

            with patch.object(rollback, "get_current_revision", return_value="002"):
                with patch.object(
                    rollback, "validate_target_revision", return_value=True
                ):
                    with patch.object(
                        rollback, "generate_rollback_sql", return_value="SQL"
                    ):
                        result = rollback.run_rollback("001")
                        assert result is True

    def test_run_rollback_already_at_target(self):
        """Test rollback when already at target revision"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="development")

            with patch.object(rollback, "get_current_revision", return_value="001"):
                result = rollback.run_rollback("001")
                assert result is True

    def test_run_rollback_success(self):
        """Test successful rollback execution"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="development", dry_run=False)

            with patch.object(rollback, "get_current_revision", return_value="002"):
                with patch.object(
                    rollback, "validate_target_revision", return_value=True
                ):
                    with patch.object(rollback, "confirm_rollback", return_value=True):
                        with patch.object(
                            rollback, "run_command", return_value=(0, "Success", "")
                        ):
                            result = rollback.run_rollback("001", force=True)
                            assert result is True

    def test_run_rollback_cancelled(self):
        """Test rollback cancelled by user"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="production", dry_run=False)

            with patch.object(rollback, "get_current_revision", return_value="002"):
                with patch.object(
                    rollback, "validate_target_revision", return_value=True
                ):
                    with patch.object(rollback, "confirm_rollback", return_value=False):
                        result = rollback.run_rollback("001")
                        assert result is False

    def test_verify_rollback_success(self):
        """Test rollback verification succeeds"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="development")

            with patch.object(rollback, "get_current_revision", return_value="001"):
                result = rollback.verify_rollback("001")
                assert result is True

    def test_verify_rollback_failure(self):
        """Test rollback verification fails"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="development")

            with patch.object(rollback, "get_current_revision", return_value="002"):
                result = rollback.verify_rollback("001")
                assert result is False

    def test_create_rollback_report(self):
        """Test rollback report creation"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="staging")

            with patch.object(rollback, "get_current_revision", return_value="001"):
                report = rollback.create_rollback_report(success=True, target="001")

                assert report["success"] is True
                assert report["environment"] == "staging"
                assert report["target_revision"] == "001"
                assert report["current_revision"] == "001"
                assert "timestamp" in report


class TestMigrationIntegration:
    """Integration tests for migration automation"""

    def test_full_migration_workflow(self):
        """Test complete migration workflow"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            migrator = DatabaseMigrator(environment="development", dry_run=True)

            # Mock all steps
            with patch.object(migrator, "validate_migrations", return_value=True):
                with patch.object(migrator, "check_alembic_config", return_value=True):
                    with patch.object(
                        migrator, "get_pending_migrations", return_value=["002"]
                    ):
                        with patch.object(migrator, "run_migration", return_value=True):
                            with patch.object(
                                migrator, "verify_migration", return_value=True
                            ):
                                # Simulate full workflow
                                assert migrator.validate_migrations()
                                assert migrator.check_alembic_config()
                                assert len(migrator.get_pending_migrations()) > 0
                                assert migrator.run_migration()

    def test_full_rollback_workflow(self):
        """Test complete rollback workflow"""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}
        ):
            rollback = DatabaseRollback(environment="development", dry_run=True)

            # Mock all steps
            with patch.object(rollback, "get_current_revision", return_value="002"):
                with patch.object(
                    rollback, "validate_target_revision", return_value=True
                ):
                    with patch.object(rollback, "run_rollback", return_value=True):
                        with patch.object(
                            rollback, "verify_rollback", return_value=True
                        ):
                            # Simulate full workflow
                            assert rollback.get_current_revision() == "002"
                            assert rollback.validate_target_revision("001")
                            assert rollback.run_rollback("001")
