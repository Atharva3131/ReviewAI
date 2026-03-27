"""
Metrics Aggregation Background Tasks

This module contains Celery tasks for aggregating metrics, calculating KPIs,
updating customer risk scores, and generating analytics data.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from celery import current_task
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery import celery_app
from app.core.database import get_async_db_context
from app.models.customer import Customer
from app.models.recovery_action import RecoveryAction
from app.models.review import Review
from app.models.support_ticket import SupportTicket
from app.services.customer_risk_service import CustomerRiskAssessmentService


@celery_app.task(bind=True, max_retries=2)
def aggregate_metrics(self, organization_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Aggregate metrics for dashboard and reporting

    Args:
        organization_id: Optional organization ID to filter by

    Returns:
        Aggregated metrics
    """
    try:
        return asyncio.run(_aggregate_metrics_async(organization_id))

    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={
                "error": str(exc),
                "organization_id": organization_id,
                "retry_count": self.request.retries,
            },
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=300)  # 5 minutes

        raise exc


async def _aggregate_metrics_async(organization_id: Optional[str]) -> Dict[str, Any]:
    """Aggregate metrics asynchronously"""
    async with get_async_db_context() as db:
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # Base query filter
        org_filter = (
            Customer.organization_id == organization_id if organization_id else True
        )

        # 1. Review Metrics
        review_metrics = await _calculate_review_metrics(
            db, org_filter, thirty_days_ago
        )

        # 2. Customer Metrics
        customer_metrics = await _calculate_customer_metrics(db, org_filter)

        # 3. Recovery Action Metrics
        recovery_metrics = await _calculate_recovery_metrics(
            db, org_filter, thirty_days_ago
        )

        # 4. Support Ticket Metrics
        support_metrics = await _calculate_support_metrics(
            db, org_filter, thirty_days_ago
        )

        # 5. Performance Metrics
        performance_metrics = await _calculate_performance_metrics(
            db, org_filter, thirty_days_ago
        )

        aggregated_data = {
            "organization_id": organization_id,
            "aggregation_timestamp": now.isoformat(),
            "period_days": 30,
            "review_metrics": review_metrics,
            "customer_metrics": customer_metrics,
            "recovery_metrics": recovery_metrics,
            "support_metrics": support_metrics,
            "performance_metrics": performance_metrics,
        }

        # Store aggregated metrics (in production, this would go to a metrics table)
        # For now, we'll just return the data

        return aggregated_data


async def _calculate_review_metrics(
    db: AsyncSession, org_filter, start_date: datetime
) -> Dict[str, Any]:
    """Calculate review-related metrics"""
    # Total reviews
    total_reviews_result = await db.execute(
        select(func.count(Review.id))
        .join(Customer)
        .where(and_(org_filter, Review.created_at >= start_date))
    )
    total_reviews = total_reviews_result.scalar() or 0

    # Average rating
    avg_rating_result = await db.execute(
        select(func.avg(Review.rating))
        .join(Customer)
        .where(and_(org_filter, Review.created_at >= start_date))
    )
    avg_rating = float(avg_rating_result.scalar() or 0)

    # Rating distribution
    rating_dist_result = await db.execute(
        select(Review.rating, func.count(Review.id))
        .join(Customer)
        .where(and_(org_filter, Review.created_at >= start_date))
        .group_by(Review.rating)
    )
    rating_distribution = {
        str(rating): count for rating, count in rating_dist_result.fetchall()
    }

    # Sentiment metrics
    sentiment_result = await db.execute(
        select(
            func.avg(Review.sentiment_score).label("avg_sentiment"),
            func.count(Review.id)
            .filter(Review.sentiment_score < 0.4)
            .label("negative_count"),
            func.count(Review.id)
            .filter(Review.sentiment_score >= 0.6)
            .label("positive_count"),
        )
        .join(Customer)
        .where(
            and_(
                org_filter,
                Review.created_at >= start_date,
                Review.sentiment_score.isnot(None),
            )
        )
    )
    sentiment_data = sentiment_result.first()

    # Response metrics
    response_result = await db.execute(
        select(
            func.count(Review.id)
            .filter(Review.status == "responded")
            .label("responded_count"),
            func.count(Review.id)
            .filter(Review.ai_response.isnot(None))
            .label("ai_generated_count"),
        )
        .join(Customer)
        .where(and_(org_filter, Review.created_at >= start_date))
    )
    response_data = response_result.first()

    return {
        "total_reviews": total_reviews,
        "average_rating": round(avg_rating, 2),
        "rating_distribution": rating_distribution,
        "average_sentiment": round(float(sentiment_data.avg_sentiment or 0), 3),
        "negative_reviews": sentiment_data.negative_count or 0,
        "positive_reviews": sentiment_data.positive_count or 0,
        "responded_reviews": response_data.responded_count or 0,
        "ai_generated_responses": response_data.ai_generated_count or 0,
        "response_rate": round(
            (response_data.responded_count or 0) / max(total_reviews, 1), 3
        ),
    }


