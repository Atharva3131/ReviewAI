"""Support ticket schemas for API requests and responses"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.support_ticket import TicketCategory, TicketPriority, TicketStatus


class SupportTicketBase(BaseModel):
    """Base support ticket schema"""

    subject: str = Field(
        ..., min_length=1, max_length=500, description="Ticket subject"
    )
    content: str = Field(..., min_length=1, description="Ticket content/description")
    priority: TicketPriority = Field(
        default=TicketPriority.MEDIUM, description="Ticket priority"
    )
    category: Optional[TicketCategory] = Field(None, description="Ticket category")
    source: Optional[str] = Field(
        None, max_length=50, description="Ticket source (email, chat, phone, web)"
    )
    tags: Optional[List[str]] = Field(None, description="Ticket tags")


class SupportTicketCreate(SupportTicketBase):
    """Schema for creating a support ticket"""

    customer_id: Optional[UUID] = Field(None, description="Customer ID")
    external_id: Optional[str] = Field(
        None, max_length=255, description="External system ID"
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        if v and len(v) > 20:
            raise ValueError("Maximum 20 tags allowed")
        return v


class SupportTicketUpdate(BaseModel):
    """Schema for updating a support ticket"""

    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None
    assigned_to: Optional[str] = Field(None, max_length=255)
    resolution: Optional[str] = None
    internal_notes: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        if v and len(v) > 20:
            raise ValueError("Maximum 20 tags allowed")
        return v


class SupportTicketResponse(SupportTicketBase):
    """Schema for support ticket response"""

    id: UUID
    organization_id: UUID
    customer_id: Optional[UUID]
    external_id: Optional[str]
    ticket_number: Optional[str]
    status: TicketStatus
    sentiment_score: Optional[Decimal]
    sentiment_label: str
    urgency_score: Optional[Decimal]
    escalation_risk: Optional[Decimal]
    assigned_to: Optional[str]
    assigned_at: Optional[datetime]
    resolution: Optional[str]
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    satisfaction_rating: Optional[int]
    satisfaction_feedback: Optional[str]
    first_response_at: Optional[datetime]
    last_response_at: Optional[datetime]
    response_count: int
    internal_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_open: bool
    is_resolved: bool
    is_overdue: bool
    hours_open: float
    time_to_first_response: Optional[float]
    time_to_resolution: Optional[float]

    class Config:
        from_attributes = True


class SupportTicketListResponse(BaseModel):
    """Schema for paginated support ticket list"""

    tickets: List[SupportTicketResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TicketAssignRequest(BaseModel):
    """Schema for assigning a ticket"""

    assigned_to: str = Field(
        ..., min_length=1, max_length=255, description="User ID or name to assign to"
    )


class TicketResolveRequest(BaseModel):
    """Schema for resolving a ticket"""

    resolution: str = Field(..., min_length=1, description="Resolution description")
    resolved_by: str = Field(
        ..., min_length=1, max_length=255, description="User ID or name who resolved"
    )


class TicketReopenRequest(BaseModel):
    """Schema for reopening a ticket"""

    reason: Optional[str] = Field(None, description="Reason for reopening")


class TicketSatisfactionRequest(BaseModel):
    """Schema for setting customer satisfaction"""

    rating: int = Field(..., ge=1, le=5, description="Satisfaction rating (1-5)")
    feedback: Optional[str] = Field(None, description="Customer feedback")


class TicketResponseRequest(BaseModel):
    """Schema for adding a response to a ticket"""

    content: str = Field(..., min_length=1, description="Response content")
    is_internal: bool = Field(
        default=False, description="Whether this is an internal note"
    )


class TicketAnalyzeRequest(BaseModel):
    """Schema for analyzing a ticket"""

    ticket_id: UUID = Field(..., description="Ticket ID to analyze")


class TicketAnalyzeResponse(BaseModel):
    """Schema for ticket analysis response"""

    ticket_id: UUID
    sentiment_score: Decimal
    sentiment_label: str
    urgency_score: Decimal
    escalation_risk: Decimal
    recommended_priority: TicketPriority
    recommended_category: Optional[TicketCategory]
    suggested_actions: List[str]


class TicketStatsResponse(BaseModel):
    """Schema for ticket statistics"""

    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    closed_tickets: int
    overdue_tickets: int
    avg_time_to_first_response: Optional[float]
    avg_time_to_resolution: Optional[float]
    avg_satisfaction_rating: Optional[float]
    tickets_by_priority: dict
    tickets_by_category: dict
    tickets_by_source: dict
