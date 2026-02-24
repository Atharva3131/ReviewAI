"""
Recovery Action Background Tasks

This module contains Celery tasks for executing customer recovery actions,
including email sending, SMS delivery, callback scheduling, and action tracking.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from celery import current_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery import celery_app
from app.core.database import get_async_db_context
from app.models.recovery_action import RecoveryAction, ActionStatus
from app.models.customer import Customer
from app.models.review import Review
from app.services.recovery_execution_service import RecoveryExecutionService
from app.services.recovery_recommendation_service import RecoveryRecommendationEngine
from app.services.agent_engine import AgentEngine


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def execute_recovery_action(self, action_id: str) -> Dict[str, Any]:
    """
    Execute a specific recovery action
    
    Args:
        action_id: Recovery action ID to execute
        
    Returns:
        Execution results
    """
    try:
        return asyncio.run(_execute_recovery_action_async(action_id))
        
    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={
                "error": str(exc),
                "action_id": action_id,
                "retry_count": self.request.retries
            }
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        
        # Send to dead letter queue after max retries
        celery_app.send_task(
            "app.tasks.monitoring_tasks.log_failed_task",
            args=[self.request.id, str(exc), f"Recovery action {action_id} execution failed"],
            queue="dead_letter"
        )
        
        raise exc


async def _execute_recovery_action_async(action_id: str) -> Dict[str, Any]:
    """Execute recovery action asynchronously"""
    async with get_async_db_context() as db:
        execution_service = RecoveryExecutionService()
        
        # Execute the action
        result = await execution_service.execute_action(action_id, db)
        
        # Schedule follow-up tasks if needed
        if result["success"]:
            # Schedule follow-up check in 24 hours
            celery_app.send_task(
                "app.tasks.recovery_tasks.check_action_effectiveness",
                args=[action_id],
                queue="recovery",
                countdown=86400  # 24 hours
            )
        
        return result


@celery_app.task(bind=True, max_retries=2)
def process_review_for_action(self, review_id: str) -> Dict[str, Any]:
    """
    Process a review to determine and create recovery actions
    
    Args:
        review_id: Review ID to process
        
    Returns:
        Processing results
    """
    try:
        return asyncio.run(_process_review_for_action_async(review_id))
        
    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={
                "error": str(exc),
                "review_id": review_id,
                "retry_count": self.request.retries
            }
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120)
        
        raise exc


async def _process_review_for_action_async(review_id: str) -> Dict[str, Any]:
    """Process review for recovery actions asynchronously"""
    async with get_async_db_context() as db:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        # Get review with customer data
        result = await db.execute(
            select(Review)
            .options(selectinload(Review.customer))
            .where(Review.id == review_id)
        )
        review = result.scalar_one_or_none()
        
        if not review:
            raise ValueError(f"Review {review_id} not found")
        
        # Use agent engine to decide on actions
        agent_engine = AgentEngine()
        decision = await agent_engine.make_decision({
            "type": "review",
            "review_id": review_id,
            "rating": review.rating,
            "sentiment_score": review.sentiment_score,
            "urgency_level": review.urgency_level,
            "categories": review.categories,
            "customer_id": str(review.customer_id)
        }, db)
        
        created_actions = []
        
        if decision["action"] in ["recover_private", "escalate"]:
            # Get recovery recommendations
            recommendation_engine = RecoveryRecommendationEngine()
            
            trigger_context = {
                "type": "review",
                "review_id": review_id,
                "rating": review.rating,
                "sentiment_score": review.sentiment_score
            }
            
            recommendations = await recommendation_engine.recommend_recovery_actions(
                str(review.customer_id),
                db,
                trigger_context
            )
            
            # Create recovery actions
            actions = await recommendation_engine.create_recovery_actions(
                str(review.customer_id),
                recommendations,
                db,
                trigger_context
            )
            
            created_actions = [str(action.id) for action in actions]
            
            # Schedule immediate execution for urgent actions
            for action in actions:
                if action.priority.value in ["urgent", "high"]:
                    celery_app.send_task(
                        "app.tasks.recovery_tasks.execute_recovery_action",
                        args=[str(action.id)],
                        queue="recovery",
                        countdown=60  # Execute in 1 minute
                    )
                else:
                    # Schedule for later execution
                    delay = 3600 if action.priority.value == "medium" else 7200  # 1-2 hours
                    celery_app.send_task(
                        "app.tasks.recovery_tasks.execute_recovery_action",
                        args=[str(action.id)],
                        queue="recovery",
                        countdown=delay
                    )
        
        return {
            "review_id": review_id,
            "decision": decision,
            "created_actions": created_actions,
            "status": "completed"
        }


@celery_app.task(bind=True)
def process_pending_actions(self) -> Dict[str, Any]:
    """
    Process all pending recovery actions that are ready for execution
    
    Returns:
        Processing results
    """
    try:
        return asyncio.run(_process_pending_actions_async())
        
    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(exc)}
        )
        raise exc


async def _process_pending_actions_async() -> Dict[str, Any]:
    """Process pending actions asynchronously"""
    async with get_async_db_context() as db:
        from sqlalchemy import select, and_, or_
        
        now = datetime.now(timezone.utc)
        
        # Get actions ready for execution
        result = await db.execute(
            select(RecoveryAction)
            .where(
                and_(
                    RecoveryAction.status.in_([ActionStatus.PENDING, ActionStatus.SCHEDULED]),
                    or_(
                        RecoveryAction.scheduled_at.is_(None),
                        RecoveryAction.scheduled_at <= now
                    ),
                    or_(
                        RecoveryAction.expires_at.is_(None),
                        RecoveryAction.expires_at > now
                    ),
                    or_(
                        RecoveryAction.requires_approval == False,
                        RecoveryAction.approved_at.isnot(None)
                    )
                )
            )
            .limit(20)  # Process in batches
        )
        
        pending_actions = result.scalars().all()
        
        scheduled_count = 0
        for action in pending_actions:
            try:
                # Schedule execution
                celery_app.send_task(
                    "app.tasks.recovery_tasks.execute_recovery_action",
                    args=[str(action.id)],
                    queue="recovery"
                )
                scheduled_count += 1
                
            except Exception as e:
                print(f"Failed to schedule action {action.id}: {e}")
        
        return {
            "total_pending": len(pending_actions),
            "scheduled_count": scheduled_count,
            "status": "completed"
        }


@celery_app.task(bind=True)
def check_action_effectiveness(self, action_id: str) -> Dict[str, Any]:
    """
    Check the effectiveness of a recovery action after execution
    
    Args:
        action_id: Recovery action ID to check
        
    Returns:
        Effectiveness check results
    """
    try:
        return asyncio.run(_check_action_effectiveness_async(action_id))
        
    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={
                "error": str(exc),
                "action_id": action_id
            }
        )
        raise exc


async def _check_action_effectiveness_async(action_id: str) -> Dict[str, Any]:
    """Check action effectiveness asynchronously"""
    async with get_async_db_context() as db:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        # Get action with customer data
        result = await db.execute(
            select(RecoveryAction)
            .options(selectinload(RecoveryAction.customer))
            .where(RecoveryAction.id == action_id)
        )
        action = result.scalar_one_or_none()
        
        if not action:
            return {"error": f"Action {action_id} not found"}
        
        # Check for customer response indicators
        customer_responded = False
        response_indicators = []
        
        # Check if customer left a new review
        recent_reviews = await db.execute(
            select(Review)
            .where(
                and_(
                    Review.customer_id == action.customer_id,
                    Review.created_at > action.executed_at
                )
            )
        )
        
        new_reviews = recent_reviews.scalars().all()
        if new_reviews:
            avg_rating = sum(r.rating for r in new_reviews) / len(new_reviews)
            if avg_rating > 3:
                customer_responded = True
                response_indicators.append(f"Positive review (avg rating: {avg_rating:.1f})")
        
        # Check if customer contacted support
        # (This would require integration with support ticket system)
        
        # Update action with effectiveness data
        if customer_responded:
            action.mark_customer_response(outcome_rating=0.8)  # Good outcome
        
        # Calculate effectiveness score
        effectiveness_score = 0.5  # Base score
        
        if customer_responded:
            effectiveness_score += 0.3
        
        if action.customer_responded:
            effectiveness_score += 0.2
        
        action.outcome_rating = min(effectiveness_score, 1.0)
        
        await db.commit()
        
        return {
            "action_id": action_id,
            "customer_responded": customer_responded,
            "response_indicators": response_indicators,
            "effectiveness_score": effectiveness_score,
            "status": "completed"
        }


@celery_app.task(bind=True)
def batch_execute_actions(self, action_ids: List[str]) -> Dict[str, Any]:
    """
    Execute multiple recovery actions in batch
    
    Args:
        action_ids: List of action IDs to execute
        
    Returns:
        Batch execution results
    """
    results = {
        "total": len(action_ids),
        "scheduled": 0,
        "failed": 0,
        "results": []
    }
    
    for action_id in action_ids:
        try:
            # Schedule individual action execution
            task = celery_app.send_task(
                "app.tasks.recovery_tasks.execute_recovery_action",
                args=[action_id],
                queue="recovery"
            )
            
            results["results"].append({
                "action_id": action_id,
                "task_id": task.id,
                "status": "scheduled"
            })
            results["scheduled"] += 1
            
        except Exception as e:
            results["results"].append({
                "action_id": action_id,
                "status": "failed",
                "error": str(e)
            })
            results["failed"] += 1
    
    return results


@celery_app.task(bind=True)
def cleanup_expired_actions(self) -> Dict[str, Any]:
    """
    Clean up expired recovery actions
    
    Returns:
        Cleanup results
    """
    try:
        return asyncio.run(_cleanup_expired_actions_async())
        
    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(exc)}
        )
        raise exc


async def _cleanup_expired_actions_async() -> Dict[str, Any]:
    """Clean up expired actions asynchronously"""
    async with get_async_db_context() as db:
        from sqlalchemy import select, update
        
        now = datetime.now(timezone.utc)
        
        # Find expired actions
        result = await db.execute(
            select(RecoveryAction)
            .where(
                and_(
                    RecoveryAction.expires_at < now,
                    RecoveryAction.status.in_([ActionStatus.PENDING, ActionStatus.SCHEDULED])
                )
            )
        )
        
        expired_actions = result.scalars().all()
        
        # Mark as cancelled
        for action in expired_actions:
            action.cancel("Action expired")
        
        await db.commit()
        
        return {
            "expired_count": len(expired_actions),
            "cleanup_date": now.isoformat(),
            "status": "completed"
        }


@celery_app.task(bind=True)
def generate_recovery_report(self, organization_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Generate a recovery effectiveness report
    
    Args:
        organization_id: Organization ID
        days: Number of days to include in report
        
    Returns:
        Recovery report data
    """
    try:
        return asyncio.run(_generate_recovery_report_async(organization_id, days))
        
    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={
                "error": str(exc),
                "organization_id": organization_id,
                "days": days
            }
        )
        raise exc


