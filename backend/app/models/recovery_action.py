"""Recovery action model for customer recovery automation"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, DECIMAL, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from app.core.database import Base


class ActionType(str, enum.Enum):
    """Recovery action type enumeration"""
    EMAIL = "email"
    SMS = "sms"
    PHONE_CALL = "phone_call"
    DISCOUNT_OFFER = "discount_offer"
    REFUND = "refund"
    ESCALATE_TO_MANAGER = "escalate_to_manager"
    FOLLOW_UP = "follow_up"
    SURVEY = "survey"
    CALLBACK_REQUEST = "callback_request"
    PERSONALIZED_MESSAGE = "personalized_message"


class ActionStatus(str, enum.Enum):
    """Recovery action status enumeration"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    RESPONDED = "responded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ActionPriority(str, enum.Enum):
    """Recovery action priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RecoveryAction(Base):
    """Recovery action model for automated customer recovery"""
    
    __tablename__ = "recovery_actions"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )
    organization_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("organizations.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    customer_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("customers.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Related entities (optional - action can be triggered by review or ticket)
    review_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("reviews.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    ticket_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("support_tickets.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    
    # Action details
    action_type = Column(Enum(ActionType), nullable=False, index=True)
    status = Column(Enum(ActionStatus), default=ActionStatus.PENDING, nullable=False, index=True)
    priority = Column(Enum(ActionPriority), default=ActionPriority.MEDIUM, nullable=False, index=True)
    
    # Content and configuration
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    action_metadata = Column(JSON, nullable=True)  # Action-specific data (discount %, callback time, etc.)
    
    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Execution tracking
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    
    # Results tracking
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    response_data = Column(JSON, nullable=True)  # External service response
    
    # Effectiveness tracking
    customer_responded = Column(Boolean, default=False, nullable=False)
    customer_response_date = Column(DateTime(timezone=True), nullable=True)
    outcome_rating = Column(DECIMAL(3, 2), nullable=True)  # 0.00 to 1.00 success rating
    
    # AI context
    trigger_reason = Column(Text, nullable=True)  # Why this action was triggered
    confidence_score = Column(DECIMAL(3, 2), nullable=True)  # AI confidence in action
    
    # Approval workflow
    requires_approval = Column(Boolean, default=False, nullable=False)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="recovery_actions")
    customer = relationship("Customer", back_populates="recovery_actions")
    review = relationship("Review", back_populates="recovery_actions")
    ticket = relationship("SupportTicket", back_populates="recovery_actions")
    
    def __repr__(self):
        return f"<RecoveryAction(id={self.id}, type='{self.action_type}', status='{self.status}')>"
    
    @property
    def is_pending(self) -> bool:
        """Check if action is pending execution"""
        return self.status in [ActionStatus.PENDING, ActionStatus.SCHEDULED]
    
    @property
    def is_completed(self) -> bool:
        """Check if action is completed"""
        return self.status in [
            ActionStatus.COMPLETED, 
            ActionStatus.RESPONDED, 
            ActionStatus.DELIVERED,
            ActionStatus.CLICKED
        ]
    
    @property
    def is_failed(self) -> bool:
        """Check if action failed"""
        return self.status in [ActionStatus.FAILED, ActionStatus.CANCELLED]
    
    @property
    def is_expired(self) -> bool:
        """Check if action is expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_overdue(self) -> bool:
        """Check if scheduled action is overdue"""
        if not self.scheduled_at or not self.is_pending:
            return False
        return datetime.now(timezone.utc) > self.scheduled_at
    
    @property
    def can_retry(self) -> bool:
        """Check if action can be retried"""
        return (
            self.status == ActionStatus.FAILED and 
            self.attempts < self.max_attempts and
            not self.is_expired
        )
    
    @property
    def time_until_scheduled(self) -> Optional[float]:
        """Get hours until scheduled execution"""
        if not self.scheduled_at:
            return None
        
        delta = self.scheduled_at - datetime.now(timezone.utc)
        return delta.total_seconds() / 3600
    
    @property
    def execution_delay(self) -> Optional[float]:
        """Get hours between scheduled and actual execution"""
        if not self.scheduled_at or not self.executed_at:
            return None
        
        delta = self.executed_at - self.scheduled_at
        return delta.total_seconds() / 3600
    
    def schedule(self, scheduled_time: datetime):
        """Schedule the action for execution"""
        self.scheduled_at = scheduled_time
        self.status = ActionStatus.SCHEDULED
    
    def execute(self):
        """Mark action as being executed"""
        self.executed_at = datetime.now(timezone.utc)
        self.attempts += 1
        self.last_attempt_at = self.executed_at
        self.status = ActionStatus.SENT
    
    def mark_success(self, response_data: Dict[str, Any] = None):
        """Mark action as successful"""
        self.success = True
        self.status = ActionStatus.DELIVERED
        if response_data:
            self.response_data = response_data
    
    def mark_failure(self, error_message: str):
        """Mark action as failed"""
        self.success = False
        self.error_message = error_message
        
        if self.can_retry:
            self.status = ActionStatus.FAILED
        else:
            self.status = ActionStatus.CANCELLED
    
    def mark_customer_response(self, outcome_rating: float = None):
        """Mark that customer responded to the action"""
        self.customer_responded = True
        self.customer_response_date = datetime.now(timezone.utc)
        self.status = ActionStatus.RESPONDED
        
        if outcome_rating is not None:
            self.outcome_rating = max(0.0, min(1.0, outcome_rating))
    
    def approve(self, approved_by: str):
        """Approve the action for execution"""
        self.approved_by = approved_by
        self.approved_at = datetime.now(timezone.utc)
        self.requires_approval = False
        
        if self.status == ActionStatus.PENDING:
            # If scheduled, keep scheduled status, otherwise make it ready
            if not self.scheduled_at:
                self.status = ActionStatus.PENDING
    
    def cancel(self, reason: str = None):
        """Cancel the action"""
        self.status = ActionStatus.CANCELLED
        if reason:
            self.error_message = f"Cancelled: {reason}"
    
    def get_metadata_value(self, key: str, default=None):
        """Get value from metadata"""
        if not self.action_metadata:
            return default
        return self.action_metadata.get(key, default)
    
    def set_metadata_value(self, key: str, value: Any):
        """Set value in metadata"""
        if not self.action_metadata:
            self.action_metadata = {}
        self.action_metadata[key] = value
    
    def get_discount_percentage(self) -> Optional[float]:
        """Get discount percentage for discount offers"""
        if self.action_type == ActionType.DISCOUNT_OFFER:
            return self.get_metadata_value("discount_percentage")
        return None
    
    def get_callback_time(self) -> Optional[str]:
        """Get preferred callback time"""
        if self.action_type == ActionType.CALLBACK_REQUEST:
            return self.get_metadata_value("preferred_time")
        return None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "customer_id": str(self.customer_id),
            "review_id": str(self.review_id) if self.review_id else None,
            "ticket_id": str(self.ticket_id) if self.ticket_id else None,
            "action_type": self.action_type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "title": self.title,
            "content": self.content,
            "metadata": self.action_metadata,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "success": self.success,
            "error_message": self.error_message,
            "response_data": self.response_data,
            "customer_responded": self.customer_responded,
            "customer_response_date": self.customer_response_date.isoformat() if self.customer_response_date else None,
            "outcome_rating": float(self.outcome_rating) if self.outcome_rating else None,
            "trigger_reason": self.trigger_reason,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "requires_approval": self.requires_approval,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_pending": self.is_pending,
            "is_completed": self.is_completed,
            "is_failed": self.is_failed,
            "is_expired": self.is_expired,
            "is_overdue": self.is_overdue,
            "can_retry": self.can_retry,
            "time_until_scheduled": round(self.time_until_scheduled, 2) if self.time_until_scheduled else None,
            "execution_delay": round(self.execution_delay, 2) if self.execution_delay else None
        }
