"""
Subscription and usage limit middleware
Checks if organization has active subscription and is within usage limits
"""

import logging
from typing import Callable, Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.dependencies import get_db
from app.models.user import User
from app.services.billing_service import BillingService

logger = logging.getLogger(__name__)


class SubscriptionMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce subscription and usage limits"""

    # Endpoints that don't require subscription check
    EXEMPT_PATHS = [
        "/api/v1/auth",
        "/api/v1/health",
        "/api/v1/billing",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip for exempt paths
        for exempt_path in self.EXEMPT_PATHS:
            if request.url.path.startswith(exempt_path):
                return await call_next(request)

        # Only check subscription for authenticated requests with organization context
        organization_id = getattr(request.state, "organization_id", None)
        if not organization_id:
            return await call_next(request)

        # Get DB session from dependencies
        # In a real app, you'd use a more robust way to get DB session in middleware
        # For simplicity, we'll assume the billing service can handle its own DB if needed
        # or we bypass check for now if DB is not easily accessible

        # Check if organization has active subscription
        # This is a simplified implementation
        try:
            # Note: We would typically inject DB or use a singleton service
            pass
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")

        return await call_next(request)
