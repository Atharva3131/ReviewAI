"""Billing and subscription schemas"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal


class SubscriptionPlanBase(BaseModel):
    """Base subscription plan schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price_monthly: Decimal = Field(..., ge=0)
    price_yearly: Decimal = Field(..., ge=0)
    features: Dict[str, Any] = Field(default_factory=dict)
    limits: Dict[str, Any] = Field(default_factory=dict)


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """Schema for creating subscription plan"""
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None


class SubscriptionPlanUpdate(BaseModel):
    """Schema for updating subscription plan"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price_monthly: Optional[Decimal] = Field(None, ge=0)
    price_yearly: Optional[Decimal] = Field(None, ge=0)
    features: Optional[Dict[str, Any]] = None
    limits: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    """Schema for subscription plan response"""
    id: str
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    """Schema for creating subscription"""
    plan_id: str
    billing_period: str = Field(..., pattern="^(monthly|yearly)$")
    trial_days: Optional[int] = Field(None, ge=0, le=90)


class SubscriptionUpdate(BaseModel):
    """Schema for updating subscription"""
    plan_id: Optional[str] = None
    billing_period: Optional[str] = Field(None, pattern="^(monthly|yearly)$")
    cancel_at_period_end: Optional[bool] = None


class SubscriptionResponse(BaseModel):
    """Schema for subscription response"""
    id: str
    organization_id: str
    plan_id: str
    status: str
    billing_period: str
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    canceled_at: Optional[datetime] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    is_active: bool
    is_trial: bool
    created_at: datetime
    updated_at: datetime
    plan: Optional[SubscriptionPlanResponse] = None

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    """Schema for invoice response"""
    id: str
    organization_id: str
    subscription_id: str
    stripe_invoice_id: Optional[str] = None
    amount: Decimal
    currency: str
    status: str
    invoice_number: Optional[str] = None
    invoice_pdf: Optional[str] = None
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    is_paid: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsageRecordCreate(BaseModel):
    """Schema for creating usage record"""
    metric_name: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(..., ge=0)
    period_start: datetime
    period_end: datetime

    @field_validator('period_end')
    def validate_period(cls, v, values):
        if 'period_start' in values and v <= values['period_start']:
            raise ValueError('period_end must be after period_start')
        return v


class UsageRecordResponse(BaseModel):
    """Schema for usage record response"""
    id: str
    organization_id: str
    subscription_id: str
    metric_name: str
    quantity: int
    period_start: datetime
    period_end: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class CheckoutSessionCreate(BaseModel):
    """Schema for creating Stripe checkout session"""
    plan_id: str
    billing_period: str = Field(..., pattern="^(monthly|yearly)$")
    success_url: str
    cancel_url: str
    trial_days: Optional[int] = Field(None, ge=0, le=90)


class CheckoutSessionResponse(BaseModel):
    """Schema for checkout session response"""
    session_id: str
    url: str


class BillingPortalSessionCreate(BaseModel):
    """Schema for creating billing portal session"""
    return_url: str


class BillingPortalSessionResponse(BaseModel):
    """Schema for billing portal session response"""
    url: str


class WebhookEvent(BaseModel):
    """Schema for webhook event"""
    type: str
    data: Dict[str, Any]


class SubscriptionUsageResponse(BaseModel):
    """Schema for subscription usage response"""
    subscription_id: str
    current_period_start: datetime
    current_period_end: datetime
    usage: Dict[str, int]
    limits: Dict[str, int]
    usage_percentage: Dict[str, float]


class BillingOverviewResponse(BaseModel):
    """Schema for billing overview response"""
    subscription: Optional[SubscriptionResponse] = None
    upcoming_invoice: Optional[InvoiceResponse] = None
    recent_invoices: List[InvoiceResponse] = []
    usage: Optional[SubscriptionUsageResponse] = None
    payment_method: Optional[Dict[str, Any]] = None