async def _calculate_customer_metrics(db: AsyncSession, org_filter) -> Dict[str, Any]:
    """Calculate customer-related metrics"""
    # Total customers
    total_customers_result = await db.execute(
        select(func.count(Customer.id)).where(org_filter)
    )
    total_customers = total_customers_result.scalar() or 0

    # At-risk customers
    at_risk_result = await db.execute(
        select(func.count(Customer.id)).where(
            and_(
                org_filter,
                or_(
                    Customer.churn_risk_score >= 0.6,
                    Customer.bad_review_likelihood >= 0.6,
                ),
            )
        )
    )
    at_risk_customers = at_risk_result.scalar() or 0

    # High-value customers
    high_value_result = await db.execute(
        select(func.count(Customer.id)).where(
            and_(org_filter, Customer.lifetime_value >= 1000)
        )
    )
    high_value_customers = high_value_result.scalar() or 0

    # Customer satisfaction
    satisfaction_result = await db.execute(
        select(func.avg(Customer.avg_rating_given)).where(
            and_(org_filter, Customer.avg_rating_given.isnot(None))
        )
    )
    avg_satisfaction = float(satisfaction_result.scalar() or 0)

    # New customers (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    new_customers_result = await db.execute(
        select(func.count(Customer.id)).where(
            and_(org_filter, Customer.created_at >= thirty_days_ago)
        )
    )
    new_customers = new_customers_result.scalar() or 0

    return {
        "total_customers": total_customers,
        "at_risk_customers": at_risk_customers,
        "high_value_customers": high_value_customers,
        "new_customers_30d": new_customers,
        "average_satisfaction": round(avg_satisfaction, 2),
        "at_risk_percentage": round(
            (at_risk_customers / max(total_customers, 1)) * 100, 1
        ),
    }


async def _calculate_recovery_metrics(
    db: AsyncSession, org_filter, start_date: datetime
) -> Dict[str, Any]:
    """Calculate recovery action metrics"""
    # Total recovery actions
    total_actions_result = await db.execute(
        select(func.count(RecoveryAction.id))
        .join(Customer)
        .where(and_(org_filter, RecoveryAction.created_at >= start_date))
    )
    total_actions = total_actions_result.scalar() or 0

    # Success metrics
    success_result = await db.execute(
        select(
            func.count(RecoveryAction.id)
            .filter(RecoveryAction.success == True)
            .label("successful"),
            func.count(RecoveryAction.id)
            .filter(RecoveryAction.customer_responded == True)
            .label("responded"),
            func.avg(RecoveryAction.outcome_rating).label("avg_effectiveness"),
        )
        .join(Customer)
        .where(and_(org_filter, RecoveryAction.created_at >= start_date))
    )
    success_data = success_result.first()

    # Action type distribution
    action_type_result = await db.execute(
        select(RecoveryAction.action_type, func.count(RecoveryAction.id))
        .join(Customer)
        .where(and_(org_filter, RecoveryAction.created_at >= start_date))
        .group_by(RecoveryAction.action_type)
    )
    action_type_distribution = {
        action_type.value: count for action_type, count in action_type_result.fetchall()
    }

    return {
        "total_recovery_actions": total_actions,
        "successful_actions": success_data.successful or 0,
        "customer_responses": success_data.responded or 0,
        "success_rate": round(
            (success_data.successful or 0) / max(total_actions, 1), 3
        ),
        "response_rate": round(
            (success_data.responded or 0) / max(total_actions, 1), 3
        ),
        "average_effectiveness": round(float(success_data.avg_effectiveness or 0), 3),
        "action_type_distribution": action_type_distribution,
    }


