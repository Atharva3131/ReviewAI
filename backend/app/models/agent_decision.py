"""Agent decision model for tracking AI decision-making process"""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast

from sqlalchemy import (
    DECIMAL,
    JSON,
    Boolean,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Input information
    input_type: Mapped[InputType] = mapped_column(Enum(InputType), nullable=False, index=True)
    input_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )  # ID of review, ticket, etc.

    # Decision details
    decision_type: Mapped[DecisionType] = mapped_column(Enum(DecisionType), nullable=False, index=True)
    status: Mapped[DecisionStatus] = mapped_column(
        Enum(DecisionStatus), default=DecisionStatus.PENDING, nullable=False, index=True
    )

    # AI reasoning
    confidence_score: Mapped[float] = mapped_column(DECIMAL(3, 2), nullable=False, index=True)  # 0.00 to 1.00
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    # Decision context
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Snapshot of input data at decision time
    context_factors: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Factors that influenced decision

    # Generated content (if applicable)
    generated_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # email, response, message

    # Execution tracking
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # system or user ID
    execution_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Human oversight
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # User ID who reviewed
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Effectiveness tracking
    outcome_success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    outcome_rating: Mapped[Optional[float]] = mapped_column(DECIMAL(3, 2), nullable=True)  # 0.00 to 1.00
    customer_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Model information
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # openai, gemini, etc.
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AgentDecision(id={self.id}, type='{self.decision_type}', confidence={self.confidence_score})>"

    @property
    def float_confidence(self) -> float:
        """Safely convert confidence_score to float"""
        if self.confidence_score is None:
            return 0.0
        return float(cast(Any, self.confidence_score))

    @property
    def is_high_confidence(self) -> bool:
        """Check if decision has high confidence"""
        return self.float_confidence >= 0.8

    @property
    def is_low_confidence(self) -> bool:
        """Check if decision has low confidence"""
        return self.float_confidence < 0.5

    @property
    def requires_human_review(self) -> bool:
        """Check if decision requires human review"""
        decision_val = (
            self.decision_type.value
            if hasattr(self.decision_type, "value")
            else self.decision_type
        )
        status_val = (
            self.status.value
            if hasattr(self.status, "value")
            else self.status
        )
        return bool(
            self.is_low_confidence
            or decision_val == DecisionType.ESCALATE.value
            or status_val == DecisionStatus.PENDING.value
        )

    @property
    def is_executed(self) -> bool:
        """Check if decision has been executed"""
        status_val = (
            self.status.value
            if hasattr(self.status, "value")
            else self.status
        )
        return bool(status_val == DecisionStatus.EXECUTED.value)

    @property
    def execution_time(self) -> Optional[float]:
        """Get time between decision and execution in hours"""
        if not self.executed_at or not self.created_at:
            return None

        delta = self.executed_at - self.created_at
        return float(delta.total_seconds() / 3600)

    @property
    def confidence_level(self) -> str:
        """Get human-readable confidence level"""
        score = self.float_confidence
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

    def approve(self, approved_by: str, notes: Optional[str] = None) -> None:
        """Approve the decision"""
        self.status = DecisionStatus.APPROVED
        self.reviewed_by = approved_by
        self.reviewed_at = datetime.now(timezone.utc)
        if notes:
            self.review_notes = notes

    def reject(self, rejected_by: str, reason: str) -> None:
        """Reject the decision"""
        self.status = DecisionStatus.REJECTED
        self.reviewed_by = rejected_by
        self.reviewed_at = datetime.now(timezone.utc)
        self.review_notes = reason

    def execute(
        self, executed_by: str = "system", result: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark decision as executed"""
        self.status = DecisionStatus.EXECUTED
        self.executed_by = executed_by
        self.executed_at = datetime.now(timezone.utc)
        if result:
            self.execution_result = result

    def mark_failed(self, error_message: str) -> None:
        """Mark decision execution as failed"""
        self.status = DecisionStatus.FAILED
        self.execution_result = {"error": error_message}

    def set_outcome(
        self,
        success: bool,
        rating: Optional[float] = None,
        feedback: Optional[str] = None,
    ) -> None:
        """Set the outcome of the decision"""
        self.outcome_success = success
        if rating is not None:
            self.outcome_rating = max(0.0, min(1.0, rating))
        if feedback:
            self.customer_feedback = feedback

    def add_context_factor(self, key: str, value: Any) -> None:
        """Add context factor that influenced the decision"""
        current = dict(self.context_factors or {})
        current[key] = value
        self.context_factors = current
        self.context_factors = current

    def get_context_factor(self, key: str, default: Any = None) -> Any:
        """Get context factor value"""
        if not self.context_factors or not isinstance(self.context_factors, dict):
            return default
        return self.context_factors.get(key, default)

    def get_input_summary(self) -> str:
        """Get summary of input data"""
        input_type_val = (
            self.input_type.value
            if hasattr(self.input_type, "value")
            else str(self.input_type or "")
        )
        if not self.input_data or not isinstance(self.input_data, dict):
            return f"{input_type_val} {self.input_id}"

        if input_type_val == InputType.REVIEW.value:
            rating = self.input_data.get("rating", "?")
            content = (self.input_data.get("content") or "")[:50]
            return f"Review ({rating}★): {content}..."
        elif input_type_val == InputType.SUPPORT_TICKET.value:
            subject = (self.input_data.get("subject") or "")[:50]
            return f"Ticket: {subject}..."
        else:
            return f"{input_type_val} {self.input_id}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary safely"""
        input_type_val = (
            self.input_type.value
            if hasattr(self.input_type, "value")
            else str(self.input_type)
        )
        decision_type_val = (
            self.decision_type.value
            if hasattr(self.decision_type, "value")
            else str(self.decision_type)
        )
        status_val = (
            self.status.value
            if hasattr(self.status, "value")
            else str(self.status)
        )

        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "input_type": input_type_val,
            "input_id": str(self.input_id),
            "input_summary": self.get_input_summary(),
            "decision_type": decision_type_val,
            "status": status_val,
            "confidence_score": self.float_confidence,
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
            "outcome_rating": (
                float(cast(Any, self.outcome_rating)) if self.outcome_rating is not None else None
            ),
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
            "execution_time": (
                round(self.execution_time, 2) if self.execution_time is not None else None
            ),
        }
