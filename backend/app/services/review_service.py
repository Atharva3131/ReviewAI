"""
Review service for managing review operations and analysis
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import AccessControlContext
from app.models.customer import Customer
from app.models.review import (
    IssueCategory,
    Review,
    ReviewPlatform,
    ReviewStatus,
    UrgencyLevel,
)
from app.schemas.review import ReviewFilter, ReviewIngest, ReviewStats


class ReviewService:
    """Service for review management and operations"""

    @staticmethod
    async def ingest_review(
        db: AsyncSession, organization_id: str, review_data: ReviewIngest
    ) -> Review:
        """Ingest a new review into the system"""

        # Check for duplicate review
        if review_data.external_id:
            existing_review = await db.execute(
                select(Review).where(
                    and_(
                        Review.organization_id == organization_id,
                        Review.platform == review_data.platform,
                        Review.external_id == review_data.external_id,
                    )
                )
            )

            if existing_review.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Review with this external ID already exists",
                )

        # Find or create customer if email provided
        customer_id = None
        customer = None
        if review_data.customer_email:
            customer = await ReviewService._find_or_create_customer(
                db,
                organization_id,
                review_data.customer_email,
                review_data.customer_name,
            )
            customer_id = customer.id

        # Create review
        review = Review(
            organization_id=organization_id,
            platform=review_data.platform,
            external_id=review_data.external_id,
            review_url=review_data.review_url,
            customer_name=review_data.customer_name,
            customer_email=review_data.customer_email,
            customer_id=customer_id,
            rating=review_data.rating,
            title=review_data.title,
            content=review_data.content,
            review_date=review_data.review_date or datetime.now(timezone.utc),
            status=ReviewStatus.PENDING,
        )

        db.add(review)

        # Update customer review statistics if customer exists
        if customer:
            customer.add_review_stats(review_data.rating)
            customer.update_interaction()

        await db.commit()
        await db.refresh(review)

        return review

    @staticmethod
    async def get_reviews(
        db: AsyncSession,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[ReviewFilter] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> List[Review]:
        """Get reviews with filtering and sorting"""

        query = select(Review).where(Review.organization_id == organization_id)

        # Apply filters
        if filters:
            if filters.platform:
                query = query.where(Review.platform == filters.platform)

            if filters.rating_min is not None:
                query = query.where(Review.rating >= filters.rating_min)

            if filters.rating_max is not None:
                query = query.where(Review.rating <= filters.rating_max)

            if filters.sentiment_min is not None:
                query = query.where(Review.sentiment_score >= filters.sentiment_min)

            if filters.sentiment_max is not None:
                query = query.where(Review.sentiment_score <= filters.sentiment_max)

            if filters.urgency_level:
                query = query.where(Review.urgency_level == filters.urgency_level)

            if filters.status:
                query = query.where(Review.status == filters.status)

            if filters.issue_categories:
                # Check if review has any of the specified categories
                for category in filters.issue_categories:
                    query = query.where(Review.issue_categories.contains([category]))

            if filters.requires_private_recovery is not None:
                query = query.where(
                    Review.requires_private_recovery
                    == filters.requires_private_recovery
                )

            if filters.date_from:
                query = query.where(Review.review_date >= filters.date_from)

            if filters.date_to:
                query = query.where(Review.review_date <= filters.date_to)

            if filters.search:
                search_term = f"%{filters.search.lower()}%"
                query = query.where(
                    or_(
                        func.lower(Review.content).like(search_term),
                        func.lower(Review.title).like(search_term),
                        func.lower(Review.customer_name).like(search_term),
                    )
                )

        # Apply sorting
        if sort_order.lower() == "desc":
            query = query.order_by(desc(getattr(Review, sort_by)))
        else:
            query = query.order_by(getattr(Review, sort_by))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_review_by_id(
        db: AsyncSession, review_id: str, organization_id: str
    ) -> Optional[Review]:
        """Get review by ID within organization"""
        try:
            review_uuid = uuid.UUID(review_id)
            result = await db.execute(
                select(Review).where(
                    and_(
                        Review.id == review_uuid,
                        Review.organization_id == organization_id,
                    )
                )
            )
            return result.scalar_one_or_none()
        except (ValueError, TypeError):
            return None

    @staticmethod
    async def update_review(
        db: AsyncSession, review_id: str, organization_id: str, updates: Dict[str, Any]
    ) -> Review:
        """Update review information"""

        review = await ReviewService.get_review_by_id(db, review_id, organization_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )

        # Update allowed fields
        allowed_fields = {
            "sentiment_score",
            "urgency_level",
            "issue_categories",
            "status",
            "requires_private_recovery",
            "public_response",
            "internal_notes",
            "processed_at",
        }

        for field, value in updates.items():
            if field in allowed_fields and hasattr(review, field):
                setattr(review, field, value)

        if "public_response" in updates and updates["public_response"]:
            review.public_response_date = datetime.now(timezone.utc)
            review.status = ReviewStatus.RESPONDED

        await db.commit()
        await db.refresh(review)

        return review

    @staticmethod
    async def get_review_stats(
        db: AsyncSession,
        organization_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> ReviewStats:
        """Get review statistics for organization"""

        base_query = select(Review).where(Review.organization_id == organization_id)

        if date_from:
            base_query = base_query.where(Review.review_date >= date_from)
        if date_to:
            base_query = base_query.where(Review.review_date <= date_to)

        # Total reviews
        total_result = await db.execute(
            select(func.count(Review.id)).where(
                Review.organization_id == organization_id
            )
        )
        total_reviews = total_result.scalar()

        if total_reviews == 0:
            return ReviewStats(
                total_reviews=0,
                avg_rating=0.0,
                rating_distribution={},
                sentiment_distribution={},
                urgency_distribution={},
                status_distribution={},
                category_distribution={},
                recent_reviews=0,
                response_rate=0.0,
                private_recovery_rate=0.0,
            )

        # Average rating
        avg_rating_result = await db.execute(
            select(func.avg(Review.rating)).where(
                Review.organization_id == organization_id
            )
        )
        avg_rating = float(avg_rating_result.scalar() or 0.0)

        # Rating distribution
        rating_dist_result = await db.execute(
            select(Review.rating, func.count(Review.id))
            .where(Review.organization_id == organization_id)
            .group_by(Review.rating)
        )
        rating_distribution = {
            str(rating): count for rating, count in rating_dist_result
        }

        # Status distribution
        status_dist_result = await db.execute(
            select(Review.status, func.count(Review.id))
            .where(Review.organization_id == organization_id)
            .group_by(Review.status)
        )
        status_distribution = {
            status.value: count for status, count in status_dist_result
        }

        # Response rate
        responded_count = await db.execute(
            select(func.count(Review.id)).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.status == ReviewStatus.RESPONDED,
                )
            )
        )
        response_rate = (
            (responded_count.scalar() / total_reviews) * 100
            if total_reviews > 0
            else 0.0
        )

        # Private recovery rate
        recovery_count = await db.execute(
            select(func.count(Review.id)).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.requires_private_recovery == True,
                )
            )
        )
        private_recovery_rate = (
            (recovery_count.scalar() / total_reviews) * 100
            if total_reviews > 0
            else 0.0
        )

        return ReviewStats(
            total_reviews=total_reviews,
            avg_rating=round(avg_rating, 2),
            rating_distribution=rating_distribution,
            sentiment_distribution={},  # Will be populated after sentiment analysis
            urgency_distribution={},  # Will be populated after urgency analysis
            status_distribution=status_distribution,
            category_distribution={},  # Will be populated after categorization
            recent_reviews=total_reviews,  # Simplified for now
            response_rate=round(response_rate, 2),
            private_recovery_rate=round(private_recovery_rate, 2),
        )

    @staticmethod
    async def _find_or_create_customer(
        db: AsyncSession, organization_id: str, email: str, name: Optional[str] = None
    ) -> Customer:
        """Find existing customer or create new one"""

        # Try to find existing customer
        result = await db.execute(
            select(Customer).where(
                and_(
                    Customer.organization_id == organization_id,
                    Customer.email == email.lower(),
                )
            )
        )

        customer = result.scalar_one_or_none()

        if not customer:
            # Create new customer
            customer = Customer(
                organization_id=organization_id,
                email=email.lower(),
                name=name,
                status="active",
            )
            db.add(customer)
            await db.flush()  # Get the customer ID

        return customer

    @staticmethod
    async def mark_review_processed(
        db: AsyncSession,
        review_id: str,
        organization_id: str,
        analysis_results: Dict[str, Any],
    ) -> Review:
        """Mark review as processed with analysis results"""

        review = await ReviewService.get_review_by_id(db, review_id, organization_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
            )

        # Update review with analysis results
        review.sentiment_score = analysis_results.get("sentiment_score")
        review.urgency_level = analysis_results.get("urgency_level")
        review.issue_categories = analysis_results.get("issue_categories", [])
        review.requires_private_recovery = analysis_results.get(
            "requires_private_recovery", False
        )
        review.processed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(review)

        return review
