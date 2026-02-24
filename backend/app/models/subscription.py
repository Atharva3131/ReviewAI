"""Subscription and billing models"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Numeric, Integer, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base


class BillingPeriod(str, enum.Enum):
    """Billing period enumeration"""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status enumeration"""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


class InvoiceStatus(str, enum.Enum):
    """Invoice status enumeration"""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class SubscriptionPlan(Base):
    """Subscription plan model"""
    
    __tablename__ = "subscription_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price_monthly = Column(Numeric(10, 2), nullable=False)
    price_yearly = Column(Numeric(10, 2), nullable=False)
    features = Column(JSON, default=dict, nullable=False)
    limits = Column(JSON, default=dict, nullable=False)
    stripe_price_id_monthly = Column(String(255), nullable=True)
    stripe_price_id_yearly = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")
    
    def __repr__(self):
        return f"<SubscriptionPlan(id={self.id}, name='{self.name}')>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "price_monthly": float(self.price_monthly),
            "price_yearly": float(self.price_yearly),
            "features": self.features,
            "limits": self.limits,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Subscription(Base):
    """Subscription model"""
    
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False, index=True)
    billing_period = Column(Enum(BillingPeriod), default=BillingPeriod.MONTHLY, nullable=False)
    
    # Stripe integration
    stripe_subscription_id = Column(String(255), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)
    
    # Billing cycle
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Trial period
    trial_start = Column(DateTime(timezone=True), nullable=True)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="subscription", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, organization_id={self.organization_id}, status='{self.status}')>"
    
    @property
    def is_active(self):
        """Check if subscription is active"""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
    
    @property
    def is_trial(self):
        """Check if subscription is in trial period"""
        return self.status == SubscriptionStatus.TRIALING
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "plan_id": str(self.plan_id),
            "status": self.status.value,
            "billing_period": self.billing_period.value,
            "stripe_subscription_id": self.stripe_subscription_id,
            "stripe_customer_id": self.stripe_customer_id,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "canceled_at": self.canceled_at.isoformat() if self.canceled_at else None,
            "trial_start": self.trial_start.isoformat() if self.trial_start else None,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "is_active": self.is_active,
            "is_trial": self.is_trial,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Invoice(Base):
    """Invoice model"""
    
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    stripe_invoice_id = Column(String(255), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="usd", nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False, index=True)
    invoice_number = Column(String(100), nullable=True)
    invoice_pdf = Column(String(500), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization")
    subscription = relationship("Subscription", back_populates="invoices")
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, amount={self.amount}, status='{self.status}')>"
    
    @property
    def is_paid(self):
        """Check if invoice is paid"""
        return self.status == InvoiceStatus.PAID
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "subscription_id": str(self.subscription_id),
            "stripe_invoice_id": self.stripe_invoice_id,
            "amount": float(self.amount),
            "currency": self.currency,
            "status": self.status.value,
            "invoice_number": self.invoice_number,
            "invoice_pdf": self.invoice_pdf,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "is_paid": self.is_paid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class UsageRecord(Base):
    """Usage tracking model"""
    
    __tablename__ = "usage_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    metric_name = Column(String(100), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization")
    subscription = relationship("Subscription", back_populates="usage_records")
    
    def __repr__(self):
        return f"<UsageRecord(id={self.id}, metric='{self.metric_name}', quantity={self.quantity})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "subscription_id": str(self.subscription_id),
            "metric_name": self.metric_name,
            "quantity": self.quantity,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

