"""Agent decision model for tracking AI decision-making"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, DECIMAL, JSON, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from app.core.database import Base


class InputType(str, enum.Enum):
    """Input type for agent decisions"""
    REVIEW = "review"
    SUPPORT_TICKET = "support_ticket"
    CUSTOMER_PROFILE = "customer_profile"
    RECOVERY_ACTION = "recovery_action"


class DecisionType(str, enum.Enum):
    """Agent decision type enumeration"""
    RESPOND_PUBLIC = "respond_public"
    RECOVER_PRIVATE = "recover_private"
    ESCALATE = "escalate"
    NO_ACTION = "no_action"
    SCHEDULE_FOLLOWUP = "schedule_followup"
    REQUEST_APPROVAL = "request_approval"


class DecisionStatus(str, enum.Enum):
    """Decision execution status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class AgentDecision(Base):
    """Agent decision model for tracking AI decision-making process"""
    
    __tablename__ = "agent_decisions"
    
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
    
    # Input information
    input_type = Column(Enum(InputType), nullable=False, index=True)
    input_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # ID of review, ticket, etc.
    
    # Decision details
    decision_type = Column(Enum(DecisionType), nullable=False, index=True)
    status = Column(Enum(DecisionStatus), default=DecisionStatus.PENDING, nullable=False, index=True)
    
    # AI reasoning
    confidence_score = Column(DECIMAL(3, 2), nullable=False, index=True)  # 0.00 to 1.00
    reasoning = Column(Text, nullable=False)
    
    # Decision context
    input_data = Column(JSON, nullable=True)  # Snapshot of input data at decision time
    context_factors = Column(JSON, nullable=True)  # Factors that influenced decision
    
    # Generated content (if applicable)
    generated_content = Column(Text, nullable=True)
    content_type = Column(String(50), nullable=True)  # email, response, message
    
    # Execution tracking
    executed_at = Column(DateTime(timezone=True), nullable=True)
    executed_by = Column(String(255), nullable=True)  # system or user ID
    execution_result = Column(JSON, nullable=True)
    
    # Human oversight
    reviewed_by = Column(String(255), nullable=True)  # User ID who reviewed
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Effectiveness tracking
    outcome_success = Column(Boolean, nullable=True)
    outcome_rating = Column(DECIMAL(3, 2), nullable=True)  # 0.00 to 1.00
    customer_feedback = Column(Text, nullable=True)
    
    # Model information
    model_version = Column(String(50), nullable=True)
    model_provider = Column(String(50), nullable=True)  # openai, gemini, etc.
    processing_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="agent_decisions")
    
    def __repr__(self):
        return f"<AgentDecision(id={self.id}, type='{self.decision_type}', confidence={self.confidence_score})>"
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if decision has high confidence"""
        return float(self.confidence_score) >= 0.8
    
    @property
    def is_low_confidence(self) -> bool:
        """Check if decision has low confidence"""
        return float(self.confidence_score) < 0.5
    
    @property
    def requires_human_review(self) -> bool:
        """Check if decision requires human review"""
        return (
            self.is_low_confidence or 
            self.decision_type == DecisionType.ESCALATE or
            self.status == DecisionStatus.PENDING
        )
    
    @property
    def is_executed(self) -> bool:
        """Check if decision has been executed"""
        return self.status == DecisionStatus.EXECUTED
    
    @property
    def execution_time(self) -> Optional[float]:
        """Get time between decision and execution in hours"""
        if not self.executed_at:
            return None
        
        delta = self.executed_at - self.created_at
        return delta.total_seconds() / 3600
    
    @property
    def confidence_level(self) -> str:
        """Get human-readable confidence level"""
        score = float(self.confidence_score)
        if score >= 0.9:
            return "Very High"
        elif score >= 0.8:
            return "High"
        elif score >= 0.6:
            return "Medium"
        elif score >= 0.4:
            return "Low"
        else:
            return "Very Low"
    
    def approve(self, approved_by: str, notes: str = None):
        """Approve the decision"""
        self.status = DecisionStatus.APPROVED
        self.reviewed_by = approved_by
        self.reviewed_at = datetime.now(timezone.utc)
        if notes:
            self.review_notes = notes
    
    def reject(self, rejected_by: str, reason: str):
        """Reject the decision"""
        self.status = DecisionStatus.REJECTED
        self.reviewed_by = rejected_by
        self.reviewed_at = datetime.now(timezone.utc)
        self.review_notes = reason
    
    def execute(self, executed_by: str = "system", result: Dict[str, Any] = None):
        """Mark decision as executed"""
        self.status = DecisionStatus.EXECUTED
        self.executed_by = executed_by
        self.executed_at = datetime.now(timezone.utc)
        if result:
            self.execution_result = result
    
    def mark_failed(self, error_message: str):
        """Mark decision execution as failed"""
        self.status = DecisionStatus.FAILED
        self.execution_result = {"error": error_message}
    
    def set_outcome(self, success: bool, rating: float = None, feedback: str = None):
        """Set the outcome of the decision"""
        self.outcome_success = success
        if rating is not None:
            self.outcome_rating = max(0.0, min(1.0, rating))
        if feedback:
            self.customer_feedback = feedback
    
    def add_context_factor(self, key: str, value: Any):
        """Add context factor that influenced the decision"""
        if not self.context_factors:
            self.context_factors = {}
        self.context_factors[key] = value
    
    def get_context_factor(self, key: str, default=None):
        """Get context factor value"""
        if not self.context_factors:
            return default
        return self.context_factors.get(key, default)
    
    def get_input_summary(self) -> str:
        """Get summary of input data"""
        if not self.input_data:
            return f"{self.input_type.value} {self.input_id}"
        
        if self.input_type == InputType.REVIEW:
            rating = self.input_data.get("rating", "?")
            content = self.input_data.get("content", "")[:50]
            return f"Review ({rating}★): {content}..."
        elif self.input_type == InputType.SUPPORT_TICKET:
            subject = self.input_data.get("subject", "")[:50]
            return f"Ticket: {subject}..."
        else:
            return f"{self.input_type.value} {self.input_id}"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "input_type": self.input_type.value,
            "input_id": str(self.input_id),
            "input_summary": self.get_input_summary(),
            "decision_type": self.decision_type.value,
            "status": self.status.value,
            "confidence_score": float(self.confidence_score),
            "confidence_level": self.confidence_level,
            "reasoning": self.reasoning,
            "input_data": self.input_data,
            "context_factors": self.context_factors,
            "generated_content": self.generated_content,
            "content_type": self.content_type,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "executed_by": self.executed_by,
            "execution_result": self.execution_result,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
            "outcome_success": self.outcome_success,
            "outcome_rating": float(self.outcome_rating) if self.outcome_rating else None,
            "customer_feedback": self.customer_feedback,
            "model_version": self.model_version,
            "model_provider": self.model_provider,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_high_confidence": self.is_high_confidence,
            "is_low_confidence": self.is_low_confidence,
            "requires_human_review": self.requires_human_review,
            "is_executed": self.is_executed,
            "execution_time": round(self.execution_time, 2) if self.execution_time else None
        }
