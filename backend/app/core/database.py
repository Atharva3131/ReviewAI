"""
Database configuration and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Convert sync URL to async URL for asyncpg
async_database_url = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# For sync operations (Alembic), use psycopg driver
sync_database_url = settings.DATABASE_URL
if sync_database_url.startswith("postgresql://"):
    sync_database_url = sync_database_url.replace(
        "postgresql://", "postgresql+psycopg://"
    )

# Async engine for main operations
async_engine = create_async_engine(async_database_url, echo=True)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Sync engine for migrations
sync_engine = create_engine(sync_database_url, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()


async def get_async_db():
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


async def init_db():
    """Initialize database"""
    # Import all models here to ensure they are registered
    from app.models import (
        agent_decision,
        customer,
        organization,
        recovery_action,
        review,
        support_ticket,
        user,
    )

    # Note: embedding model requires pgvector extension - enable it in Supabase first
    # from app.models import embedding

    # Create tables (in production, use Alembic migrations)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


from contextlib import asynccontextmanager


@asynccontextmanager
async def get_async_db_context():
    """Context manager to get async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
