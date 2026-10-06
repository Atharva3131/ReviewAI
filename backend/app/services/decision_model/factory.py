"""
Decision Model Factory
"""

import logging
from typing import Optional

from app.core.config import settings
from app.services.decision_model.base import DecisionModel
from app.services.decision_model.laya_model import LayaDecisionModel
from app.services.decision_model.mock_model import MockDecisionModel

logger = logging.getLogger(__name__)

# Global instance cache
_decision_model: Optional[DecisionModel] = None


async def get_decision_model() -> DecisionModel:
    """
    Get the configured decision model instance.
    Uses singleton pattern for efficiency.
    """
    global _decision_model

    if _decision_model is not None:
        return _decision_model

    provider = getattr(settings, "DECISION_MODEL_PROVIDER", "mock")

    if provider == "laya":
        try:
            model_path = getattr(settings, "LAYA_MODEL_PATH", None)
            _decision_model = LayaDecisionModel(model_path=model_path)
            logger.info("Using Laya decision model")
        except Exception as e:
            logger.warning(
                f"Failed to initialize Laya model: {e}, falling back to mock"
            )
            _decision_model = MockDecisionModel()
    else:
        _decision_model = MockDecisionModel()
        logger.info("Using Mock decision model")

    return _decision_model


async def reset_decision_model() -> None:
    """Reset the model instance (for testing)"""
    global _decision_model
    _decision_model = None
