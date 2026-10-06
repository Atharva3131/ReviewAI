"""
Mock Decision Model - For testing and development
"""

import logging
from random import random

from app.models.decision import DecisionCategory, StructuredDecisionOutput
from app.services.decision_model.base import DecisionModel

logger = logging.getLogger(__name__)


class MockDecisionModel(DecisionModel):
    """Mock decision model for testing"""

    def __init__(self):
        self.model_name = "mock_decision_model"
        self.model_version = "1.0.0"
        logger.info("MockDecisionModel initialized")

    async def predict(
        self, text: str, rating: int, additional_context: dict | None = None
    ) -> StructuredDecisionOutput:
        """
        Mock prediction - deterministic based on rating
        """
        # Determine category based on keywords
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["deliver", "shipping", "late", "slow"]):
            category = DecisionCategory.DELIVERY
        elif any(kw in text_lower for kw in ["price", "expensive", "cost", "charge"]):
            category = DecisionCategory.PRICING
        elif any(
            kw in text_lower for kw in ["quality", "broken", "defect", "poor", "bad"]
        ):
            category = DecisionCategory.QUALITY
        elif any(kw in text_lower for kw in ["sick", "health", "safety", "injury"]):
            category = DecisionCategory.SAFETY
        elif rating >= 4:
            category = DecisionCategory.POSITIVE_FEEDBACK
        else:
            category = DecisionCategory.SUPPORT

        # Determine urgency and risk based on rating
        if rating <= 1:
            urgency = 5
            churn_risk = 0.95
            escalation_required = True
            safety_concern = "sick" in text_lower or "injury" in text_lower
        elif rating == 2:
            urgency = 4
            churn_risk = 0.75
            escalation_required = False
            safety_concern = False
        elif rating == 3:
            urgency = 2
            churn_risk = 0.3
            escalation_required = False
            safety_concern = False
        elif rating >= 4:
            urgency = 1
            churn_risk = 0.05
            escalation_required = False
            safety_concern = False
        else:
            urgency = 3
            churn_risk = 0.5
            escalation_required = False
            safety_concern = False

        # Determine if compensation is likely requested
        compensation_keywords = ["refund", "compensation", "money back", "replace"]
        compensation_requested = any(kw in text_lower for kw in compensation_keywords)

        # Policy violation flags
        policy_violation = safety_concern

        # Confidence is slightly random for variability
        base_confidence = 0.85
        confidence = min(1.0, max(0.6, base_confidence + (random() * 0.1 - 0.05)))

        return StructuredDecisionOutput(
            category=category,
            urgency=urgency,
            churn_risk_factor=churn_risk,
            recovery_possible=churn_risk < 0.9,
            escalation_required=escalation_required,
            policy_violation=policy_violation,
            compensation_requested=compensation_requested,
            safety_concern=safety_concern,
            confidence=confidence,
            category_confidence=confidence - 0.1,
            decision_provider="mock",
            model_version=self.model_version,
            model_name=self.model_name,
        )

    async def health_check(self) -> bool:
        """Mock health check always succeeds"""
        return True
