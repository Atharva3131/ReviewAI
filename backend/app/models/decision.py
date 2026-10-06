"""
Structured Decision Model Output
Defines the structured decision types that decision models should produce.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DecisionCategory(str, Enum):
    """Issue category"""

    SUPPORT = "support"
    PRICING = "pricing"
    DELIVERY = "delivery"
    QUALITY = "quality"
    BILLING = "billing"
    TECHNICAL = "technical"
    SAFETY = "safety"
    POSITIVE_FEEDBACK = "positive_feedback"
    OTHER = "other"


class StructuredDecisionOutput(BaseModel):
    """
    Structured decision model output
    Designed to work with Laya, Jev, or similar structured decision models
    """

    # Primary categorization
    category: DecisionCategory = Field(
        ..., description="Issue category classification"
    )

    # Urgency level (1-5 scale)
    urgency: int = Field(
        ..., ge=1, le=5, description="Urgency level from 1 (low) to 5 (critical)"
    )

    # Risk factors
    churn_risk_factor: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Likelihood this customer will churn (0.0-1.0)",
    )
    recovery_possible: bool = Field(
        ..., description="Whether recovery/retention is likely possible"
    )

    # Policy and safety flags
    escalation_required: bool = Field(
        ..., description="Whether this requires human escalation"
    )
    policy_violation: bool = Field(
        ..., description="Whether the review indicates a policy violation"
    )
    compensation_requested: bool = Field(
        ..., description="Whether customer appears to be requesting compensation"
    )
    safety_concern: bool = Field(
        ..., description="Whether this contains a safety/health concern"
    )

    # Confidence scores
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence in this decision (0.0-1.0)",
    )
    category_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence specific to categorization"
    )

    # Model metadata
    decision_provider: str = Field(
        default="mock",
        description="Decision provider (mock, laya, jev, llm)",
    )
    model_version: Optional[str] = Field(
        None, description="Version of the model that produced this decision"
    )
    model_name: Optional[str] = Field(
        None, description="Name/identifier of the decision model used"
    )

    class Config:
        """Pydantic config"""

        json_schema_extra = {
            "example": {
                "category": "quality",
                "urgency": 3,
                "churn_risk_factor": 0.65,
                "recovery_possible": True,
                "escalation_required": False,
                "policy_violation": False,
                "compensation_requested": False,
                "safety_concern": False,
                "confidence": 0.87,
                "model_name": "laya-v1",
            }
        }
