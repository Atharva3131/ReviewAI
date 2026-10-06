"""
Database configuration and session management for Amazon RDS PostgreSQL and local database environments.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base declarative class
Base = declarative_base()

# Build database URLs cleanly
database_url = settings.DATABASE_URL
if settings.DB_HOST and settings.DB_USER and settings.DB_PASSWORD:
    database_url = (
        f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@"
        f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )

# Async URL for asyncpg driver
async_database_url = database_url
if async_database_url.startswith("postgresql://"):
    async_database_url = async_database_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    )

# Sync URL for Alembic migrations using psycopg driver
sync_database_url = database_url
if sync_database_url.startswith("postgresql://"):
    sync_database_url = sync_database_url.replace(
        "postgresql://", "postgresql+psycopg://"
    )

# Connection kwargs for SSL / RDS compatibility
async_connect_args: Dict[str, Any] = {}
if settings.DB_SSL:
    async_connect_args["ssl"] = "require"

# Engine kwargs for production connection pooling
async_engine_kwargs: Dict[str, Any] = {
    "echo": settings.DEBUG,
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_timeout": settings.DB_POOL_TIMEOUT,
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}

if async_connect_args:
    async_engine_kwargs["connect_args"] = async_connect_args

# Async engine for main application operations
async_engine = create_async_engine(async_database_url, **async_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Sync engine for Alembic and migration scripts
sync_engine = create_engine(sync_database_url, echo=settings.DEBUG, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_db():
    """Dependency to get sync database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def get_async_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager to get async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database for local/demo environment. In production, use Alembic migrations."""
    import app.models  # ensure models registered

    if settings.APP_ENV.lower() in ("production", "prod", "staging"):
        logger.info("Production environment detected: Skipping Base.metadata.create_all (use Alembic migrations)")
        return

    logger.info("Initializing database tables via Base.metadata.create_all for development...")
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.warning(f"Database table initialization warning: {e}")
