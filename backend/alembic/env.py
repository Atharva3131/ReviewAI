"""Alembic environment configuration for Revive AI"""
from logging.config import fileConfig
from sqlalchemy import Connection, engine_from_config, pool
from sqlalchemy.engine import make_url
from alembic import context
import os
import sys

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.core.database import Base
import app.models  # load all active models for Alembic metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
ACTIVE_TABLES = {
    "customers",
    "reviews",
    "support_tickets",
    "recovery_actions",
    "agent_decisions",
    "business_knowledge",
}
if set(Base.metadata.tables) != ACTIVE_TABLES:
    raise RuntimeError(
        "Alembic metadata does not match the active single-user schema: "
        f"expected {sorted(ACTIVE_TABLES)}, found {sorted(Base.metadata.tables)}"
    )

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url() -> str:
    """Get a safe PostgreSQL URL from the environment/application settings."""
    configured_url = os.getenv("DATABASE_URL")
    url = configured_url or settings.DATABASE_URL

    parsed_url = make_url(url)
    if settings.APP_ENV.lower() in {"production", "prod", "staging"}:
        if not configured_url:
            raise RuntimeError(
                "DATABASE_URL must be explicitly set for production/staging migrations; "
                "refusing the local default database"
            )
        if parsed_url.host in {"localhost", "127.0.0.1", "::1"}:
            raise RuntimeError(
                "Production/staging migrations may not target a local PostgreSQL host"
            )

    if settings.DB_SSL and parsed_url.drivername in {"postgresql", "postgresql+psycopg"}:
        query = dict(parsed_url.query)
        query.setdefault("sslmode", "require")
        parsed_url = parsed_url.set(query=query)
        url = str(parsed_url)

    # Convert to psycopg driver for sync operations
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