async def _calculate_support_metrics(
    db: AsyncSession, org_filter, start_date: datetime
) -> Dict[str, Any]:
    """Calculate support ticket metrics"""
    # Total tickets
    total_tickets_result = await db.execute(
        select(func.count(SupportTicket.id))
        .join(Customer)
        .where(and_(org_filter, SupportTicket.created_at >= start_date))
    )
    total_tickets = total_tickets_result.scalar() or 0

    # Status distribution
    status_result = await db.execute(
        select(SupportTicket.status, func.count(SupportTicket.id))
        .join(Customer)
        .where(and_(org_filter, SupportTicket.created_at >= start_date))
        .group_by(SupportTicket.status)
    )
    status_distribution = {
        status.value: count for status, count in status_result.fetchall()
    }

    # Priority distribution
    priority_result = await db.execute(
        select(SupportTicket.priority, func.count(SupportTicket.id))
        .join(Customer)
        .where(and_(org_filter, SupportTicket.created_at >= start_date))
        .group_by(SupportTicket.priority)
    )
    priority_distribution = {
        priority.value: count for priority, count in priority_result.fetchall()
    }

    return {
        "total_tickets": total_tickets,
        "status_distribution": status_distribution,
        "priority_distribution": priority_distribution,
        "resolution_rate": round(
            status_distribution.get("resolved", 0) / max(total_tickets, 1), 3
        ),
    }


async def _calculate_performance_metrics(
    db: AsyncSession, org_filter, start_date: datetime
) -> Dict[str, Any]:
    """Calculate system performance metrics"""
    # Average response time for AI-generated responses
    ai_response_time_result = await db.execute(
        select(
            func.avg(
                func.extract("epoch", Review.response_generated_at - Review.created_at)
            )
        )
        .join(Customer)
        .where(
            and_(
                org_filter,
                Review.created_at >= start_date,
                Review.response_generated_at.isnot(None),
            )
        )
    )
    avg_ai_response_time = float(ai_response_time_result.scalar() or 0)

    # Recovery action execution time
    recovery_time_result = await db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch", RecoveryAction.executed_at - RecoveryAction.created_at
                )
            )
        )
        .join(Customer)
        .where(
            and_(
                org_filter,
                RecoveryAction.created_at >= start_date,
                RecoveryAction.executed_at.isnot(None),
            )
        )
    )
    avg_recovery_time = float(recovery_time_result.scalar() or 0)

    return {
        "avg_ai_response_time_seconds": round(avg_ai_response_time, 1),
        "avg_recovery_execution_time_seconds": round(avg_recovery_time, 1),
        "system_uptime_percentage": 99.9,  # Would be calculated from monitoring data
        "api_success_rate": 0.995,  # Would be calculated from API logs
    }


@celery_app.task(bind=True)
def batch_update_risk_scores(
    self, organization_id: str, limit: int = 50
) -> Dict[str, Any]:
    """
    Update risk scores for customers in batch

    Args:
        organization_id: Organization ID
        limit: Maximum number of customers to update

    Returns:
        Update results
    """
    try:
        return asyncio.run(_batch_update_risk_scores_async(organization_id, limit))

    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={
                "error": str(exc),
                "organization_id": organization_id,
                "limit": limit,
            },
        )
        raise exc


async def _batch_update_risk_scores_async(
    organization_id: str, limit: int
) -> Dict[str, Any]:
    """Update risk scores in batch asynchronously"""
    async with get_async_db_context() as db:
        risk_service = CustomerRiskAssessmentService()

        result = await risk_service.batch_update_risk_scores(organization_id, db, limit)

        return result


@celery_app.task(bind=True)
def calculate_kpis(self, organization_id: str) -> Dict[str, Any]:
    """
    Calculate key performance indicators

    Args:
        organization_id: Organization ID

    Returns:
        KPI data
    """
    try:
        return asyncio.run(_calculate_kpis_async(organization_id))

    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(exc), "organization_id": organization_id},
        )
        raise exc


