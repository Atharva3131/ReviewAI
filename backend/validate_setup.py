#!/usr/bin/env python3
"""
Validation script to check if all components are ready
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def validate_imports():
    """Check if all imports work"""
    logger.info("Validating imports...")
    try:
        from app.models.decision import StructuredDecisionOutput, DecisionCategory
        from app.models.knowledge import BusinessKnowledge
        from app.services.decision_model import get_decision_model, MockDecisionModel
        from app.services.policy_engine import PolicyEngine, ExecutionStrategy
        from app.services.ml_churn_model import get_ml_churn_model
        from app.services.knowledge_service import KnowledgeService
        from app.api.v1.endpoints.demo import router as demo_router

        logger.info("✓ All imports successful")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False


async def validate_decision_model():
    """Test decision model"""
    logger.info("Testing decision model...")
    try:
        from app.services.decision_model import get_decision_model

        model = await get_decision_model()
        result = await model.predict(
            text="Product broke after 1 week, no response from support",
            rating=1,
        )

        assert result.category
        assert 0 <= result.urgency <= 5
        assert 0 <= result.confidence <= 1
        assert 0 <= result.churn_risk_factor <= 1

        logger.info(f"✓ Decision model works: {result.category} (confidence: {result.confidence:.2f})")
        return True
    except Exception as e:
        logger.error(f"✗ Decision model failed: {e}")
        return False


async def validate_policy_engine():
    """Test policy engine"""
    logger.info("Testing policy engine...")
    try:
        from app.services.policy_engine import PolicyEngine
        from app.models.decision import DecisionCategory, StructuredDecisionOutput

        engine = PolicyEngine()
        decision = StructuredDecisionOutput(
            category=DecisionCategory.POSITIVE_FEEDBACK,
            urgency=1,
            churn_risk_factor=0.05,
            recovery_possible=True,
            escalation_required=False,
            policy_violation=False,
            compensation_requested=False,
            safety_concern=False,
            confidence=0.95,
        )

        result = await engine.validate_decision(decision)
        assert result["strategy"]
        assert result["reason"]

        logger.info(f"✓ Policy engine works: {result['strategy'].value}")
        return True
    except Exception as e:
        logger.error(f"✗ Policy engine failed: {e}")
        return False


async def validate_ml_model():
    """Test ML churn model"""
    logger.info("Testing ML churn model...")
    try:
        from app.services.ml_churn_model import get_ml_churn_model

        model = await get_ml_churn_model()
        result = await model.predict({
            "rating": 2,
            "urgency_level": 4,
            "negative_review_count": 1,
            "support_ticket_count": 2,
            "days_since_last_interaction": 30,
            "account_tenure_days": 365,
            "avg_previous_rating": 3.5,
        })

        assert 0 <= result["churn_probability"] <= 1
        assert result["prediction"]

        logger.info(f"✓ ML model works: churn_prob={result['churn_probability']:.2f}")
        return True
    except Exception as e:
        logger.error(f"✗ ML model failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def validate_knowledge_service():
    """Test knowledge service"""
    logger.info("Testing knowledge service...")
    try:
        from app.services.knowledge_service import KnowledgeService

        service = KnowledgeService()
        knowledge = await service.get_default_knowledge()

        assert isinstance(knowledge, dict)
        assert len(knowledge) > 0
        assert "brand_voice" in knowledge

        logger.info(f"✓ Knowledge service works: {len(knowledge)} categories")
        return True
    except Exception as e:
        logger.error(f"✗ Knowledge service failed: {e}")
        return False


async def main():
    """Run all validations"""
    logger.info("=" * 60)
    logger.info("ReviewAI Demo - Setup Validation")
    logger.info("=" * 60)

    results = []

    results.append(("Imports", await validate_imports()))
    results.append(("Decision Model", await validate_decision_model()))
    results.append(("Policy Engine", await validate_policy_engine()))
    results.append(("ML Model", await validate_ml_model()))
    results.append(("Knowledge Service", await validate_knowledge_service()))

    logger.info("\n" + "=" * 60)
    logger.info("Validation Results")
    logger.info("=" * 60)

    for name, status in results:
        status_str = "✓" if status else "✗"
        logger.info(f"{status_str} {name}")

    all_passed = all(status for _, status in results)

    if all_passed:
        logger.info("\n✓ All validations passed!")
        logger.info("Ready to run: uvicorn app.main:app --reload")
        return 0
    else:
        logger.error("\n✗ Some validations failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
