"""
Revive AI - Main FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from contextlib import asynccontextmanager
import logging
import time
from typing import Union

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import init_db
from app.core.middleware import (
    ErrorHandlingMiddleware,
    AuthenticationMiddleware,
    RequestLoggingMiddleware,
    RateLimitingMiddleware,
    SecurityHeadersMiddleware,
    OrganizationIsolationMiddleware
)
from app.core.security_middleware import (
    CSRFProtectionMiddleware,
    InputSanitizationMiddleware,
    AdvancedSecurityHeadersMiddleware,
    IPWhitelistMiddleware,
    DDoSProtectionMiddleware,
    AuditLoggingMiddleware
)
from app.api.versioning import APIVersionMiddleware
from app.core.openapi import OpenAPICustomizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Revive AI API...")
    await init_db()
    logger.info("Database initialized successfully")
    
    # Initialize Redis
    from app.core.redis import redis_client
    await redis_client.connect()
    logger.info("Redis initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Revive AI API...")
    await redis_client.disconnect()
    logger.info("Redis disconnected")


# Create FastAPI application with comprehensive configuration
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
# Revive AI - AI-Powered Reputation Intelligence & Customer Recovery Platform

## Overview
Revive AI is a comprehensive SaaS platform that helps businesses monitor public reviews, analyze customer conversations, predict churn risks, and take automated recovery actions to improve ratings, retention, and revenue.

## Key Features
- **Review Intelligence Engine**: Automated sentiment analysis, urgency classification, and issue categorization
- **Customer Recovery Agent**: Predictive churn risk assessment and automated recovery action generation
- **Agent Orchestration**: Intelligent decision-making for routing customer issues
- **LLM Integration**: Multi-provider AI integration for response generation
- **Background Processing**: Scalable task queue system for asynchronous operations

## Authentication
All API endpoints (except public ones) require authentication using JWT Bearer tokens.

### Getting Started
1. Register a new account: `POST /api/v1/auth/register`
2. Login to get access token: `POST /api/v1/auth/login`
3. Include token in requests: `Authorization: Bearer <your_token>`

## Rate Limiting
API requests are rate-limited based on user tier:
- **Anonymous**: 100 requests/hour
- **Authenticated**: 1,000 requests/hour
- **Premium**: 5,000 requests/hour
- **Admin**: 10,000 requests/hour

Endpoint-specific limits may also apply. Rate limit information is included in response headers.

## Error Handling
All errors follow a consistent format:
```json
{
  "error": {
    "type": "error_type",
    "message": "Human-readable message",
    "status_code": 400,
    "request_id": "unique-id",
    "timestamp": 1640995200.0,
    "path": "/api/v1/endpoint"
  }
}
```

## Versioning
The API supports multiple versioning strategies:
- **URL Path**: `/api/v1/endpoint` (recommended)
- **Accept Header**: `Accept: application/vnd.revive-ai.v1+json`
- **Query Parameter**: `/api/endpoint?version=v1`

Current version: **v1** (stable)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    contact={
        "name": "Revive AI Support",
        "email": "support@revive-ai.com",
        "url": "https://revive-ai.com/support"
    },
    license_info={
        "name": "Proprietary License",
        "url": "https://revive-ai.com/license"
    },
    terms_of_service="https://revive-ai.com/terms",
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.revive-ai.com",
            "description": "Production server"
        },
        {
            "url": "https://staging-api.revive-ai.com",
            "description": "Staging server"
        }
    ],
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and system status endpoints"
        },
        {
            "name": "auth",
            "description": "Authentication and authorization endpoints"
        },
        {
            "name": "reviews",
            "description": "Review intelligence and management endpoints"
        },
        {
            "name": "customers",
            "description": "Customer management and recovery endpoints"
        },
        {
            "name": "agents",
            "description": "Agent orchestration and decision endpoints"
        },
        {
            "name": "dashboard",
            "description": "Dashboard metrics and analytics endpoints"
        },
        {
            "name": "users",
            "description": "User management endpoints"
        },
        {
            "name": "monitoring",
            "description": "System monitoring and metrics endpoints"
        },
        {
            "name": "versioning",
            "description": "API versioning information endpoints"
        }
    ]
)

# Add middleware in correct order (last added = first executed)
app.add_middleware(AdvancedSecurityHeadersMiddleware)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(DDoSProtectionMiddleware, max_requests_per_minute=100, max_requests_per_second=10)
app.add_middleware(InputSanitizationMiddleware)
# CSRF disabled for API endpoints (they use JWT Bearer tokens, not cookies)
# app.add_middleware(CSRFProtectionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(OrganizationIsolationMiddleware)
app.add_middleware(RateLimitingMiddleware, use_sliding_window=True)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(APIVersionMiddleware)
app.add_middleware(RequestLoggingMiddleware, log_body=settings.DEBUG, log_headers=settings.DEBUG)
app.add_middleware(ErrorHandlingMiddleware)  # Add error handling as the first middleware

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
)

# Set up custom OpenAPI documentation
# Temporarily disabled to use FastAPI's default OpenAPI
# OpenAPICustomizer.setup_custom_openapi(app)


# Include API router with versioning
app.include_router(api_router, prefix=settings.API_V1_STR)


# Root endpoints
@app.get("/", tags=["health"])
async def root():
    """
    Root endpoint with basic API information
    
    Returns basic information about the Revive AI API including version,
    status, and links to documentation.
    """
    return {
        "message": "Revive AI API",
        "version": "1.0.0",
        "description": "AI-Powered Reputation Intelligence & Customer Recovery Platform",
        "docs_url": "/docs" if settings.DEBUG else None,
        "redoc_url": "/redoc" if settings.DEBUG else None,
        "status": "operational",
        "features": [
            "Review Intelligence Engine",
            "Customer Recovery Agent", 
            "Agent Orchestration",
            "LLM Integration",
            "Background Processing"
        ]
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Comprehensive health check endpoint
    
    Performs health checks on all system components including database,
    Redis, and background task system. Returns detailed status information.
    """
    # TODO: Add actual health checks for each component
    health_status = {
        "status": "healthy",
        "service": "revive-ai-api",
        "version": "1.0.0",
        "timestamp": int(time.time()),
        "environment": "development" if settings.DEBUG else "production",
        "components": {
            "database": {
                "status": "healthy",
                "response_time_ms": 5,
                "last_check": int(time.time())
            },
            "redis": {
                "status": "healthy", 
                "response_time_ms": 2,
                "last_check": int(time.time())
            },
            "celery": {
                "status": "healthy",
                "active_workers": 3,
                "last_check": int(time.time())
            },
            "llm_providers": {
                "status": "healthy",
                "available_providers": ["openai", "mock"],
                "last_check": int(time.time())
            }
        },
        "uptime_seconds": 3600,  # TODO: Calculate actual uptime
        "memory_usage_mb": 256,  # TODO: Get actual memory usage
        "cpu_usage_percent": 15  # TODO: Get actual CPU usage
    }
    
    # Determine overall status
    component_statuses = [comp["status"] for comp in health_status["components"].values()]
    if all(status == "healthy" for status in component_statuses):
        health_status["status"] = "healthy"
    elif any(status == "unhealthy" for status in component_statuses):
        health_status["status"] = "unhealthy"
    else:
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/docs/api", tags=["documentation"])
async def api_documentation():
    """
    Get comprehensive API documentation in markdown format
    
    Returns detailed API documentation including examples, best practices,
    and integration guides.
    """
    from app.core.openapi import generate_api_documentation
    
    return {
        "title": "Revive AI API Documentation",
        "version": "1.0.0",
        "content": generate_api_documentation(),
        "format": "markdown",
        "last_updated": int(time.time())
    }


