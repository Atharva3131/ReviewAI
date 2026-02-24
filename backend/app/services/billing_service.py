"""Billing service with Stripe integration"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
import stripe
import uuid

from app.models.subscription import (
    SubscriptionPlan, Subscription, Invoice, UsageRecord,
    SubscriptionStatus, InvoiceStatus, BillingPeriod
)
from app.schemas.billing import (
    SubscriptionCreate, SubscriptionUpdate,
    CheckoutSessionCreate, BillingPortalSessionCreate,
    UsageRecordCreate
)
from app.core.config import settings
from app.core.exceptions import ValidationError, NotFoundError


class BillingService:
    """Service for handling billing and subscription operations"""
    
    def __init__(self, db: Session):
        self.db = db
        # Initialize Stripe if API key is available
        if hasattr(settings, 'STRIPE_SECRET_KEY') and settings.STRIPE_SECRET_KEY:
            stripe.api_key = settings.STRIPE_SECRET_KEY
    
    # Subscription Plan Management
    
    def get_subscription_plans(self, active_only: bool = True) -> List[SubscriptionPlan]:
        """Get all subscription plans"""
        query = self.db.query(SubscriptionPlan)
        if active_only:
            query = query.filter(SubscriptionPlan.is_active == True)
        return query.all()
    
    def get_subscription_plan(self, plan_id: str) -> SubscriptionPlan:
        """Get subscription plan by ID"""
        plan = self.db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == plan_id
        ).first()
        if not plan:
            raise NotFoundError(f"Subscription plan {plan_id} not found")
        return plan
    
    # Subscription Management
    
    def get_organization_subscription(self, organization_id: str) -> Optional[Subscription]:
        """Get active subscription for organization"""
        return self.db.query(Subscription).filter(
            and_(
                Subscription.organization_id == organization_id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
            )
        ).first()
    
    def create_subscription(
        self, 
        organization_id: str, 
        subscription_data: SubscriptionCreate
    ) -> Subscription:
        """Create a new subscription"""
        # Validate plan exists
        plan = self.get_subscription_plan(subscription_data.plan_id)
        
        # Check if organization already has active subscription
        existing = self.get_organization_subscription(organization_id)
        if existing:
            raise ValidationError("Organization already has an active subscription")
        
        # Calculate trial period if specified
        trial_start = None
        trial_end = None
        status = SubscriptionStatus.ACTIVE
        
        if subscription_data.trial_days and subscription_data.trial_days > 0:
            trial_start = datetime.now(timezone.utc)
            trial_end = trial_start + timedelta(days=subscription_data.trial_days)
            status = SubscriptionStatus.TRIALING
        
        # Calculate billing period
        current_period_start = datetime.now(timezone.utc)
        if subscription_data.billing_period == "monthly":
            current_period_end = current_period_start + timedelta(days=30)
        else:  # yearly
            current_period_end = current_period_start + timedelta(days=365)
        
        # Create subscription
        subscription = Subscription(
            id=uuid.uuid4(),
            organization_id=organization_id,
            plan_id=subscription_data.plan_id,
            status=status,
            billing_period=BillingPeriod(subscription_data.billing_period),
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            trial_start=trial_start,
            trial_end=trial_end
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    def update_subscription(
        self, 
        subscription_id: str, 
        organization_id: str,
        update_data: SubscriptionUpdate
    ) -> Subscription:
        """Update subscription"""
        subscription = self.db.query(Subscription).filter(
            and_(
                Subscription.id == subscription_id,
                Subscription.organization_id == organization_id
            )
        ).first()
        
        if not subscription:
            raise NotFoundError(f"Subscription {subscription_id} not found")
        
        # Update fields
        if update_data.plan_id:
            plan = self.get_subscription_plan(update_data.plan_id)
            subscription.plan_id = update_data.plan_id
        
        if update_data.billing_period:
            subscription.billing_period = BillingPeriod(update_data.billing_period)
        
        if update_data.cancel_at_period_end is not None:
            subscription.cancel_at_period_end = update_data.cancel_at_period_end
            if update_data.cancel_at_period_end:
                subscription.canceled_at = datetime.now(timezone.utc)
        
        subscription.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    def cancel_subscription(
        self, 
        subscription_id: str, 
        organization_id: str,
        immediate: bool = False
    ) -> Subscription:
        """Cancel subscription"""
        subscription = self.db.query(Subscription).filter(
            and_(
                Subscription.id == subscription_id,
                Subscription.organization_id == organization_id
            )
        ).first()
        
        if not subscription:
            raise NotFoundError(f"Subscription {subscription_id} not found")
        
        if immediate:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.now(timezone.utc)
        else:
            subscription.cancel_at_period_end = True
            subscription.canceled_at = datetime.now(timezone.utc)
        
        subscription.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    # Stripe Integration
    
    def create_checkout_session(
        self, 
        organization_id: str,
        checkout_data: CheckoutSessionCreate
    ) -> Dict[str, str]:
        """Create Stripe checkout session"""
        if not hasattr(settings, 'STRIPE_SECRET_KEY') or not settings.STRIPE_SECRET_KEY:
            raise ValidationError("Stripe is not configured")
        
        plan = self.get_subscription_plan(checkout_data.plan_id)
        
        # Determine price based on billing period
        if checkout_data.billing_period == "monthly":
            price = float(plan.price_monthly)
            stripe_price_id = plan.stripe_price_id_monthly
        else:
            price = float(plan.price_yearly)
            stripe_price_id = plan.stripe_price_id_yearly
        
        # Create Stripe checkout session
        try:
            session_params = {
                "payment_method_types": ["card"],
                "line_items": [{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": plan.name,
                            "description": plan.description or ""
                        },
                        "unit_amount": int(price * 100),  # Convert to cents
                        "recurring": {
                            "interval": "month" if checkout_data.billing_period == "monthly" else "year"
                        }
                    },
                    "quantity": 1
                }],
                "mode": "subscription",
                "success_url": checkout_data.success_url,
                "cancel_url": checkout_data.cancel_url,
                "client_reference_id": str(organization_id),
                "metadata": {
                    "organization_id": str(organization_id),
                    "plan_id": str(checkout_data.plan_id),
                    "billing_period": checkout_data.billing_period
                }
            }
            
            # Add trial period if specified
            if checkout_data.trial_days and checkout_data.trial_days > 0:
                session_params["subscription_data"] = {
                    "trial_period_days": checkout_data.trial_days
                }
            
            session = stripe.checkout.Session.create(**session_params)
            
            return {
                "session_id": session.id,
                "url": session.url
            }
        except stripe.error.StripeError as e:
            raise ValidationError(f"Stripe error: {str(e)}")
    
    def create_billing_portal_session(
        self, 
        organization_id: str,
        portal_data: BillingPortalSessionCreate
    ) -> Dict[str, str]:
        """Create Stripe billing portal session"""
        if not hasattr(settings, 'STRIPE_SECRET_KEY') or not settings.STRIPE_SECRET_KEY:
            raise ValidationError("Stripe is not configured")
        
        subscription = self.get_organization_subscription(organization_id)
        if not subscription or not subscription.stripe_customer_id:
            raise ValidationError("No active subscription with Stripe customer found")
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=portal_data.return_url
            )
            
            return {"url": session.url}
        except stripe.error.StripeError as e:
            raise ValidationError(f"Stripe error: {str(e)}")
    
    def handle_stripe_webhook(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Handle Stripe webhook events"""
        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(event_data)
        elif event_type == "customer.subscription.updated":
            self._handle_subscription_updated(event_data)
        elif event_type == "customer.subscription.deleted":
            self._handle_subscription_deleted(event_data)
        elif event_type == "invoice.paid":
            self._handle_invoice_paid(event_data)
        elif event_type == "invoice.payment_failed":
            self._handle_invoice_payment_failed(event_data)
    
    def _handle_checkout_completed(self, data: Dict[str, Any]) -> None:
        """Handle successful checkout"""
        session = data.get("object", {})
        organization_id = session.get("metadata", {}).get("organization_id")
        plan_id = session.get("metadata", {}).get("plan_id")
        billing_period = session.get("metadata", {}).get("billing_period", "monthly")
        
        if not organization_id or not plan_id:
            return
        
        # Create or update subscription
        subscription = self.get_organization_subscription(organization_id)
        if not subscription:
            subscription_data = SubscriptionCreate(
                plan_id=plan_id,
                billing_period=billing_period
            )
            subscription = self.create_subscription(organization_id, subscription_data)
        
        # Update with Stripe data
        subscription.stripe_subscription_id = session.get("subscription")
        subscription.stripe_customer_id = session.get("customer")
        subscription.status = SubscriptionStatus.ACTIVE
        
        self.db.commit()
    
    def _handle_subscription_updated(self, data: Dict[str, Any]) -> None:
        """Handle subscription update"""
        stripe_subscription = data.get("object", {})
        stripe_subscription_id = stripe_subscription.get("id")
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_subscription_id
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus(stripe_subscription.get("status", "active"))
            subscription.current_period_start = datetime.fromtimestamp(
                stripe_subscription.get("current_period_start"), tz=timezone.utc
            )
            subscription.current_period_end = datetime.fromtimestamp(
                stripe_subscription.get("current_period_end"), tz=timezone.utc
            )
            subscription.cancel_at_period_end = stripe_subscription.get("cancel_at_period_end", False)
            
            self.db.commit()
    
    def _handle_subscription_deleted(self, data: Dict[str, Any]) -> None:
        """Handle subscription deletion"""
        stripe_subscription = data.get("object", {})
        stripe_subscription_id = stripe_subscription.get("id")
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_subscription_id
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.now(timezone.utc)
            self.db.commit()
    
    def _handle_invoice_paid(self, data: Dict[str, Any]) -> None:
        """Handle successful invoice payment"""
        stripe_invoice = data.get("object", {})
        stripe_subscription_id = stripe_invoice.get("subscription")
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_subscription_id
        ).first()
        
        if subscription:
            # Create or update invoice record
            invoice = self.db.query(Invoice).filter(
                Invoice.stripe_invoice_id == stripe_invoice.get("id")
            ).first()
            
            if not invoice:
                invoice = Invoice(
                    id=uuid.uuid4(),
                    organization_id=subscription.organization_id,
                    subscription_id=subscription.id,
                    stripe_invoice_id=stripe_invoice.get("id"),
                    amount=stripe_invoice.get("amount_paid", 0) / 100,
                    currency=stripe_invoice.get("currency", "usd"),
                    status=InvoiceStatus.PAID,
                    invoice_number=stripe_invoice.get("number"),
                    invoice_pdf=stripe_invoice.get("invoice_pdf"),
                    paid_at=datetime.now(timezone.utc)
                )
                self.db.add(invoice)
            else:
                invoice.status = InvoiceStatus.PAID
                invoice.paid_at = datetime.now(timezone.utc)
            
            self.db.commit()
    
    def _handle_invoice_payment_failed(self, data: Dict[str, Any]) -> None:
        """Handle failed invoice payment"""
        stripe_invoice = data.get("object", {})
        stripe_subscription_id = stripe_invoice.get("subscription")
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_subscription_id
        ).first()
        
        if subscription:
            subscription.status = SubscriptionStatus.PAST_DUE
            self.db.commit()
    
    # Invoice Management
    
    def get_organization_invoices(
        self, 
        organization_id: str,
        limit: int = 10
    ) -> List[Invoice]:
        """Get invoices for organization"""
        return self.db.query(Invoice).filter(
            Invoice.organization_id == organization_id
        ).order_by(Invoice.created_at.desc()).limit(limit).all()
    
    def get_upcoming_invoice(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """Get upcoming invoice estimate"""
        subscription = self.get_organization_subscription(organization_id)
        if not subscription:
            return None
        
        # Calculate next invoice amount
        plan = subscription.plan
        if subscription.billing_period == BillingPeriod.MONTHLY:
            amount = float(plan.price_monthly)
        else:
            amount = float(plan.price_yearly)
        
        return {
            "amount": amount,
            "currency": "usd",
            "period_start": subscription.current_period_end,
            "period_end": subscription.current_period_end + timedelta(
                days=30 if subscription.billing_period == BillingPeriod.MONTHLY else 365
            )
        }
    
    # Usage Tracking
    
    def record_usage(
        self, 
        organization_id: str,
        usage_data: UsageRecordCreate
    ) -> UsageRecord:
        """Record usage for organization"""
        subscription = self.get_organization_subscription(organization_id)
        if not subscription:
            raise ValidationError("No active subscription found")
        
        usage_record = UsageRecord(
            id=uuid.uuid4(),
            organization_id=organization_id,
            subscription_id=subscription.id,
            metric_name=usage_data.metric_name,
            quantity=usage_data.quantity,
            period_start=usage_data.period_start,
            period_end=usage_data.period_end
        )
        
        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)
        
        return usage_record
    
    def get_usage_summary(
        self, 
        organization_id: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict[str, int]:
        """Get usage summary for organization"""
        subscription = self.get_organization_subscription(organization_id)
        if not subscription:
            return {}
        
        # Use current billing period if not specified
        if not period_start:
            period_start = subscription.current_period_start
        if not period_end:
            period_end = subscription.current_period_end
        
        # Query usage records
        usage_records = self.db.query(UsageRecord).filter(
            and_(
                UsageRecord.organization_id == organization_id,
                UsageRecord.period_start >= period_start,
                UsageRecord.period_end <= period_end
            )
        ).all()
        
        # Aggregate by metric
        usage_summary = {}
        for record in usage_records:
            if record.metric_name not in usage_summary:
                usage_summary[record.metric_name] = 0
            usage_summary[record.metric_name] += record.quantity
        
        return usage_summary
    
    def check_usage_limits(self, organization_id: str) -> Dict[str, Any]:
        """Check if organization is within usage limits"""
        subscription = self.get_organization_subscription(organization_id)
        if not subscription:
            return {"within_limits": False, "reason": "No active subscription"}
        
        plan = subscription.plan
        limits = plan.limits
        usage = self.get_usage_summary(organization_id)
        
        violations = []
        for metric, limit in limits.items():
            current_usage = usage.get(metric, 0)
            if current_usage > limit:
                violations.append({
                    "metric": metric,
                    "limit": limit,
                    "current": current_usage
                })
        
        return {
            "within_limits": len(violations) == 0,
            "violations": violations,
            "usage": usage,
            "limits": limits
        }
    
    def get_billing_overview(self, organization_id: str) -> Dict[str, Any]:
        """Get complete billing overview"""
        subscription = self.get_organization_subscription(organization_id)
        recent_invoices = self.get_organization_invoices(organization_id, limit=5)
        upcoming_invoice = self.get_upcoming_invoice(organization_id)
        usage = self.get_usage_summary(organization_id) if subscription else {}
        
        return {
            "subscription": subscription.to_dict() if subscription else None,
            "upcoming_invoice": upcoming_invoice,
            "recent_invoices": [inv.to_dict() for inv in recent_invoices],
            "usage": usage,
            "limits": subscription.plan.limits if subscription else {}
        }