async def _calculate_kpis_async(organization_id: str) -> Dict[str, Any]:
    """Calculate KPIs asynchronously"""
    async with get_async_db_context() as db:
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # KPI 1: Average Rating
        avg_rating_result = await db.execute(
            select(func.avg(Review.rating))
            .join(Customer)
            .where(
                and_(
                    Customer.organization_id == organization_id,
                    Review.created_at >= thirty_days_ago,
                )
            )
        )
        avg_rating = float(avg_rating_result.scalar() or 0)

        # KPI 2: Monthly Review Count
        monthly_reviews_result = await db.execute(
            select(func.count(Review.id))
            .join(Customer)
            .where(
                and_(
                    Customer.organization_id == organization_id,
                    Review.created_at >= thirty_days_ago,
                )
            )
        )
        monthly_reviews = monthly_reviews_result.scalar() or 0

        # KPI 3: At-Risk Customer Count
        at_risk_result = await db.execute(
            select(func.count(Customer.id)).where(
                and_(
                    Customer.organization_id == organization_id,
                    or_(
                        Customer.churn_risk_score >= 0.6,
                        Customer.bad_review_likelihood >= 0.6,
                    ),
                )
            )
        )
        at_risk_count = at_risk_result.scalar() or 0

        # KPI 4: Recovery Success Rate
        recovery_success_result = await db.execute(
            select(
                func.count(RecoveryAction.id)
                .filter(RecoveryAction.customer_responded == True)
                .label("responded"),
                func.count(RecoveryAction.id).label("total"),
            )
            .join(Customer)
            .where(
                and_(
                    Customer.organization_id == organization_id,
                    RecoveryAction.created_at >= thirty_days_ago,
                    RecoveryAction.executed_at.isnot(None),
                )
            )
        )
        recovery_data = recovery_success_result.first()
        recovery_success_rate = (
            (recovery_data.responded / max(recovery_data.total, 1))
            if recovery_data.total
            else 0
        )

        return {
            "organization_id": organization_id,
            "calculation_timestamp": now.isoformat(),
            "period_days": 30,
            "kpis": {
                "average_rating": round(avg_rating, 2),
                "monthly_review_count": monthly_reviews,
                "at_risk_customer_count": at_risk_count,
                "recovery_success_rate": round(recovery_success_rate, 3),
            },
        }


@celery_app.task(bind=True)
def generate_analytics_report(
    self, organization_id: str, report_type: str = "monthly"
) -> Dict[str, Any]:
    """
    Generate comprehensive analytics report

    Args:
        organization_id: Organization ID
        report_type: Type of report (daily, weekly, monthly)

    Returns:
        Analytics report data
    """
    try:
        return asyncio.run(
            _generate_analytics_report_async(organization_id, report_type)
        )

    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={
                "error": str(exc),
                "organization_id": organization_id,
                "report_type": report_type,
            },
        )
        raise exc


async def _generate_analytics_report_async(
    organization_id: str, report_type: str
) -> Dict[str, Any]:
    """Generate analytics report asynchronously"""
    # Determine date range based on report type
    now = datetime.now(timezone.utc)
    if report_type == "daily":
        start_date = now - timedelta(days=1)
    elif report_type == "weekly":
        start_date = now - timedelta(days=7)
    else:  # monthly
        start_date = now - timedelta(days=30)

    # Get aggregated metrics
    metrics = await _aggregate_metrics_async(organization_id)

    # Get KPIs
    kpis = await _calculate_kpis_async(organization_id)

    return {
        "report_type": report_type,
        "organization_id": organization_id,
        "report_period": {
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat(),
            "days": (now - start_date).days,
        },
        "generated_at": now.isoformat(),
        "metrics": metrics,
        "kpis": kpis["kpis"],
        "summary": {
            "total_reviews": metrics["review_metrics"]["total_reviews"],
            "average_rating": metrics["review_metrics"]["average_rating"],
            "at_risk_customers": metrics["customer_metrics"]["at_risk_customers"],
            "recovery_success_rate": metrics["recovery_metrics"]["success_rate"],
        },
    }


@celery_app.task(bind=True)
def cleanup_old_metrics(self, days_old: int = 90) -> Dict[str, Any]:
    """
    Clean up old metrics data

    Args:
        days_old: Number of days after which to clean up metrics

    Returns:
        Cleanup results
    """
    try:
        # In a real implementation, this would clean up metrics tables
        # For now, we'll just return a success message
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        return {
            "cleaned_up_before": cutoff_date.isoformat(),
            "days_old": days_old,
            "status": "completed",
            "note": "Metrics cleanup would be implemented with actual metrics storage",
        }

    except Exception as exc:
        current_task.update_state(
            state="FAILURE", meta={"error": str(exc), "days_old": days_old}
        )
        raise exc