@app.get("/openapi.json", tags=["documentation"], include_in_schema=False)
async def get_openapi_schema():
    """
    Get the OpenAPI schema in JSON format
    
    Returns the complete OpenAPI 3.0 schema for the API.
    Only available in development mode.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=404,
            detail="OpenAPI schema not available in production"
        )
    
    return app.openapi()


@app.get("/versions", tags=["versioning"])
async def get_api_versions():
    """
    Get information about supported API versions
    
    Returns comprehensive information about all supported API versions,
    their status, and available versioning strategies.
    """
    from app.api.versioning import APIVersionManager
    return {
        "current_version": APIVersionManager.CURRENT_VERSION.value,
        "default_version": APIVersionManager.DEFAULT_VERSION.value,
        "supported_versions": APIVersionManager.get_supported_versions(),
        "versioning_strategies": [
            {
                "name": "URL Path",
                "description": "Include version in URL path",
                "example": "/api/v1/endpoint",
                "recommended": True
            },
            {
                "name": "Accept Header", 
                "description": "Specify version in Accept header",
                "example": "Accept: application/vnd.revive-ai.v1+json",
                "recommended": False
            },
            {
                "name": "Query Parameter",
                "description": "Specify version as query parameter", 
                "example": "/api/endpoint?version=v1",
                "recommended": False
            }
        ],
        "migration_guides": {
            "v1_to_v2": "https://docs.revive-ai.com/migration/v1-to-v2"
        }
    }


@app.get("/metrics", tags=["monitoring"])
async def metrics():
    """Comprehensive metrics endpoint for monitoring"""
    from app.core.middleware import MetricsCollector
    
    # Get system metrics
    system_metrics = await MetricsCollector.get_system_metrics()
    
    # Get endpoint metrics
    endpoint_metrics = await MetricsCollector.get_endpoint_metrics()
    
    # Get top endpoints by request count
    top_endpoints = sorted(
        endpoint_metrics.items(),
        key=lambda x: x[1]["request_count"],
        reverse=True
    )[:10]
    
    return {
        "system": system_metrics,
        "endpoints": {
            "summary": {
                "total_endpoints": len(endpoint_metrics),
                "top_endpoints": dict(top_endpoints)
            },
            "detailed": endpoint_metrics
        },
        "timestamp": int(time.time()),
        "collection_period": "24 hours"
    }


@app.get("/metrics/endpoint/{endpoint:path}", tags=["monitoring"])
async def endpoint_metrics(endpoint: str):
    """Get metrics for a specific endpoint"""
    from app.core.middleware import MetricsCollector
    
    # Ensure endpoint starts with /
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    
    metrics = await MetricsCollector.get_endpoint_metrics(endpoint)
    
    if endpoint not in metrics:
        raise HTTPException(
            status_code=404,
            detail=f"No metrics found for endpoint: {endpoint}"
        )
    
    return {
        "endpoint": endpoint,
        "metrics": metrics[endpoint],
        "timestamp": int(time.time())
    }


@app.post("/metrics/reset", tags=["monitoring"])
async def reset_metrics():
    """Reset all metrics (admin only)"""
    from app.core.middleware import MetricsCollector
    
    # TODO: Add admin authentication check
    await MetricsCollector.reset_metrics()
    
    return {
        "message": "Metrics reset successfully",
        "timestamp": int(time.time())
    }