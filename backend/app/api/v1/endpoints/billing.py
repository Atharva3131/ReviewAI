"""Billing and subscription API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import stripe

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.billing_service import BillingService
from app.schemas.billing import (
    SubscriptionPlanResponse,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    InvoiceResponse,
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    BillingPortalSessionCreate,
    BillingPortalSessionResponse,
    UsageRecordCreate,
    UsageRecordResponse,
    BillingOverviewResponse
)
from app.core.config import settings

router = APIRouter()


@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get all available subscription plans"""
    billing_service = BillingService(db)
    plans = billing_service.get_subscription_plans(active_only=active_only)
    return [SubscriptionPlanResponse.model_validate(plan) for plan in plans]


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def get_subscription_plan(
    plan_id: str,
    db: Session = Depends(get_db)
):
    """Get subscription plan by ID"""
    billing_service = BillingService(db)
    plan = billing_service.get_subscription_plan(plan_id)
    return SubscriptionPlanResponse.model_validate(plan)


@router.get("/subscription", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current organization's subscription"""
    billing_service = BillingService(db)
    subscription = billing_service.get_organization_subscription(
        str(current_user.organization_id)
    )
    
    if not subscription:
        return None
    
    # Load plan relationship
    db.refresh(subscription)
    return SubscriptionResponse.model_validate(subscription)


@router.post("/subscription", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new subscription for the organization"""
    billing_service = BillingService(db)
    subscription = billing_service.create_subscription(
        str(current_user.organization_id),
        subscription_data
    )
    
    db.refresh(subscription)
    return SubscriptionResponse.model_validate(subscription)


@router.patch("/subscription/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    update_data: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update subscription"""
    billing_service = BillingService(db)
    subscription = billing_service.update_subscription(
        subscription_id,
        str(current_user.organization_id),
        update_data
    )
    
    db.refresh(subscription)
    return SubscriptionResponse.model_validate(subscription)


@router.post("/subscription/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    immediate: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel subscription"""
    billing_service = BillingService(db)
    subscription = billing_service.cancel_subscription(
        subscription_id,
        str(current_user.organization_id),
        immediate=immediate
    )
    
    db.refresh(subscription)
    return SubscriptionResponse.model_validate(subscription)


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    checkout_data: CheckoutSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session"""
    billing_service = BillingService(db)
    session = billing_service.create_checkout_session(
        str(current_user.organization_id),
        checkout_data
    )
    return CheckoutSessionResponse(**session)


@router.post("/portal", response_model=BillingPortalSessionResponse)
async def create_billing_portal_session(
    portal_data: BillingPortalSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe billing portal session"""
    billing_service = BillingService(db)
    session = billing_service.create_billing_portal_session(
        str(current_user.organization_id),
        portal_data
    )
    return BillingPortalSessionResponse(**session)


@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get organization's invoices"""
    billing_service = BillingService(db)
    invoices = billing_service.get_organization_invoices(
        str(current_user.organization_id),
        limit=limit
    )
    return [InvoiceResponse.model_validate(inv) for inv in invoices]


@router.get("/overview", response_model=BillingOverviewResponse)
async def get_billing_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complete billing overview"""
    billing_service = BillingService(db)
    overview = billing_service.get_billing_overview(
        str(current_user.organization_id)
    )
    
    # Convert to response model
    return BillingOverviewResponse(
        subscription=SubscriptionResponse(**overview["subscription"]) if overview["subscription"] else None,
        upcoming_invoice=InvoiceResponse(**overview["upcoming_invoice"]) if overview.get("upcoming_invoice") else None,
        recent_invoices=[InvoiceResponse(**inv) for inv in overview["recent_invoices"]],
        usage=overview.get("usage"),
        payment_method=None  # TODO: Implement payment method retrieval from Stripe
    )


@router.post("/usage", response_model=UsageRecordResponse, status_code=status.HTTP_201_CREATED)
async def record_usage(
    usage_data: UsageRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record usage for the organization"""
    billing_service = BillingService(db)
    usage_record = billing_service.record_usage(
        str(current_user.organization_id),
        usage_data
    )
    return UsageRecordResponse.model_validate(usage_record)


@router.get("/usage")
async def get_usage_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage summary for current billing period"""
    billing_service = BillingService(db)
    usage = billing_service.get_usage_summary(
        str(current_user.organization_id)
    )
    return usage


@router.get("/usage/limits")
async def check_usage_limits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if organization is within usage limits"""
    billing_service = BillingService(db)
    limits_check = billing_service.check_usage_limits(
        str(current_user.organization_id)
    )
    return limits_check


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events"""
    if not hasattr(settings, 'STRIPE_WEBHOOK_SECRET') or not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Stripe webhooks not configured"
        )
    
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    billing_service = BillingService(db)
    billing_service.handle_stripe_webhook(event["type"], event["data"])
    
    return {"status": "success"}

