"""
Review Processing Background Tasks

This module contains Celery tasks for processing reviews, including ingestion,
sentiment analysis, urgency classification, and automated response generation.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from celery import current_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery import celery_app
from app.core.database import get_async_db_context
from app.models.customer import Customer
from app.models.review import Review
from app.services.agent_engine import AgentEngine
from app.services.categorization_service import CategorizationService
from app.services.llm.response_generation_service import get_llm_service
from app.services.sentiment_service import SentimentService
from app.services.urgency_service import UrgencyService


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingest and process a new review

    Args:
        review_data: Dictionary containing review information

    Returns:
        Processing results
    """
    try:
        # Run async processing in sync context
        return asyncio.run(_process_review_ingestion(review_data))

    except Exception as exc:
        # Log the error and retry
        current_task.update_state(
            state="FAILURE",
            meta={
                "error": str(exc),
                "review_data": review_data,
                "retry_count": self.request.retries,
            },
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))

        # Send to dead letter queue after max retries
        celery_app.send_task(
            "app.tasks.monitoring_tasks.log_failed_task",
            args=[self.request.id, str(exc), "Review ingestion failed"],
            queue="dead_letter",
        )

        raise exc


async def _process_review_ingestion(review_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process review ingestion asynchronously"""
    async with get_async_db_context() as db:
        # Create or get customer
        customer = await _get_or_create_customer(db, review_data)

        # Create review record
        review = Review(
            organization_id=review_data["organization_id"],
            customer_id=customer.id,
            platform=review_data.get("platform", "google"),
            external_review_id=review_data.get("external_review_id"),
            rating=review_data["rating"],
            content=review_data["content"],
            review_date=datetime.fromisoformat(review_data["review_date"]),
            reviewer_name=review_data.get("reviewer_name"),
            reviewer_location=review_data.get("reviewer_location"),
            status="pending",
        )

        db.add(review)
        await db.flush()  # Get the ID

        # Process review analysis
        analysis_results = await _analyze_review(review, db)

        # Update review with analysis results
        review.sentiment_score = analysis_results["sentiment_score"]
        review.urgency_level = analysis_results["urgency_level"]
        review.categories = analysis_results["categories"]
        review.confidence_score = analysis_results["confidence_score"]

        # Update customer statistics
        customer.add_review_stats(review.rating)

        await db.commit()

        # Trigger follow-up tasks
        if analysis_results["urgency_level"] in ["high", "medium"]:
            # Schedule agent decision task
            celery_app.send_task(
                "app.tasks.recovery_tasks.process_review_for_action",
                args=[str(review.id)],
                queue="recovery",
                countdown=30,  # Process in 30 seconds
            )

        return {
            "review_id": str(review.id),
            "customer_id": str(customer.id),
            "analysis_results": analysis_results,
            "status": "completed",
        }


async def _get_or_create_customer(
    db: AsyncSession, review_data: Dict[str, Any]
) -> Customer:
    """Get existing customer or create new one"""
    from sqlalchemy import select

    # Try to find existing customer by email or external ID
    customer_email = review_data.get("customer_email")
    external_customer_id = review_data.get("external_customer_id")

    customer = None

    if customer_email:
        result = await db.execute(
            select(Customer).where(
                Customer.email == customer_email,
                Customer.organization_id == review_data["organization_id"],
            )
        )
        customer = result.scalar_one_or_none()

    if not customer and external_customer_id:
        result = await db.execute(
            select(Customer).where(
                Customer.external_id == external_customer_id,
                Customer.organization_id == review_data["organization_id"],
            )
        )
        customer = result.scalar_one_or_none()

    # Create new customer if not found
    if not customer:
        customer = Customer(
            organization_id=review_data["organization_id"],
            email=customer_email,
            name=review_data.get("customer_name"),
            external_id=external_customer_id,
            phone=review_data.get("customer_phone"),
        )
        db.add(customer)
        await db.flush()

    return customer


async def _analyze_review(review: Review, db: AsyncSession) -> Dict[str, Any]:
    """Analyze review for sentiment, urgency, and categories"""
    # Initialize services
    sentiment_service = SentimentService()
    urgency_service = UrgencyService()
    categorization_service = CategorizationService()

    # Perform analysis
    sentiment_score = sentiment_service.analyze_sentiment(review.content)
    urgency_result = urgency_service.classify_urgency(review.content, review.rating)
    categories = categorization_service.categorize_review(review.content)

    # Calculate overall confidence
    confidence_score = (
        sentiment_result.get("confidence", 0.8) * 0.4
        + urgency_result.get("confidence", 0.8) * 0.3
        + (
            sum(cat.get("confidence", 0.8) for cat in categories)
            / max(len(categories), 1)
        )
        * 0.3
    )

    return {
        "sentiment_score": sentiment_score,
        "urgency_level": urgency_result["urgency_level"],
        "categories": [cat["category"] for cat in categories],
        "confidence_score": confidence_score,
        "analysis_metadata": {
            "sentiment_details": {"score": sentiment_score},
            "urgency_details": urgency_result,
            "category_details": categories,
        },
    }


@celery_app.task(bind=True, max_retries=3)
def generate_review_response(
    self, review_id: str, auto_publish: bool = False
) -> Dict[str, Any]:
    """
    Generate an automated response to a review

    Args:
        review_id: Review ID to respond to
        auto_publish: Whether to automatically publish the response

    Returns:
        Generated response details
    """
    try:
        return asyncio.run(_generate_review_response_async(review_id, auto_publish))

    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={
                "error": str(exc),
                "review_id": review_id,
                "retry_count": self.request.retries,
            },
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))

        raise exc


async def _generate_review_response_async(
    review_id: str, auto_publish: bool
) -> Dict[str, Any]:
    """Generate review response asynchronously"""
    async with get_async_db_context() as db:
        # Get review with customer data
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Review)
            .options(selectinload(Review.customer))
            .where(Review.id == review_id)
        )
        review = result.scalar_one_or_none()

        if not review:
            raise ValueError(f"Review {review_id} not found")

        # Generate response using LLM service
        llm_service = get_llm_service()

        response = await llm_service.generate_review_response(
            rating=review.rating,
            review_content=review.content,
            customer_name=(
                review.customer.display_name if review.customer else "Valued Customer"
            ),
            business_type="business",  # Could be made configurable
        )

        # Store the generated response
        review.ai_response = response.content
        review.ai_response_confidence = response.metadata.get("quality_score", 0.8)
        review.response_generated_at = datetime.now(timezone.utc)

        if auto_publish:
            review.status = "responded"
            review.responded_at = datetime.now(timezone.utc)
        else:
            review.status = "response_pending"

        await db.commit()

        return {
            "review_id": review_id,
            "response_content": response.content,
            "confidence_score": response.metadata.get("quality_score", 0.8),
            "auto_published": auto_publish,
            "status": "completed",
        }


@celery_app.task(bind=True)
def batch_process_reviews(self, review_ids: List[str]) -> Dict[str, Any]:
    """
    Process multiple reviews in batch

    Args:
        review_ids: List of review IDs to process

    Returns:
        Batch processing results
    """
    results = {"processed": 0, "failed": 0, "results": []}

    for review_id in review_ids:
        try:
            # Schedule individual review processing
            task = celery_app.send_task(
                "app.tasks.review_tasks.ingest_review",
                args=[{"review_id": review_id}],
                queue="reviews",
            )

            results["results"].append(
                {"review_id": review_id, "task_id": task.id, "status": "scheduled"}
            )
            results["processed"] += 1

        except Exception as e:
            results["results"].append(
                {"review_id": review_id, "status": "failed", "error": str(e)}
            )
            results["failed"] += 1

    return results


@celery_app.task(bind=True)
def cleanup_old_reviews(self, days_old: int = 90) -> Dict[str, Any]:
    """
    Clean up old review data

    Args:
        days_old: Number of days after which to clean up reviews

    Returns:
        Cleanup results
    """
    try:
        return asyncio.run(_cleanup_old_reviews_async(days_old))

    except Exception as exc:
        current_task.update_state(
            state="FAILURE", meta={"error": str(exc), "days_old": days_old}
        )
        raise exc


async def _cleanup_old_reviews_async(days_old: int) -> Dict[str, Any]:
    """Clean up old reviews asynchronously"""
    async with get_async_db_context() as db:
        from sqlalchemy import delete, select

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        # Count reviews to be cleaned up
        count_result = await db.execute(
            select(func.count(Review.id)).where(Review.created_at < cutoff_date)
        )
        count = count_result.scalar()

        # Delete old reviews
        await db.execute(delete(Review).where(Review.created_at < cutoff_date))

        await db.commit()

        return {
            "cleaned_up_count": count,
            "cutoff_date": cutoff_date.isoformat(),
            "status": "completed",
        }


@celery_app.task(bind=True)
def reprocess_failed_reviews(self) -> Dict[str, Any]:
    """
    Reprocess reviews that failed initial processing

    Returns:
        Reprocessing results
    """
    try:
        return asyncio.run(_reprocess_failed_reviews_async())

    except Exception as exc:
        current_task.update_state(state="FAILURE", meta={"error": str(exc)})
        raise exc


async def _reprocess_failed_reviews_async() -> Dict[str, Any]:
    """Reprocess failed reviews asynchronously"""
    async with get_async_db_context() as db:
        from sqlalchemy import select

        # Find reviews with failed status
        result = await db.execute(
            select(Review)
            .where(Review.status == "failed")
            .limit(50)  # Process in batches
        )
        failed_reviews = result.scalars().all()

        reprocessed = 0
        for review in failed_reviews:
            try:
                # Reanalyze the review
                analysis_results = await _analyze_review(review, db)

                # Update review with new analysis
                review.sentiment_score = analysis_results["sentiment_score"]
                review.urgency_level = analysis_results["urgency_level"]
                review.categories = analysis_results["categories"]
                review.confidence_score = analysis_results["confidence_score"]
                review.status = "pending"

                reprocessed += 1

            except Exception as e:
                # Log individual failures but continue processing
                print(f"Failed to reprocess review {review.id}: {e}")

        await db.commit()

        return {
            "total_failed_reviews": len(failed_reviews),
            "reprocessed_count": reprocessed,
            "status": "completed",
        }


# Aliases for backward compatibility
process_review_analysis = ingest_review
