"""Support ticket model for customer service tracking"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DECIMAL,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TicketStatus(str, enum.Enum):
    """Support ticket status enumeration"""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class TicketPriority(str, enum.Enum):
    """Support ticket priority enumeration"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCategory(str, enum.Enum):
    """Support ticket category enumeration"""

    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    PRODUCT = "product"
    SHIPPING = "shipping"
    REFUND = "refund"
    COMPLAINT = "complaint"
    FEATURE_REQUEST = "feature_request"
    OTHER = "other"


class SupportTicket(Base):
    """Support ticket model for customer service management"""

    __tablename__ = "support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Ticket identification
    external_id = Column(String(255), nullable=True, index=True)  # External system ID
    ticket_number = Column(String(50), nullable=True, unique=True, index=True)

    # Ticket content
    subject = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # Classification
    status = Column(
        Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False, index=True
    )
    priority = Column(
        Enum(TicketPriority), default=TicketPriority.MEDIUM, nullable=False, index=True
    )
    category = Column(Enum(TicketCategory), nullable=True, index=True)

    # AI Analysis
    sentiment_score = Column(DECIMAL(3, 2), nullable=True, index=True)  # 0.00 to 1.00
    urgency_score = Column(DECIMAL(3, 2), nullable=True)  # AI-calculated urgency
    escalation_risk = Column(DECIMAL(3, 2), nullable=True)  # Risk of escalation

    # Assignment and handling
    assigned_to = Column(String(255), nullable=True)  # User ID or name
    assigned_at = Column(DateTime(timezone=True), nullable=True)

    # Resolution tracking
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(255), nullable=True)

    # Customer satisfaction
    satisfaction_rating = Column(Integer, nullable=True)  # 1-5 stars
    satisfaction_feedback = Column(Text, nullable=True)

    # Response time tracking
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    last_response_at = Column(DateTime(timezone=True), nullable=True)
    response_count = Column(Integer, default=0, nullable=False)

    # Metadata
    source = Column(String(50), nullable=True)  # email, chat, phone, web
    tags = Column(Text, nullable=True)  # Comma-separated tags
    internal_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    organization = relationship("Organization", back_populates="support_tickets")
    customer = relationship("Customer", back_populates="support_tickets")
    recovery_actions = relationship("RecoveryAction", back_populates="ticket")
    # Note: agent_decisions relationship removed - use input_id query instead (polymorphic relationship)

    def __repr__(self):
        return f"<SupportTicket(id={self.id}, subject='{self.subject[:50]}...', status='{self.status}')>"

    @property
    def is_open(self) -> bool:
        """Check if ticket is open"""
        return self.status in [
            TicketStatus.OPEN,
            TicketStatus.IN_PROGRESS,
            TicketStatus.REOPENED,
        ]

    @property
    def is_resolved(self) -> bool:
        """Check if ticket is resolved"""
        return self.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]

    @property
    def is_overdue(self) -> bool:
        """Check if ticket is overdue based on priority"""
        if not self.is_open:
            return False

        now = datetime.now(timezone.utc)
        hours_open = (now - self.created_at).total_seconds() / 3600

        # SLA thresholds by priority
        sla_hours = {
            TicketPriority.CRITICAL: 2,
            TicketPriority.HIGH: 8,
            TicketPriority.MEDIUM: 24,
            TicketPriority.LOW: 72,
        }

        return hours_open > sla_hours.get(self.priority, 24)

    @property
    def hours_open(self) -> float:
        """Get hours since ticket was created"""
        if self.resolved_at:
            delta = self.resolved_at - self.created_at
        else:
            delta = datetime.now(timezone.utc) - self.created_at

        return delta.total_seconds() / 3600

    @property
    def time_to_first_response(self) -> Optional[float]:
        """Get hours to first response"""
        if not self.first_response_at:
            return None

        delta = self.first_response_at - self.created_at
        return delta.total_seconds() / 3600

    @property
    def time_to_resolution(self) -> Optional[float]:
        """Get hours to resolution"""
        if not self.resolved_at:
            return None

        delta = self.resolved_at - self.created_at
        return delta.total_seconds() / 3600

    @property
    def sentiment_label(self) -> str:
        """Get human-readable sentiment label"""
        if self.sentiment_score is None:
            return "Unknown"

        score = float(self.sentiment_score)
        if score >= 0.7:
            return "Positive"
        elif score >= 0.5:
            return "Neutral"
        elif score >= 0.3:
            return "Frustrated"
        elif score >= 0.1:
            return "Angry"
        else:
            return "Very Angry"

    def generate_ticket_number(self):
        """Generate unique ticket number"""
        if not self.ticket_number:
            # Format: ORG-YYYYMMDD-XXXX
            date_str = self.created_at.strftime("%Y%m%d")
            org_prefix = str(self.organization_id)[:8].upper()
            counter = str(self.id).replace("-", "")[:4].upper()
            self.ticket_number = f"{org_prefix}-{date_str}-{counter}"

    def assign_to(self, user_id: str):
        """Assign ticket to user"""
        self.assigned_to = user_id
        self.assigned_at = datetime.now(timezone.utc)

        if self.status == TicketStatus.OPEN:
            self.status = TicketStatus.IN_PROGRESS

    def add_response(self):
        """Record a response to the ticket"""
        now = datetime.now(timezone.utc)

        if self.response_count == 0:
            self.first_response_at = now

        self.last_response_at = now
        self.response_count += 1

    def resolve(self, resolution: str, resolved_by: str):
        """Resolve the ticket"""
        self.resolution = resolution
        self.resolved_by = resolved_by
        self.resolved_at = datetime.now(timezone.utc)
        self.status = TicketStatus.RESOLVED

    def close(self):
        """Close the ticket"""
        if self.status == TicketStatus.RESOLVED:
            self.status = TicketStatus.CLOSED

    def reopen(self, reason: str = None):
        """Reopen the ticket"""
        self.status = TicketStatus.REOPENED
        self.resolved_at = None

        if reason:
            if self.internal_notes:
                self.internal_notes += f"\n\nReopened: {reason}"
            else:
                self.internal_notes = f"Reopened: {reason}"

    def set_satisfaction(self, rating: int, feedback: str = None):
        """Set customer satisfaction rating"""
        self.satisfaction_rating = max(1, min(5, rating))  # Clamp to 1-5
        if feedback:
            self.satisfaction_feedback = feedback

    def add_tag(self, tag: str):
        """Add tag to ticket"""
        if not self.tags:
            self.tags = tag
        else:
            tags = self.tags.split(",")
            if tag not in tags:
                tags.append(tag)
                self.tags = ",".join(tags)

    def get_tags(self) -> list:
        """Get list of tags"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",")]

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "external_id": self.external_id,
            "ticket_number": self.ticket_number,
            "subject": self.subject,
            "content": self.content,
            "status": self.status.value,
            "priority": self.priority.value,
            "category": self.category.value if self.category else None,
            "sentiment_score": (
                float(self.sentiment_score) if self.sentiment_score else None
            ),
            "sentiment_label": self.sentiment_label,
            "urgency_score": float(self.urgency_score) if self.urgency_score else None,
            "escalation_risk": (
                float(self.escalation_risk) if self.escalation_risk else None
            ),
            "assigned_to": self.assigned_to,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "resolution": self.resolution,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "satisfaction_rating": self.satisfaction_rating,
            "satisfaction_feedback": self.satisfaction_feedback,
            "first_response_at": (
                self.first_response_at.isoformat() if self.first_response_at else None
            ),
            "last_response_at": (
                self.last_response_at.isoformat() if self.last_response_at else None
            ),
            "response_count": self.response_count,
            "source": self.source,
            "tags": self.get_tags(),
            "internal_notes": self.internal_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_open": self.is_open,
            "is_resolved": self.is_resolved,
            "is_overdue": self.is_overdue,
            "hours_open": round(self.hours_open, 2),
            "time_to_first_response": (
                round(self.time_to_first_response, 2)
                if self.time_to_first_response
                else None
            ),
            "time_to_resolution": (
                round(self.time_to_resolution, 2) if self.time_to_resolution else None
            ),
        }
