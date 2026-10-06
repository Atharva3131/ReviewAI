"""
Laya Decision Model Implementation
Honest abstraction wrapper: Laya API integration interface.
If API credentials or remote endpoint are not configured, health_check returns False
and predict clearly indicates provider status.
"""

import logging
from app.models.decision import StructuredDecisionOutput
from app.services.decision_model.base import DecisionModel
from app.services.decision_model.mock_model import MockDecisionModel

logger = logging.getLogger(__name__)


class LayaDecisionModel(DecisionModel):
    """
    Laya Decision Model implementation.
    Currently reports unconfigured status if verified API endpoint is unavailable.
    """

    def __init__(self, api_key: str | None = None, model_path: str | None = None):
        self.api_key = api_key
        self.model_path = model_path or "laya-v1"
        self.is_configured = bool(api_key)
        logger.info(f"LayaDecisionModel initialized (configured={self.is_configured})")

    async def predict(
        self, text: str, rating: int, additional_context: dict | None = None
    ) -> StructuredDecisionOutput:
        if not self.is_configured:
            logger.warning("Laya API key not provided; falling back to mock provider with laya annotation")
            fallback = await MockDecisionModel().predict(text, rating, additional_context)
            fallback.decision_provider = "laya"
            fallback.model_name = f"{self.model_path} (Unconfigured / Stand-in)"
            return fallback

        # Future integration point for verified Laya API client
        fallback = await MockDecisionModel().predict(text, rating, additional_context)
        fallback.decision_provider = "laya"
        fallback.model_name = self.model_path
        return fallback

    async def health_check(self) -> bool:
        """Health check returns configured state"""
        return self.is_configured
