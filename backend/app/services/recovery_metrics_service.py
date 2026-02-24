"""
Recovery Success Tracking and Metrics Service

This service tracks the effectiveness of recovery actions and provides
metrics for analyzing recovery success rates and ROI.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.recovery_action import RecoveryAction, ActionType, ActionStatus
from app.models.review import Review
from app.models.support_ticket import SupportTicket


class RecoveryMetricsService:
    """Service for tracking recovery action effectiveness and metrics"""
    
    def __init__(self):
        # Metric calculation periods
        self.periods = {
            'daily': timedelta(days=1),
            'weekly': timedelta(days=7),
            'monthly': timedelta(days=30),
            'quarterly': timedelta(days=90)
        }
    
    async def get_recovery_success_metrics(
        self, 
        organization_id: str, 
        db: AsyncSession,
        period: str = 'monthly'
    ) -> Dict[str, Any]:
        """Get comprehensive recovery success metrics"""
        if period not in self.periods:
            raise ValueError(f"Invalid period: {period}")
        
        start_date = datetime.now(timezone.utc) - self.periods[period]
        
        # Get basic recovery action metrics
        action_metrics = await self._get_action_metrics(organization_id, db, start_date)
        
        # Get customer outcome metrics
        customer_metrics = await self._get_customer_outcome_metrics(organization_id, db, start_date)
        
        # Get ROI metrics
        roi_metrics = await self._get_roi_metrics(organization_id, db, start_date)
        
        # Get action type effectiveness
        effectiveness_metrics = await self._get_action_effectiveness_metrics(organization_id, db, start_date)
        
        return {
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': datetime.now(timezone.utc).isoformat(),
            'action_metrics': action_metrics,
            'customer_metrics': customer_metrics,
            'roi_metrics': roi_metrics,
            'effectiveness_by_type': effectiveness_metrics
        }
    
    async def _get_action_metrics(
        self, 
        organization_id: str, 
        db: AsyncSession, 
        start_date: datetime
    ) -> Dict[str, Any]:
        """Get basic recovery action metrics"""
        # Total actions created
        total_actions = await db.execute(
            select(func.count(RecoveryAction.id))
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date
                )
            )
        )
        total_count = total_actions.scalar() or 0
        
        # Actions by status
        status_counts = await db.execute(
            select(
                RecoveryAction.status,
                func.count(RecoveryAction.id)
            )
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date
                )
            )
            .group_by(RecoveryAction.status)
        )
        
        status_breakdown = {row[0].value: row[1] for row in status_counts.fetchall()}
        
        # Success rate (completed + responded / total executed)
        executed_count = sum(
            count for status, count in status_breakdown.items() 
            if status not in ['pending', 'scheduled', 'cancelled']
        )
        
        successful_count = sum(
            count for status, count in status_breakdown.items() 
            if status in ['completed', 'responded', 'delivered']
        )
        
        success_rate = (successful_count / executed_count) if executed_count > 0 else 0.0
        
        return {
            'total_actions': total_count,
            'executed_actions': executed_count,
            'successful_actions': successful_count,
            'success_rate': round(success_rate, 3),
            'status_breakdown': status_breakdown
        }
    
    async def _get_customer_outcome_metrics(
        self, 
        organization_id: str, 
        db: AsyncSession, 
        start_date: datetime
    ) -> Dict[str, Any]:
        """Get customer outcome metrics"""
        # Customers who had recovery actions
        customers_with_actions = await db.execute(
            select(func.count(func.distinct(RecoveryAction.customer_id)))
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date
                )
            )
        )
        customers_targeted = customers_with_actions.scalar() or 0
        
        # Customers who responded to recovery actions
        customers_responded = await db.execute(
            select(func.count(func.distinct(RecoveryAction.customer_id)))
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date,
                    RecoveryAction.customer_responded == True
                )
            )
        )
        responded_count = customers_responded.scalar() or 0
        
        # Customer response rate
        response_rate = (responded_count / customers_targeted) if customers_targeted > 0 else 0.0
        
        # Average outcome rating for responded customers
        avg_outcome = await db.execute(
            select(func.avg(RecoveryAction.outcome_rating))
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date,
                    RecoveryAction.outcome_rating.isnot(None)
                )
            )
        )
        avg_outcome_rating = float(avg_outcome.scalar() or 0.0)
        
        # Churn prevention (customers who were at risk but didn't churn)
        # This would require tracking customer status changes over time
        # For now, we'll estimate based on response rates
        estimated_churn_prevented = int(responded_count * 0.7)  # Estimate 70% of responders retained
        
        return {
            'customers_targeted': customers_targeted,
            'customers_responded': responded_count,
            'customer_response_rate': round(response_rate, 3),
            'average_outcome_rating': round(avg_outcome_rating, 3),
            'estimated_churn_prevented': estimated_churn_prevented
        }
    
    async def _get_roi_metrics(
        self, 
        organization_id: str, 
        db: AsyncSession, 
        start_date: datetime
    ) -> Dict[str, Any]:
        """Get ROI metrics for recovery actions"""
        # Estimated costs by action type (in dollars)
        action_costs = {
            ActionType.EMAIL: 0.10,
            ActionType.SMS: 0.25,
            ActionType.PHONE_CALL: 15.00,
            ActionType.DISCOUNT_OFFER: 25.00,  # Average discount value
            ActionType.REFUND: 50.00,  # Average refund
            ActionType.ESCALATE_TO_MANAGER: 30.00,  # Manager time
            ActionType.FOLLOW_UP: 5.00,
            ActionType.SURVEY: 0.50,
            ActionType.CALLBACK_REQUEST: 10.00,
            ActionType.PERSONALIZED_MESSAGE: 2.00
        }
        
        # Get action counts by type
        action_type_counts = await db.execute(
            select(
                RecoveryAction.action_type,
                func.count(RecoveryAction.id)
            )
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date
                )
            )
            .group_by(RecoveryAction.action_type)
        )
        
        total_cost = 0.0
        cost_breakdown = {}
        
        for action_type, count in action_type_counts.fetchall():
            cost_per_action = action_costs.get(action_type, 5.00)  # Default cost
            type_cost = cost_per_action * count
            total_cost += type_cost
            cost_breakdown[action_type.value] = {
                'count': count,
                'cost_per_action': cost_per_action,
                'total_cost': type_cost
            }
        
        # Estimated revenue retained (customers who responded * average customer value)
        # Get average customer lifetime value
        avg_customer_value = await db.execute(
            select(func.avg(Customer.lifetime_value))
            .where(
                and_(
                    Customer.organization_id == organization_id,
                    Customer.lifetime_value.isnot(None)
                )
            )
        )
        avg_ltv = float(avg_customer_value.scalar() or 500.0)  # Default $500 if no data
        
        # Customers who responded (proxy for retention)
        customers_retained = await db.execute(
            select(func.count(func.distinct(RecoveryAction.customer_id)))
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date,
                    RecoveryAction.customer_responded == True
                )
            )
        )
        retained_count = customers_retained.scalar() or 0
        
        estimated_revenue_retained = retained_count * avg_ltv * 0.5  # Assume 50% of LTV retained
        
        # Calculate ROI
        roi = ((estimated_revenue_retained - total_cost) / total_cost) if total_cost > 0 else 0.0
        
        return {
            'total_cost': round(total_cost, 2),
            'cost_breakdown': cost_breakdown,
            'estimated_revenue_retained': round(estimated_revenue_retained, 2),
            'customers_retained': retained_count,
            'average_customer_ltv': round(avg_ltv, 2),
            'roi': round(roi, 2),
            'roi_percentage': round(roi * 100, 1)
        }
    
    async def _get_action_effectiveness_metrics(
        self, 
        organization_id: str, 
        db: AsyncSession, 
        start_date: datetime
    ) -> Dict[str, Any]:
        """Get effectiveness metrics by action type"""
        # Get success rates by action type
        effectiveness_query = await db.execute(
            select(
                RecoveryAction.action_type,
                func.count(RecoveryAction.id).label('total'),
                func.sum(
                    case(
                        (RecoveryAction.customer_responded == True, 1),
                        else_=0
                    )
                ).label('responded'),
                func.avg(RecoveryAction.outcome_rating).label('avg_rating'),
                func.avg(RecoveryAction.confidence_score).label('avg_confidence')
            )
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date,
                    RecoveryAction.status.notin_(['pending', 'scheduled', 'cancelled'])
                )
            )
            .group_by(RecoveryAction.action_type)
        )
        
        effectiveness_by_type = {}
        
        for row in effectiveness_query.fetchall():
            action_type = row.action_type.value
            total = row.total or 0
            responded = row.responded or 0
            avg_rating = float(row.avg_rating or 0.0)
            avg_confidence = float(row.avg_confidence or 0.0)
            
            response_rate = (responded / total) if total > 0 else 0.0
            
            effectiveness_by_type[action_type] = {
                'total_actions': total,
                'customer_responses': responded,
                'response_rate': round(response_rate, 3),
                'average_outcome_rating': round(avg_rating, 3),
                'average_confidence_score': round(avg_confidence, 3)
            }
        
        return effectiveness_by_type
    
    async def get_recovery_trends(
        self, 
        organization_id: str, 
        db: AsyncSession,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get recovery action trends over time"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Daily action counts
        daily_actions = await db.execute(
            select(
                func.date(RecoveryAction.created_at).label('date'),
                func.count(RecoveryAction.id).label('count'),
                func.sum(
                    case(
                        (RecoveryAction.customer_responded == True, 1),
                        else_=0
                    )
                ).label('responses')
            )
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.created_at >= start_date
                )
            )
            .group_by(func.date(RecoveryAction.created_at))
            .order_by(func.date(RecoveryAction.created_at))
        )
        
        trends = []
        for row in daily_actions.fetchall():
            date_str = row.date.isoformat()
            count = row.count or 0
            responses = row.responses or 0
            response_rate = (responses / count) if count > 0 else 0.0
            
            trends.append({
                'date': date_str,
                'actions_created': count,
                'customer_responses': responses,
                'response_rate': round(response_rate, 3)
            })
        
        return {
            'period_days': days,
            'start_date': start_date.isoformat(),
            'daily_trends': trends
        }
    
    async def get_customer_recovery_history(
        self, 
        customer_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get recovery history for a specific customer"""
        # Get all recovery actions for customer
        actions_query = await db.execute(
            select(RecoveryAction)
            .where(RecoveryAction.customer_id == customer_id)
            .order_by(RecoveryAction.created_at.desc())
        )
        
        actions = actions_query.scalars().all()
        
        # Calculate customer-specific metrics
        total_actions = len(actions)
        responded_actions = sum(1 for action in actions if action.customer_responded)
        response_rate = (responded_actions / total_actions) if total_actions > 0 else 0.0
        
        # Average outcome rating
        outcome_ratings = [
            float(action.outcome_rating) 
            for action in actions 
            if action.outcome_rating is not None
        ]
        avg_outcome = sum(outcome_ratings) / len(outcome_ratings) if outcome_ratings else 0.0
        
        # Most effective action type for this customer
        action_effectiveness = {}
        for action in actions:
            action_type = action.action_type.value
            if action_type not in action_effectiveness:
                action_effectiveness[action_type] = {'total': 0, 'responded': 0}
            
            action_effectiveness[action_type]['total'] += 1
            if action.customer_responded:
                action_effectiveness[action_type]['responded'] += 1
        
        # Find most effective action type
        best_action_type = None
        best_response_rate = 0.0
        
        for action_type, stats in action_effectiveness.items():
            if stats['total'] >= 2:  # Need at least 2 attempts to be meaningful
                rate = stats['responded'] / stats['total']
                if rate > best_response_rate:
                    best_response_rate = rate
                    best_action_type = action_type
        
        return {
            'customer_id': customer_id,
            'total_recovery_actions': total_actions,
            'customer_responses': responded_actions,
            'response_rate': round(response_rate, 3),
            'average_outcome_rating': round(avg_outcome, 3),
            'most_effective_action_type': best_action_type,
            'best_action_response_rate': round(best_response_rate, 3),
            'action_history': [action.to_dict() for action in actions],
            'effectiveness_by_type': {
                action_type: {
                    'total': stats['total'],
                    'responded': stats['responded'],
                    'response_rate': round(stats['responded'] / stats['total'], 3)
                }
                for action_type, stats in action_effectiveness.items()
            }
        }
