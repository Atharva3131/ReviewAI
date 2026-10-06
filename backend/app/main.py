"""
FastAPI Application Entry Point for ReviewAI
Configured for production AWS deployment (ECS, RDS, Bedrock, S3).
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_engine, init_db
from app.core.secrets import inject_secrets_to_env
from app.services.storage import get_storage_service

# Import API endpoints
from app.api.v1.endpoints import (
    agents,
    customers,
    dashboard,
    demo,
    reviews,
    webhooks,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle manager"""
    logger.info(f"Starting {settings.PROJECT_NAME} in environment: {settings.APP_ENV}")

    # Inject secrets from AWS Secrets Manager if configured
    try:
        inject_secrets_to_env()
    except Exception as e:
        logger.warning(f"Secrets injection notice: {e}")

    # Initialize local/dev database schema (skipped automatically in production)
    try:
        await init_db()
    except Exception as e:
        logger.warning(f"Database startup notice: {e}")

    yield

    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered review analysis and customer recovery platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG or settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.DEBUG or settings.APP_ENV != "production" else None,
)

# Add CORS middleware with configurable origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"])
app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(demo.router, prefix="/api/v1/demo", tags=["demo"])


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Lightweight process health check endpoint for ALB / ECS target groups"""
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "service": settings.PROJECT_NAME,
    }


@app.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check verifying database connectivity and configuration"""
    db_status = "ok"
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unreachable ({type(e).__name__})"

    return {
        "status": "ready" if db_status == "ok" else "degraded",
        "database": db_status,
        "llm_provider": settings.LLM_PROVIDER,
        "bedrock_model_id": settings.BEDROCK_MODEL_ID,
        "aws_region": settings.AWS_REGION,
        "s3_bucket": settings.AWS_S3_BUCKET or "not_configured (using local fallback)",
    }
