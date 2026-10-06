"""
Base class for structured decision models
"""

from abc import ABC, abstractmethod

from app.models.decision import StructuredDecisionOutput


class DecisionModel(ABC):
    """
    Abstract base class for structured decision models.
    Implementations: Laya, Jev, LLM-based, Mock
    """

    @abstractmethod
    async def predict(
        self, text: str, rating: int, additional_context: dict | None = None
    ) -> StructuredDecisionOutput:
        """
        Make a structured decision about a review

        Args:
            text: Review text content
            rating: Numeric rating (typically 1-5)
            additional_context: Optional additional context (customer history, etc.)

        Returns:
            StructuredDecisionOutput with structured decision
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if model is healthy and accessible"""
        pass
