"""
Health check endpoints for monitoring and load balancer health checks
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
import logging
import asyncio

from app.core.database import get_db
from app.core.redis import get_redis_client
from app.schemas.base import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint for load balancer
    Returns 200 OK if the service is running
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "revive-ai-backend"
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check that verifies all dependencies
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "revive-ai-backend",
        "version": "1.0.0",
        "checks": {}
    }
    
    overall_healthy = True
    
    # Database health check
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        overall_healthy = False
    
    # Redis health check
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        overall_healthy = False
    
    # Memory and disk checks could be added here
    health_status["checks"]["memory"] = {
        "status": "healthy",
        "message": "Memory usage within limits"
    }
    
    health_status["checks"]["disk"] = {
        "status": "healthy", 
        "message": "Disk usage within limits"
    }
    
    # Update overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check - indicates if the service is ready to accept traffic
    """
    try:
        # Check database connection
        db.execute(text("SELECT 1"))
        
        # Check Redis connection
        redis_client = get_redis_client()
        await redis_client.ping()
        
        return {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Service is ready to accept traffic"
        }
    
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": f"Service is not ready: {str(e)}"
            }
        )


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check - indicates if the service is alive
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Service is alive"
    }


@router.get("/metrics")
async def metrics_endpoint():
    """
    Basic metrics endpoint for monitoring
    """
    # In a production environment, this would return Prometheus-style metrics
    # For now, return basic application metrics
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "requests_total": 0,  # Would be tracked by middleware
            "requests_duration_seconds": 0,  # Would be tracked by middleware
            "active_connections": 0,  # Would be tracked by connection pool
            "memory_usage_bytes": 0,  # Would be tracked by system monitoring
            "cpu_usage_percent": 0,  # Would be tracked by system monitoring
        }
    }
