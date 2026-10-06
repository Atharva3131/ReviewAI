"""
Policy Validation Engine
Deterministic policy validation for autonomous action execution
"""

import logging
from enum import Enum
from typing import Optional

from app.models.decision import StructuredDecisionOutput

logger = logging.getLogger(__name__)


class ExecutionStrategy(str, Enum):
    """How to handle a decision"""

    AUTO_EXECUTE = "AUTO_EXECUTE"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    ESCALATE = "ESCALATE"


class PolicyDecision(dict):
    """Policy decision result"""

    pass


class PolicyEngine:
    """Deterministic policy validation for autonomous execution"""

    # Confidence thresholds
    MIN_CONFIDENCE_AUTO_EXECUTE = 0.80
    MIN_CONFIDENCE_APPROVAL = 0.60

    # Risk thresholds
    MAX_CHURN_RISK_AUTO_EXECUTE = 0.20
    MAX_CHURN_RISK_APPROVAL = 0.70

    def __init__(self):
        self.engine_version = "1.0.0"
        logger.info("PolicyEngine initialized")

    async def validate_decision(
        self,
        decision: StructuredDecisionOutput,
        customer_churn_risk: Optional[float] = None,
    ) -> PolicyDecision:
        """
        Validate decision and determine execution strategy

        Args:
            decision: Structured decision output
            customer_churn_risk: Optional ML churn prediction

        Returns:
            PolicyDecision with execution strategy and reasoning
        """

        # Check for immediate escalation flags
        if decision.safety_concern or decision.policy_violation:
            return PolicyDecision(
                {
                    "strategy": ExecutionStrategy.ESCALATE,
                    "reason": "Safety concern or policy violation detected",
                    "confidence_acceptable": decision.confidence
                    >= self.MIN_CONFIDENCE_APPROVAL,
                    "approved_by_policy": False,
                }
            )

        # Check escalation requirement flag
        if decision.escalation_required:
            return PolicyDecision(
                {
                    "strategy": ExecutionStrategy.ESCALATE,
                    "reason": "Structured decision marked as escalation required",
                    "confidence_acceptable": decision.confidence
                    >= self.MIN_CONFIDENCE_APPROVAL,
                    "approved_by_policy": False,
                }
            )

        # Check compensation requests
        if decision.compensation_requested:
            if (
                decision.confidence >= 0.90
                and decision.churn_risk_factor < 0.50
            ):
                return PolicyDecision(
                    {
                        "strategy": ExecutionStrategy.APPROVAL_REQUIRED,
                        "reason": "Compensation request - requires human approval",
                        "confidence_acceptable": True,
                        "approved_by_policy": False,
                    }
                )
            else:
                return PolicyDecision(
                    {
                        "strategy": ExecutionStrategy.ESCALATE,
                        "reason": "Compensation with high uncertainty/risk",
                        "confidence_acceptable": False,
                        "approved_by_policy": False,
                    }
                )

        # Evaluate auto-execute for positive reviews
        if decision.category.value == "positive_feedback":
            if (
                decision.confidence >= self.MIN_CONFIDENCE_AUTO_EXECUTE
                and decision.urgency <= 2
            ):
                return PolicyDecision(
                    {
                        "strategy": ExecutionStrategy.AUTO_EXECUTE,
                        "reason": "Positive review with high confidence - auto-execute thank you",
                        "confidence_acceptable": True,
                        "approved_by_policy": True,
                    }
                )

        # Evaluate auto-execute for recovery emails (negative reviews)
        if (
            decision.churn_risk_factor > 0.0
            and decision.recovery_possible
            and decision.confidence >= self.MIN_CONFIDENCE_AUTO_EXECUTE
            and decision.churn_risk_factor <= self.MAX_CHURN_RISK_AUTO_EXECUTE
        ):
            return PolicyDecision(
                {
                    "strategy": ExecutionStrategy.AUTO_EXECUTE,
                    "reason": "Low-risk recovery opportunity - send recovery email",
                    "confidence_acceptable": True,
                    "approved_by_policy": True,
                }
            )

        # Medium-confidence decisions require approval
        if decision.confidence >= self.MIN_CONFIDENCE_APPROVAL:
            return PolicyDecision(
                {
                    "strategy": ExecutionStrategy.APPROVAL_REQUIRED,
                    "reason": f"Moderate confidence ({decision.confidence:.1%}) - requires human review",
                    "confidence_acceptable": True,
                    "approved_by_policy": False,
                }
            )

        # Low confidence -> escalate
        return PolicyDecision(
            {
                "strategy": ExecutionStrategy.ESCALATE,
                "reason": f"Low confidence ({decision.confidence:.1%}) - escalate to human",
                "confidence_acceptable": False,
                "approved_by_policy": False,
            }
        )

    async def get_policy_summary(self) -> dict:
        """Get policy rules summary for debugging"""
        return {
            "version": self.engine_version,
            "auto_execute_thresholds": {
                "min_confidence": self.MIN_CONFIDENCE_AUTO_EXECUTE,
                "max_churn_risk": self.MAX_CHURN_RISK_AUTO_EXECUTE,
            },
            "approval_thresholds": {
                "min_confidence": self.MIN_CONFIDENCE_APPROVAL,
                "max_churn_risk": self.MAX_CHURN_RISK_APPROVAL,
            },
            "escalation_triggers": [
                "safety_concern",
                "policy_violation",
                "escalation_required_flag",
                "low_confidence",
                "high_churn_risk",
            ],
        }