async def _generate_recovery_report_async(organization_id: str, days: int) -> Dict[str, Any]:
    """Generate recovery report asynchronously"""
    async with get_async_db_context() as db:
        from sqlalchemy import select, func
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get recovery action statistics
        result = await db.execute(
            select(
                func.count(RecoveryAction.id).label("total_actions"),
                func.count(RecoveryAction.id).filter(RecoveryAction.success == True).label("successful_actions"),
                func.count(RecoveryAction.id).filter(RecoveryAction.customer_responded == True).label("customer_responses"),
                func.avg(RecoveryAction.outcome_rating).label("avg_effectiveness")
            )
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date
                )
            )
        )
        
        stats = result.first()
        
        # Calculate rates
        total_actions = stats.total_actions or 0
        success_rate = (stats.successful_actions / total_actions) if total_actions > 0 else 0
        response_rate = (stats.customer_responses / total_actions) if total_actions > 0 else 0
        avg_effectiveness = float(stats.avg_effectiveness or 0)
        
        return {
            "organization_id": organization_id,
            "report_period_days": days,
            "total_actions": total_actions,
            "successful_actions": stats.successful_actions or 0,
            "customer_responses": stats.customer_responses or 0,
            "success_rate": round(success_rate, 3),
            "response_rate": round(response_rate, 3),
            "avg_effectiveness": round(avg_effectiveness, 3),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed"
        }
