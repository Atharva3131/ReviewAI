"""
Subscription and usage limit middleware
Checks if organization has active subscription and is within usage limits
"""
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.dependencies import get_db
from app.services.billing_service import BillingService
from app.models.user import User

logger = logging.getLogger(__name__)


class SubscriptionMiddleware:
    """Middleware to enforce subscription and usage limits"""
    
    # Endpoints that don't require subscription check
    EXEMPT_PATHS = [
        "/api/v1/auth",
        "/api/v1/health",
