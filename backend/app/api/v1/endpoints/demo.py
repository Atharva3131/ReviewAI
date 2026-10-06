"""
Demo Endpoints
Simple ingestion for demonstration purposes
"""

import logging
from datetime import datetime, timezone

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
    confidence: float
    policy_decision: str
    reasoning: str


@router.post("/ingest-demo-review", response_model=DemoReviewResponse)
async def ingest_demo_review(
    request: DemoReviewRequest,
    db: AsyncSession = Depends(get_async_db),
):
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
                "urgency_level": int(
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

        # Convert urgency_level to enum
        urgency_level_enum = UrgencyLevel(
            urgency_result.get("urgency_level", "medium")
        )

        # Update review with analysis
        review.sentiment_score = sentiment_result.get("sentiment_score", 0.5)
        review.urgency_level = urgency_level_enum
        review.confidence_score = structured_decision.confidence

        await db.commit()

        return DemoReviewResponse(
            review_id=str(review.id),
            customer_name=request.customer_name,
            rating=request.rating,
            sentiment_score=sentiment_result.get("sentiment_score", 0.5),
            urgency_level=urgency_result.get("urgency_level", "medium"),
            decision_category=structured_decision.category.value,
            decision_urgency=structured_decision.urgency,
            churn_risk=structured_decision.churn_risk_factor,
            confidence=structured_decision.confidence,
            policy_decision=policy_result["strategy"].value,
            reasoning=policy_result.get("reason", ""),
        )

    except Exception as e:
        logger.error(f"Demo review ingestion failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/demo-status")
async def demo_status():
    """Get demo system status and available models"""
    return {
        "status": "running",
        "version": "1.0.0",
        "components": {
            "decision_model": "mock (laya placeholder)",
            "ml_churn_model": "xgboost (trained on synthetic data)",
            "policy_engine": "deterministic rules",
            "knowledge_service": "simple knowledge base",
        },
        "endpoints": {
            "ingest_review": "/demo/ingest-demo-review (POST)",
            "status": "/demo/demo-status (GET)",
        },
    }
