"""
Review management endpoints
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.dependencies import get_access_control_context, get_current_user
from app.core.permissions import AccessControlContext
from app.models.user import User
from app.schemas.review import (
    ReviewAnalysisRequest,
    ReviewAnalysisResponse,
    ReviewFilter,
    ReviewIngest,
    ReviewResponse,
    ReviewResponseGenerated,
    ReviewResponseRequest,
    ReviewStats,
    SaveResponseRequest,
)
from app.services.categorization_service import CategorizationService
from app.services.review_service import ReviewService
from app.services.sentiment_service import SentimentService
from app.services.urgency_service import UrgencyService
from app.tasks.review_tasks import generate_review_response, process_review_analysis

router = APIRouter()


@router.post("/ingest", response_model=ReviewResponse)
async def ingest_review(
    review_data: ReviewIngest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """
    Ingest a new review into the system
    """
    # Ingest the review
    review = await ReviewService.ingest_review(
        db=db, organization_id=org_context.organization_id, review_data=review_data
    )

    # Analyze the review immediately (since Celery isn't running)
    if review.content:
        try:
            # Sentiment Analysis
            sentiment_result = await SentimentService.analyze_sentiment(
                review.content, review.rating
            )

            # Urgency Classification
            urgency_result = await UrgencyService.classify_urgency(
                review.content, review.rating, sentiment_result["sentiment_score"]
            )

            # Issue Categorization
            categorization_result = await CategorizationService.categorize_issues(
                review.content, review.title, review.rating
            )

            # Update review with analysis results
            analysis_results = {
                "sentiment_score": sentiment_result["sentiment_score"],
                "urgency_level": urgency_result["urgency_level"],
                "issue_categories": categorization_result["categories"],
                "requires_private_recovery": review.rating <= 2
                and urgency_result["urgency_level"] in ["high", "medium"],
            }

            await ReviewService.mark_review_processed(
                db=db,
                review_id=str(review.id),
                organization_id=org_context.organization_id,
                analysis_results=analysis_results,
            )

            # Refresh to get updated data
            await db.refresh(review)

        except Exception as e:
            # Log error but don't fail the ingestion
            print(f"Error analyzing review: {e}")

    return ReviewResponse.from_orm(review)


@router.post("/analyze", response_model=ReviewAnalysisResponse)
async def analyze_review(
    request: ReviewAnalysisRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """
    Analyze a review for sentiment, urgency, and categorization
    """
    start_time = datetime.now()

    # Get the review
    review = await ReviewService.get_review_by_id(
        db=db, review_id=request.review_id, organization_id=org_context.organization_id
    )

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    if not review.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review has no content to analyze",
        )

    # Perform analysis
    analysis_results = {}
    recommendations = []

    # Sentiment Analysis
    sentiment_result = await SentimentService.analyze_sentiment(
        review.content, review.rating
    )
    analysis_results.update(
        {
            "sentiment_score": sentiment_result["sentiment_score"],
            "sentiment_confidence": sentiment_result["confidence"],
        }
    )

    # Urgency Classification
    urgency_result = await UrgencyService.classify_urgency(
        review.content, review.rating, sentiment_result["sentiment_score"]
    )
    analysis_results.update(
        {
            "urgency_level": urgency_result["urgency_level"],
            "urgency_confidence": urgency_result["confidence"],
        }
    )

    # Issue Categorization
    categorization_result = await CategorizationService.categorize_issues(
        review.content, review.title, review.rating
    )
    analysis_results.update(
        {
            "issue_categories": categorization_result["categories"],
            "category_confidences": categorization_result["confidences"],
        }
    )

    # Generate recommendations
    if sentiment_result["sentiment_score"] < 0.3:
        recommendations.append("Consider private recovery outreach")

    if urgency_result["urgency_level"] == "high":
        recommendations.append("Requires immediate attention")

    if review.rating <= 2:
        recommendations.append("High priority for response")

    if len(categorization_result["categories"]) > 2:
        recommendations.append("Complex issue - may need escalation")

    # Update review with analysis results
    await ReviewService.mark_review_processed(
        db=db,
        review_id=request.review_id,
        organization_id=org_context.organization_id,
        analysis_results=analysis_results,
    )

    # Calculate processing time
    processing_time = (datetime.now() - start_time).total_seconds() * 1000

    return ReviewAnalysisResponse(
        review_id=request.review_id,
        sentiment_score=sentiment_result["sentiment_score"],
        sentiment_label=sentiment_result["label"],
        urgency_level=urgency_result["urgency_level"],
        issue_categories=categorization_result["categories"],
        confidence_scores={
            "sentiment": sentiment_result["confidence"],
            "urgency": urgency_result["confidence"],
            "categories": categorization_result["confidences"],
        },
        processing_time_ms=int(processing_time),
        recommendations=recommendations,
    )


@router.post("/respond", response_model=ReviewResponseGenerated)
async def generate_review_response(
    request: ReviewResponseRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """
    Generate AI response for a review
    """
    # Get the review
    review = await ReviewService.get_review_by_id(
        db=db, review_id=request.review_id, organization_id=org_context.organization_id
    )

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    # For now, return a placeholder response since LLM service isn't implemented yet
    # This will be replaced with actual LLM integration in Task 7

    placeholder_response = _generate_placeholder_response(
        review, request.response_type, request.tone
    )

    return ReviewResponseGenerated(
        review_id=request.review_id,
        response_content=placeholder_response,
        response_type=request.response_type,
        tone=request.tone,
        confidence_score=0.8,
        requires_approval=review.rating <= 2,
        generated_at=datetime.now(),
    )


@router.get("/", response_model=List[ReviewResponse])
async def get_reviews(
    skip: int = 0,
    limit: int = 100,
    platform: Optional[str] = None,
    rating_min: Optional[int] = None,
    rating_max: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """
    Get reviews with filtering
    """
    # Build filter
    filters = ReviewFilter()
    if platform:
        filters.platform = platform
    if rating_min is not None:
        filters.rating_min = rating_min
    if rating_max is not None:
        filters.rating_max = rating_max

    reviews = await ReviewService.get_reviews(
        db=db,
        organization_id=org_context.organization_id,
        skip=skip,
        limit=limit,
        filters=filters,
    )

    return [ReviewResponse.from_orm(review) for review in reviews]


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """
    Get a specific review by ID
    """
    review = await ReviewService.get_review_by_id(
        db=db, review_id=review_id, organization_id=org_context.organization_id
    )

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    return ReviewResponse.from_orm(review)


@router.get("/stats/overview", response_model=ReviewStats)
async def get_review_stats(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """
    Get review statistics for the organization
    """
    stats = await ReviewService.get_review_stats(
        db=db,
        organization_id=org_context.organization_id,
        date_from=date_from,
        date_to=date_to,
    )

    return stats


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """
    Delete a review by ID
    """
    review = await ReviewService.get_review_by_id(
        db=db, review_id=review_id, organization_id=org_context.organization_id
    )

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    # Delete the review
    await db.delete(review)
    await db.commit()

    return None


@router.post("/{review_id}/response", response_model=ReviewResponse)
async def save_or_publish_response(
    review_id: str,
    request_data: SaveResponseRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    org_context: AccessControlContext = Depends(get_access_control_context),
):
    """
    Save or publish a response to a review

    NOTE: This saves the response to the internal database only.
    To post to external platforms (Google, Yelp, etc.), you need to:
    1. Enable platform integrations in settings
    2. Authenticate with each platform's API
    3. The system will then sync responses to platforms
    """
    from app.models.review import ReviewStatus

    review = await ReviewService.get_review_by_id(
        db=db, review_id=review_id, organization_id=org_context.organization_id
    )

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    # Update review with response
    review.public_response = request_data.content
    review.public_response_date = datetime.now()

    if request_data.action == "publish":
        review.status = ReviewStatus.RESPONDED

        # TODO: Platform integration - uncomment when ready
        # await sync_response_to_platform(review, request_data.content)

    await db.commit()
    await db.refresh(review)

    return ReviewResponse.from_orm(review)


def _generate_placeholder_response(review, response_type: str, tone: str) -> str:
    """
    Generate placeholder response until LLM service is implemented
    """
    if response_type == "public":
        if review.rating <= 2:
            return f"Thank you for your feedback. We sincerely apologize for your experience and would like to make this right. Please contact us directly so we can resolve this issue promptly."
        elif review.rating == 3:
            return f"Thank you for your review. We appreciate your feedback and are always working to improve our service."
        else:
            return f"Thank you so much for your positive review! We're thrilled to hear about your great experience."
    else:
        return f"Dear {review.customer_name or 'Valued Customer'}, we noticed your recent review and would like to personally address your concerns. Please reply to this message so we can discuss how to improve your experience."
