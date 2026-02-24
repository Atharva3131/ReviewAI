"""
Customer-related schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from .base import (
    UUIDMixin, 
    TimestampMixin, 
    OrganizationMixin,
    PaginationParams,
    FilterParams,
    EmailStr,
    PhoneStr,
    CommonValidators,
    StatusEnum,
    PriorityEnum,
    ActionTypeEnum
)


# Customer schemas
class CustomerBase(BaseModel):
    """Base customer schema"""
    email: Optional[EmailStr] = Field(None, description="Customer email")
    phone: Optional[PhoneStr] = Field(None, description="Customer phone")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Customer name")
    context_summary: Optional[str] = Field(None, max_length=2000, description="Customer context summary")


class CustomerCreate(CustomerBase, OrganizationMixin):
    """Schema for creating a customer"""
    pass


class CustomerUpdate(BaseModel):
    """Schema for updating a customer"""
    email: Optional[EmailStr] = Field(None, description="Customer email")
    phone: Optional[PhoneStr] = Field(None, description="Customer phone")
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Customer name")
    context_summary: Optional[str] = Field(None, max_length=2000, description="Customer context summary")


class CustomerResponse(CustomerBase, UUIDMixin, TimestampMixin, OrganizationMixin):
    """Schema for customer response"""
    churn_risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Churn risk score")
    bad_review_likelihood: Optional[float] = Field(None, ge=0.0, le=1.0, description="Bad review likelihood")
    last_interaction: Optional[datetime] = Field(None, description="Last interaction timestamp")
    
    class Config:
        from_attributes = True


class CustomerListFilter(FilterParams):
    """Customer list filtering parameters"""
    risk_level: Optional[str] = Field(None, pattern="^(low|medium|high)$", description="Risk level filter")
    has_email: Optional[bool] = Field(None, description="Filter customers with email")
    has_phone: Optional[bool] = Field(None, description="Filter customers with phone")
    min_churn_risk: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum churn risk")
    max_churn_risk: Optional[float] = Field(None, ge=0.0, le=1.0, description="Maximum churn risk")


# Support ticket schemas
class SupportTicketBase(BaseModel):
    """Base support ticket schema"""
    external_id: Optional[str] = Field(None, max_length=255, description="External ticket ID")
    subject: str = Field(..., min_length=1, max_length=500, description="Ticket subject")
    content: str = Field(..., min_length=1, description="Ticket content")
    status: StatusEnum = Field(StatusEnum.PENDING, description="Ticket status")
    priority: PriorityEnum = Field(PriorityEnum.MEDIUM, description="Ticket priority")


class SupportTicketCreate(SupportTicketBase, OrganizationMixin):
    """Schema for creating a support ticket"""
    customer_id: uuid.UUID = Field(..., description="Customer ID")


class SupportTicketUpdate(BaseModel):
    """Schema for updating a support ticket"""
    subject: Optional[str] = Field(None, min_length=1, max_length=500, description="Ticket subject")
    content: Optional[str] = Field(None, min_length=1, description="Ticket content")
    status: Optional[StatusEnum] = Field(None, description="Ticket status")
    priority: Optional[PriorityEnum] = Field(None, description="Ticket priority")


class SupportTicketResponse(SupportTicketBase, UUIDMixin, TimestampMixin, OrganizationMixin):
    """Schema for support ticket response"""
    customer_id: uuid.UUID = Field(..., description="Customer ID")
    sentiment_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Sentiment score")
    
    class Config:
        from_attributes = True


# Recovery action schemas
class RecoveryActionBase(BaseModel):
    """Base recovery action schema"""
    action_type: ActionTypeEnum = Field(..., description="Recovery action type")
    content: Optional[str] = Field(None, description="Action content")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled execution time")


class RecoveryActionCreate(RecoveryActionBase, OrganizationMixin):
    """Schema for creating a recovery action"""
    customer_id: uuid.UUID = Field(..., description="Customer ID")
    review_id: Optional[uuid.UUID] = Field(None, description="Related review ID")
    ticket_id: Optional[uuid.UUID] = Field(None, description="Related ticket ID")


class RecoveryActionUpdate(BaseModel):
    """Schema for updating a recovery action"""
    content: Optional[str] = Field(None, description="Action content")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled execution time")
    status: Optional[StatusEnum] = Field(None, description="Action status")


class RecoveryActionResponse(RecoveryActionBase, UUIDMixin, TimestampMixin, OrganizationMixin):
    """Schema for recovery action response"""
    customer_id: uuid.UUID = Field(..., description="Customer ID")
    review_id: Optional[uuid.UUID] = Field(None, description="Related review ID")
    ticket_id: Optional[uuid.UUID] = Field(None, description="Related ticket ID")
    status: StatusEnum = Field(StatusEnum.PENDING, description="Action status")
    executed_at: Optional[datetime] = Field(None, description="Execution timestamp")
    
    class Config:
        from_attributes = True


# Customer recovery schemas
class CustomerRecoveryRequest(BaseModel):
    """Schema for customer recovery request"""
    customer_id: uuid.UUID = Field(..., description="Customer ID")
    trigger_type: str = Field(..., description="Recovery trigger type")
    context: Optional[Dict[str, Any]] = Field(None, description="Recovery context")
    
    @field_validator('trigger_type')
    def validate_trigger_type(cls, v):
        allowed_triggers = ['support_ticket', 'negative_review', 'churn_prediction', 'manual']
        if v not in allowed_triggers:
            raise ValueError(f'trigger_type must be one of: {", ".join(allowed_triggers)}')
        return v


class RecoveryPlan(BaseModel):
    """Schema for recovery plan"""
    churn_risk: float = Field(..., ge=0.0, le=1.0, description="Churn risk score")
    bad_review_likelihood: float = Field(..., ge=0.0, le=1.0, description="Bad review likelihood")
    actions: List[RecoveryActionResponse] = Field([], description="Recommended recovery actions")
    reasoning: Optional[str] = Field(None, description="Recovery plan reasoning")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Plan confidence")


class CustomerRecoveryResponse(BaseModel):
    """Schema for customer recovery response"""
    customer_id: uuid.UUID = Field(..., description="Customer ID")
    recovery_plan: RecoveryPlan = Field(..., description="Recovery plan")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")


# Risk assessment schemas
class RiskFactors(BaseModel):
    """Schema for risk factors"""
    ticket_frequency: int = Field(0, ge=0, description="Number of recent tickets")
    avg_sentiment: float = Field(0.5, ge=0.0, le=1.0, description="Average sentiment score")
    escalation_count: int = Field(0, ge=0, description="Number of escalations")
    days_since_last_interaction: int = Field(0, ge=0, description="Days since last interaction")
    negative_review_count: int = Field(0, ge=0, description="Number of negative reviews")
    response_time_avg: Optional[float] = Field(None, ge=0.0, description="Average response time in hours")


class RiskAssessment(BaseModel):
    """Schema for customer risk assessment"""
    customer_id: uuid.UUID = Field(..., description="Customer ID")
    churn_risk: float = Field(..., ge=0.0, le=1.0, description="Churn risk score")
    bad_review_likelihood: float = Field(..., ge=0.0, le=1.0, description="Bad review likelihood")
    risk_factors: RiskFactors = Field(..., description="Risk factors")
    risk_level: str = Field(..., description="Risk level (low/medium/high)")
    recommended_actions: List[str] = Field([], description="Recommended action types")
    assessment_date: datetime = Field(default_factory=datetime.utcnow, description="Assessment timestamp")
    
    @field_validator('risk_level')
    def validate_risk_level(cls, v):
        if v not in ['low', 'medium', 'high']:
            raise ValueError('risk_level must be low, medium, or high')
        return v


# Bulk operations schemas
class BulkCustomerUpdate(BaseModel):
    """Schema for bulk customer updates"""
    customer_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=100, description="Customer IDs")
    updates: CustomerUpdate = Field(..., description="Updates to apply")


class BulkRecoveryRequest(BaseModel):
    """Schema for bulk recovery requests"""
    customer_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=50, description="Customer IDs")
    trigger_type: str = Field(..., description="Recovery trigger type")
    context: Optional[Dict[str, Any]] = Field(None, description="Recovery context")


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response"""
    total_requested: int = Field(..., description="Total items requested")
    successful: int = Field(..., description="Successfully processed items")
    failed: int = Field(..., description="Failed items")
    errors: List[Dict[str, Any]] = Field([], description="Error details")
    processing_time: float = Field(..., description="Processing time in seconds")

