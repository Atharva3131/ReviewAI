"""
Main API router for v1 endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    auth,
    billing,
    customers,
    dashboard,
    health,
    privacy,
    reviews,
    support_tickets,
    users,
    webhooks,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(
    privacy.router, prefix="/privacy", tags=["privacy", "compliance"]
)
api_router.include_router(
    billing.router, prefix="/billing", tags=["billing", "subscriptions"]
)
api_router.include_router(
    support_tickets.router, prefix="/support-tickets", tags=["support", "tickets"]
)
api_router.include_router(health.router, tags=["health"])
