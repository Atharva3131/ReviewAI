"""
Demo Endpoints
Simple ingestion for demonstration purposes
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.models.customer import Customer
from app.models.review import Review, ReviewPlatform, ReviewStatus, UrgencyLevel
from app.services.agent_engine import AgentEngine
from app.services.ml_churn_model import get_ml_churn_model
from app.services.policy_engine import PolicyEngine
from app.services.decision_model.factory import get_decision_model

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
agent_engine = AgentEngine()
policy_engine = PolicyEngine()


class DemoReviewRequest(BaseModel):
    """Demo review submission"""

    customer_name: str = Field(..., min_length=1, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    review_text: str = Field(..., min_length=10, max_length=5000)


class DemoReviewResponse(BaseModel):
    """Demo review processing response"""

    review_id: str
    customer_name: str
    rating: int
    sentiment_score: float
    urgency_level: str
    decision_category: str
    decision_urgency: int
    churn_risk: float
    ml_churn_probability: float
    confidence: float
    decision_provider: str   # which model actually ran: mock | laya | jev | llm
    policy_decision: str
    reasoning: str


@router.post("/ingest-demo-review", response_model=DemoReviewResponse)
async def ingest_demo_review(
    request: DemoReviewRequest,
    db: AsyncSession = Depends(get_async_db),
) -> DemoReviewResponse:
    """
    Ingest and process a demo review

    This endpoint simulates Google Review ingestion with structured decision making,
    ML churn prediction, and policy-based action determination.

    **Demo Flow:**
    1. Create/get customer
    2. Create review record
    3. Run sentiment/urgency/categorization analysis
    4. Get structured decision (Laya/Mock)
    5. Get ML churn risk prediction
    6. Validate policy
    7. Return complete lifecycle
    """

    try:
        # 1. Get or create customer
        try:
            customer_email = f"{request.customer_name.lower().replace(' ', '_')}@demo.com"
            stmt = select(Customer).where(Customer.email == customer_email)
            result = await db.execute(stmt)
            customer = result.scalars().first()

            if not customer:
                customer = Customer(
                    email=customer_email,
                    name=request.customer_name,
                    phone=None,
                    notes="Demo customer",
                )
                db.add(customer)
                await db.flush()

            # 2. Create review
            review = Review(
                customer_id=customer.id,
                platform=ReviewPlatform.GOOGLE,
                external_review_id=f"demo-{datetime.now().timestamp()}",
                rating=request.rating,
                content=request.review_text,
                reviewer_name=request.customer_name,
                review_date=datetime.now(timezone.utc),
                status=ReviewStatus.PENDING,
            )
            db.add(review)
            await db.flush()
            review_id = str(review.id)
        except Exception as db_err:
            logger.error("Demo review persistence failed", exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=503,
                detail="Demo review could not be persisted. Please try again later.",
            ) from db_err

        # 3. Run sentiment analysis
        sentiment_result = await agent_engine.sentiment_service.analyze_sentiment(
            request.review_text, request.rating
        )

        # 4. Run urgency classification
        urgency_result = await agent_engine.urgency_service.classify_urgency(
            request.review_text,
            request.rating,
            sentiment_result.get("sentiment_score", 0.5),
            title=f"Review: {request.customer_name}",
        )

        # 5. Get structured decision
        decision_model = await get_decision_model()
        structured_decision = await decision_model.predict(
            text=request.review_text, rating=request.rating
        )

        # 6. Get ML churn prediction
        ml_model = await get_ml_churn_model()
        ml_result = await ml_model.predict(
            {
                "rating": request.rating,
                "urgency_level": (
                    ["low", "medium", "high"].index(
                        urgency_result.get("urgency_level", "medium")
                    )
                    + 1
                ),  # Convert to 1-3 scale
                "negative_review_count": 1,
                "support_ticket_count": 0,
                "days_since_last_interaction": 0,
                "account_tenure_days": 30,
                "avg_previous_rating": request.rating,
            }
        )

        # 7. Validate policy
        policy_result = await policy_engine.validate_decision(structured_decision)

        try:
            await db.commit()
        except Exception as db_err:
            logger.error("Demo review commit failed", exc_info=True)
            await db.rollback()
            raise HTTPException(
                status_code=503,
                detail="Demo review could not be persisted. Please try again later.",
            ) from db_err

        return DemoReviewResponse(
            review_id=review_id,
            customer_name=request.customer_name,
            rating=request.rating,
            sentiment_score=sentiment_result.get("sentiment_score", 0.5),
            urgency_level=urgency_result.get("urgency_level", "medium"),
            decision_category=structured_decision.category.value,
            decision_urgency=structured_decision.urgency,
            churn_risk=structured_decision.churn_risk_factor,
            ml_churn_probability=ml_result.get("churn_probability", 0.5),
            confidence=structured_decision.confidence,
            decision_provider=structured_decision.decision_provider,
            policy_decision=policy_result["strategy"].value,
            reasoning=policy_result.get("reason", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Demo review ingestion failed: {e}", exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/demo-status")
async def demo_status() -> Dict[str, Any]:
    """Get demo system status — reports which providers are actually active"""
    from app.services.decision_model.factory import get_active_provider_name
    return {
        "status": "running",
        "version": "1.0.0",
        "authentication": "disabled (single-user demo mode)",
        "components": {
            "decision_model": {
                "active_provider": await get_active_provider_name(),
                "available_providers": ["mock", "laya (unavailable)", "jev (unavailable)", "llm (requires API key)"],
                "note": "Laya and JEV interfaces are ready but not connected to external APIs.",
            },
            "ml_churn_model": "xgboost — trained on synthetic demo data (not real customer data)",
            "policy_engine": "deterministic rules — NOT AI-decided",
            "knowledge_base": "category lookup — not vector/semantic search",
        },
        "endpoints": {
            "ingest_review": "POST /api/v1/demo/ingest-demo-review",
            "status": "GET /api/v1/demo/demo-status",
        },
    }
