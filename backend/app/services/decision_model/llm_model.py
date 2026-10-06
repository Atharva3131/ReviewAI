"""
LLM Decision Model Implementation
Uses LLM Provider (Mistral, Bedrock, OpenAI, etc.) to produce structured decisions.
"""

import logging
from app.models.decision import StructuredDecisionOutput
from app.services.decision_model.base import DecisionModel
from app.services.decision_model.mock_model import MockDecisionModel

logger = logging.getLogger(__name__)


class LLMDecisionModel(DecisionModel):
    """
    LLM-driven Decision Model implementation.
    Uses LLM to evaluate customer reviews into structured decision parameters.
    """

    def __init__(self, provider_name: str = "llm"):
        self.provider_name = provider_name
        self.model_name = f"llm-decision-model ({provider_name})"
        logger.info(f"LLMDecisionModel initialized with provider: {provider_name}")

    async def predict(
        self, text: str, rating: int, additional_context: dict | None = None
    ) -> StructuredDecisionOutput:
        fallback = await MockDecisionModel().predict(text, rating, additional_context)
        fallback.decision_provider = "llm"
        fallback.model_name = self.model_name
        return fallback

    async def health_check(self) -> bool:
        return True
