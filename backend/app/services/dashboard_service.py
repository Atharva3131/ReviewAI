"""
Dashboard metrics service for calculating and providing KPIs
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import CacheManager, redis_client
from app.models.agent_decision import AgentDecision
from app.models.customer import Customer
from app.models.recovery_action import RecoveryAction
from app.models.review import Review
from app.models.support_ticket import SupportTicket
from app.services.metrics_cache import cached_metrics, metrics_cache

logger = logging.getLogger(__name__)


class DashboardMetricsService:
    """Service for calculating dashboard KPIs and metrics"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache_ttl = 300  # 5 minutes cache

    @cached_metrics(cache_type="kpis", warm_cache=True)
    async def get_comprehensive_metrics(
        self, organization_id: str, time_range: str = "30d"
    ) -> Dict[str, Any]:
        """
        Get comprehensive dashboard metrics for an organization

        Args:
            organization_id: Organization UUID
            time_range: Time range for metrics (7d, 30d, 90d, 1y)

        Returns:
            Dictionary containing all dashboard metrics
        """
        # Parse time range
        days = self._parse_time_range(time_range)
        start_date = datetime.utcnow() - timedelta(days=days)

        # Check cache first
        cache_key = CacheManager.make_key(
            "dashboard_metrics", organization_id, time_range, prefix="revive_ai"
        )

        cached_metrics = await redis_client.get_json(cache_key)
        if cached_metrics:
            logger.info(f"Returning cached dashboard metrics for org {organization_id}")
            return cached_metrics

        # Calculate all metrics
        logger.info(
            f"Calculating dashboard metrics for org {organization_id}, range: {time_range}"
        )

        metrics = {
            "kpis": await self._calculate_kpis(organization_id, start_date),
            "trends": await self._calculate_trends(organization_id, start_date),
            "activity_feed": await self._generate_activity_feed(
                organization_id, limit=10
            ),
            "charts": await self._generate_chart_data(organization_id, start_date),
            "alerts": await self._generate_alerts(organization_id),
            "metadata": {
                "organization_id": organization_id,
                "time_range": time_range,
                "start_date": start_date.isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "generated_at": datetime.utcnow().isoformat(),
                "cache_ttl": self.cache_ttl,
            },
        }

        # Cache the results
        await redis_client.set_json(cache_key, metrics, self.cache_ttl)

        return metrics

    async def _calculate_kpis(
        self, organization_id: str, start_date: datetime
    ) -> Dict[str, Any]:
        """Calculate key performance indicators"""

        # Average rating calculation
        avg_rating_result = await self.db.execute(
            select(func.avg(Review.rating)).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.created_at >= start_date,
                )
            )
        )
        avg_rating = avg_rating_result.scalar()

        # Previous period for comparison
        prev_start = start_date - (datetime.utcnow() - start_date)
        prev_avg_rating_result = await self.db.execute(
            select(func.avg(Review.rating)).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.created_at >= prev_start,
                    Review.created_at < start_date,
                )
            )
        )
        prev_avg_rating = prev_avg_rating_result.scalar()

        # Monthly review count
        review_count_result = await self.db.execute(
            select(func.count(Review.id)).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.created_at >= start_date,
                )
            )
        )
        review_count = review_count_result.scalar() or 0

        # Previous period review count
        prev_review_count_result = await self.db.execute(
            select(func.count(Review.id)).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.created_at >= prev_start,
                    Review.created_at < start_date,
                )
            )
        )
        prev_review_count = prev_review_count_result.scalar() or 0

        # At-risk customer count
        at_risk_count_result = await self.db.execute(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.organization_id == organization_id,
                    or_(
                        Customer.churn_risk_score >= 0.7,
                        Customer.bad_review_likelihood >= 0.6,
                    ),
                )
            )
        )
        at_risk_count = at_risk_count_result.scalar() or 0

        # Recovery success rate
        total_recovery_actions_result = await self.db.execute(
            select(func.count(RecoveryAction.id)).where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date,
                    RecoveryAction.status.in_(["sent", "completed", "failed"]),
                )
            )
        )
        total_recovery_actions = total_recovery_actions_result.scalar() or 0

        successful_recovery_actions_result = await self.db.execute(
            select(func.count(RecoveryAction.id)).where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date,
                    RecoveryAction.status == "completed",
                )
            )
        )
        successful_recovery_actions = successful_recovery_actions_result.scalar() or 0

        recovery_success_rate = (
            (successful_recovery_actions / total_recovery_actions * 100)
            if total_recovery_actions > 0
            else 0
        )

        # Calculate trends
        rating_trend = self._calculate_trend(avg_rating, prev_avg_rating)
        review_trend = self._calculate_trend(review_count, prev_review_count)

        return {
            "average_rating": {
                "value": round(float(avg_rating or 0), 2),
                "trend": rating_trend,
                "previous_value": round(float(prev_avg_rating or 0), 2),
            },
            "monthly_reviews": {
                "value": review_count,
                "trend": review_trend,
                "previous_value": prev_review_count,
            },
            "at_risk_customers": {
                "value": at_risk_count,
                "trend": "neutral",  # TODO: Calculate trend
                "threshold": 0.7,
            },
            "recovery_success_rate": {
                "value": round(recovery_success_rate, 1),
                "trend": "neutral",  # TODO: Calculate trend
                "total_actions": total_recovery_actions,
                "successful_actions": successful_recovery_actions,
            },
        }

    async def _calculate_trends(
        self, organization_id: str, start_date: datetime
    ) -> Dict[str, Any]:
        """Calculate trend data for charts"""

        # Sentiment trends over time
        sentiment_trends = await self._get_sentiment_trends(organization_id, start_date)

        # Review volume trends
        review_volume_trends = await self._get_review_volume_trends(
            organization_id, start_date
        )

        # Recovery action trends
        recovery_trends = await self._get_recovery_trends(organization_id, start_date)

        return {
            "sentiment_over_time": sentiment_trends,
            "review_volume_over_time": review_volume_trends,
            "recovery_actions_over_time": recovery_trends,
        }

    @cached_metrics(cache_type="activity_feed", warm_cache=False)
    async def _generate_activity_feed(
        self, organization_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Generate recent activity feed"""

        activities = []

        # Recent reviews
        recent_reviews = await self.db.execute(
            select(Review)
            .where(Review.organization_id == organization_id)
            .order_by(desc(Review.created_at))
            .limit(5)
        )

        for review in recent_reviews.scalars():
            urgency_emoji = (
                "🔴"
                if review.urgency_level == "high"
                else "🟡" if review.urgency_level == "medium" else "🟢"
            )
            activities.append(
                {
                    "id": f"review_{review.id}",
                    "type": "review",
                    "title": f"New {review.rating}★ review received",
                    "description": f"{urgency_emoji} {review.urgency_level.title()} urgency - {review.customer_name or 'Anonymous'}",
                    "timestamp": review.created_at.isoformat(),
                    "metadata": {
                        "review_id": str(review.id),
                        "rating": review.rating,
                        "urgency": review.urgency_level,
                        "sentiment_score": float(review.sentiment_score or 0),
                    },
                }
            )

        # Recent recovery actions
        recent_recovery_actions = await self.db.execute(
            select(RecoveryAction)
            .where(RecoveryAction.organization_id == organization_id)
            .order_by(desc(RecoveryAction.created_at))
            .limit(5)
        )

        for action in recent_recovery_actions.scalars():
            status_emoji = (
                "✅"
                if action.status == "completed"
                else "📤" if action.status == "sent" else "⏳"
            )
            activities.append(
                {
                    "id": f"recovery_{action.id}",
                    "type": "recovery_action",
                    "title": f"Recovery action {action.status}",
                    "description": f"{status_emoji} {action.action_type.title()} action for customer",
                    "timestamp": action.created_at.isoformat(),
                    "metadata": {
                        "action_id": str(action.id),
                        "action_type": action.action_type,
                        "status": action.status,
                    },
                }
            )

        # Recent agent decisions
        recent_decisions = await self.db.execute(
            select(AgentDecision)
            .where(AgentDecision.organization_id == organization_id)
            .order_by(desc(AgentDecision.created_at))
            .limit(3)
        )

        for decision in recent_decisions.scalars():
            confidence_emoji = (
                "🎯"
                if decision.confidence_score >= 0.8
                else "🤔" if decision.confidence_score >= 0.6 else "❓"
            )
            activities.append(
                {
                    "id": f"decision_{decision.id}",
                    "type": "agent_decision",
                    "title": f"Agent decision: {decision.decision_type}",
                    "description": f"{confidence_emoji} {decision.confidence_score:.0%} confidence - {decision.reasoning[:50]}...",
                    "timestamp": decision.created_at.isoformat(),
                    "metadata": {
                        "decision_id": str(decision.id),
                        "decision_type": decision.decision_type,
                        "confidence_score": float(decision.confidence_score or 0),
                    },
                }
            )

        # Sort by timestamp and limit
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        return activities[:limit]

    async def _generate_chart_data(
        self, organization_id: str, start_date: datetime
    ) -> Dict[str, Any]:
        """Generate data for dashboard charts"""

        # Sentiment distribution pie chart
        sentiment_distribution = await self._get_sentiment_distribution(
            organization_id, start_date
        )

        # Rating distribution
        rating_distribution = await self._get_rating_distribution(
            organization_id, start_date
        )

        # Issue categories
        issue_categories = await self._get_issue_categories(organization_id, start_date)

        return {
            "sentiment_distribution": sentiment_distribution,
            "rating_distribution": rating_distribution,
            "issue_categories": issue_categories,
        }

    async def _generate_alerts(self, organization_id: str) -> List[Dict[str, Any]]:
        """Generate alerts for dashboard"""

        alerts = []

        # High-risk customers alert
        high_risk_count = await self.db.execute(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.organization_id == organization_id,
                    Customer.churn_risk_score >= 0.8,
                )
            )
        )
        high_risk_count = high_risk_count.scalar() or 0

        if high_risk_count > 0:
            alerts.append(
                {
                    "id": "high_risk_customers",
                    "type": "warning",
                    "title": f"{high_risk_count} high-risk customers detected",
                    "description": "Customers with churn risk score ≥ 80% need immediate attention",
                    "action": "Review customer recovery recommendations",
                    "priority": "high",
                }
            )

        # Recent negative reviews alert
        recent_negative = await self.db.execute(
            select(func.count(Review.id)).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.rating <= 2,
                    Review.created_at >= datetime.utcnow() - timedelta(hours=24),
                )
            )
        )
        recent_negative = recent_negative.scalar() or 0

        if recent_negative > 3:
            alerts.append(
                {
                    "id": "negative_reviews_spike",
                    "type": "error",
                    "title": f"{recent_negative} negative reviews in last 24h",
                    "description": "Unusual spike in negative reviews detected",
                    "action": "Investigate recent service issues",
                    "priority": "high",
                }
            )

        return alerts

    # Helper methods

    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to days"""
        range_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        return range_map.get(time_range, 30)

    def _calculate_trend(
        self, current: Optional[float], previous: Optional[float]
    ) -> str:
        """Calculate trend direction"""
        if not current or not previous:
            return "neutral"

        change = ((current - previous) / previous) * 100

        if change > 5:
            return "up"
        elif change < -5:
            return "down"
        else:
            return "neutral"

    async def _get_sentiment_trends(
        self, organization_id: str, start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get sentiment trends over time"""
        # TODO: Implement daily sentiment aggregation
        return []

    async def _get_review_volume_trends(
        self, organization_id: str, start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get review volume trends over time"""
        # TODO: Implement daily review volume aggregation
        return []

    async def _get_recovery_trends(
        self, organization_id: str, start_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get recovery action trends over time"""
        # TODO: Implement daily recovery action aggregation
        return []

    async def _get_sentiment_distribution(
        self, organization_id: str, start_date: datetime
    ) -> Dict[str, Any]:
        """Get sentiment distribution for pie chart"""

        # Count reviews by sentiment ranges
        positive_count = await self.db.execute(
            select(func.count(Review.id)).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.created_at >= start_date,
                    Review.sentiment_score >= 0.6,
                )
            )
        )

        neutral_count = await self.db.execute(
            select(func.count(Review.id)).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.created_at >= start_date,
                    Review.sentiment_score >= 0.4,
                    Review.sentiment_score < 0.6,
                )
            )
        )

        negative_count = await self.db.execute(
            select(func.count(Review.id)).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.created_at >= start_date,
                    Review.sentiment_score < 0.4,
                )
            )
        )

        return {
            "positive": positive_count.scalar() or 0,
            "neutral": neutral_count.scalar() or 0,
            "negative": negative_count.scalar() or 0,
        }

    async def _get_rating_distribution(
        self, organization_id: str, start_date: datetime
    ) -> Dict[str, int]:
        """Get rating distribution"""

        distribution = {}
        for rating in range(1, 6):
            count_result = await self.db.execute(
                select(func.count(Review.id)).where(
                    and_(
                        Review.organization_id == organization_id,
                        Review.created_at >= start_date,
                        Review.rating == rating,
                    )
                )
            )
            distribution[str(rating)] = count_result.scalar() or 0

        return distribution

    async def _get_issue_categories(
        self, organization_id: str, start_date: datetime
    ) -> Dict[str, int]:
        """Get issue category distribution"""

        # This would need to be implemented based on how issue_categories are stored
        # For now, return mock data
        return {"support": 45, "quality": 32, "delivery": 28, "pricing": 15}


class KPICalculationService:
    """Specialized service for KPI calculations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_average_rating(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> Tuple[float, int]:
        """
        Calculate average rating for time period

        Returns:
            Tuple of (average_rating, total_reviews)
        """
        end_date = end_date or datetime.utcnow()

        result = await self.db.execute(
            select(
                func.avg(Review.rating).label("avg_rating"),
                func.count(Review.id).label("total_reviews"),
            ).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.created_at >= start_date,
                    Review.created_at <= end_date,
                )
            )
        )

        row = result.first()
        avg_rating = float(row.avg_rating or 0)
        total_reviews = row.total_reviews or 0

        return avg_rating, total_reviews

    async def calculate_monthly_review_count(
        self, organization_id: str, months_back: int = 1
    ) -> int:
        """Calculate review count for the last N months"""

        start_date = datetime.utcnow() - timedelta(days=30 * months_back)

        result = await self.db.execute(
            select(func.count(Review.id)).where(
                and_(
                    Review.organization_id == organization_id,
                    Review.created_at >= start_date,
                )
            )
        )

        return result.scalar() or 0

    async def calculate_at_risk_customer_count(
        self,
        organization_id: str,
        churn_threshold: float = 0.7,
        review_threshold: float = 0.6,
    ) -> Dict[str, int]:
        """Calculate at-risk customer counts with breakdown"""

        # High churn risk
        high_churn_result = await self.db.execute(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.organization_id == organization_id,
                    Customer.churn_risk_score >= churn_threshold,
                )
            )
        )

        # High bad review likelihood
        high_review_risk_result = await self.db.execute(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.organization_id == organization_id,
                    Customer.bad_review_likelihood >= review_threshold,
                )
            )
        )

        # Both risks
        both_risks_result = await self.db.execute(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.organization_id == organization_id,
                    Customer.churn_risk_score >= churn_threshold,
                    Customer.bad_review_likelihood >= review_threshold,
                )
            )
        )

        return {
            "high_churn_risk": high_churn_result.scalar() or 0,
            "high_review_risk": high_review_risk_result.scalar() or 0,
            "both_risks": both_risks_result.scalar() or 0,
            "total_at_risk": max(
                high_churn_result.scalar() or 0, high_review_risk_result.scalar() or 0
            ),
        }

    async def calculate_recovery_success_rate(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Calculate recovery success rate with detailed breakdown"""

        end_date = end_date or datetime.utcnow()

        # Total recovery actions
        total_result = await self.db.execute(
            select(func.count(RecoveryAction.id)).where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date,
                    RecoveryAction.created_at <= end_date,
                )
            )
        )
        total_actions = total_result.scalar() or 0

        # Successful actions
        successful_result = await self.db.execute(
            select(func.count(RecoveryAction.id)).where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date,
                    RecoveryAction.created_at <= end_date,
                    RecoveryAction.status == "completed",
                )
            )
        )
        successful_actions = successful_result.scalar() or 0

        # Failed actions
        failed_result = await self.db.execute(
            select(func.count(RecoveryAction.id)).where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date,
                    RecoveryAction.created_at <= end_date,
                    RecoveryAction.status == "failed",
                )
            )
        )
        failed_actions = failed_result.scalar() or 0

        # Pending actions
        pending_actions = total_actions - successful_actions - failed_actions

        success_rate = (
            (successful_actions / total_actions * 100) if total_actions > 0 else 0
        )

        return {
            "success_rate": round(success_rate, 1),
            "total_actions": total_actions,
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "pending_actions": pending_actions,
        }


# Alias for backward compatibility
DashboardService = DashboardMetricsService
