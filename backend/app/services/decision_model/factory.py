"""
Decision Model Factory

Selects and caches the active decision model implementation.
Provider is controlled by the DECISION_MODEL_PROVIDER environment variable.

Available providers:
  mock  — rule-based deterministic model (DEFAULT, always works)
  laya  — Laya integration (UNAVAILABLE: no verified public API yet)
  jev   — JEV integration  (UNAVAILABLE: no verified public API yet)
  llm   — LLM-based classification (requires LLM API key)

Laya and JEV interfaces are defined and ready for integration
once a verified API/library becomes available.
"""

import logging
from typing import Optional

from app.core.config import settings
from app.services.decision_model.base import DecisionModel
from app.services.decision_model.laya_model import LayaDecisionModel
from app.services.decision_model.jev_model import JevDecisionModel
from app.services.decision_model.llm_model import LLMDecisionModel
from app.services.decision_model.mock_model import MockDecisionModel

logger = logging.getLogger(__name__)

_decision_model: Optional[DecisionModel] = None
_active_provider_name: str = "mock"


async def get_decision_model() -> DecisionModel:
    """
    Return the configured decision model instance (singleton).
    Falls back to MockDecisionModel if requested provider is unavailable.
    """
    global _decision_model, _active_provider_name

    if _decision_model is not None:
        return _decision_model

    provider = getattr(settings, "DECISION_MODEL_PROVIDER", "mock").lower()

    if provider == "laya":
        model_path = getattr(settings, "LAYA_MODEL_PATH", None)
        api_key = getattr(settings, "LAYA_API_KEY", None)
        _decision_model = LayaDecisionModel(api_key=api_key, model_path=model_path)
        _active_provider_name = "laya"
    elif provider == "jev":
        api_key = getattr(settings, "JEV_API_KEY", None)
        _decision_model = JevDecisionModel(api_key=api_key)
        _active_provider_name = "jev"
    elif provider == "llm":
        _decision_model = LLMDecisionModel()
        _active_provider_name = "llm"
    else:
        _decision_model = MockDecisionModel()
        _active_provider_name = "mock"
        logger.info("Decision model: Mock (default)")

    return _decision_model


async def get_active_provider_name() -> str:
    """Return the name of the currently active decision provider."""
    await get_decision_model()  # ensure initialised
    return _active_provider_name


async def reset_decision_model() -> None:
    """Reset singleton (for testing)."""
    global _decision_model, _active_provider_name
    _decision_model = None
    _active_provider_name = "mock"
