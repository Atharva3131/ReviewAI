"""
Recovery Action Recommendation Engine

This service recommends appropriate recovery actions based on customer risk assessment,
interaction history, and business rules. It prioritizes actions and schedules them
for optimal customer recovery outcomes.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.review import Review
from app.models.support_ticket import SupportTicket
from app.models.recovery_action import RecoveryAction, ActionType, ActionPriority
from app.services.customer_risk_service import CustomerRiskAssessmentService


class RecoveryRecommendationEngine:
    """Engine for recommending recovery actions based on customer risk and context"""
    
    def __init__(self):
        self.risk_service = CustomerRiskAssessmentService()
        
        # Action effectiveness scores (can be made configurable)
        self.action_effectiveness = {
            ActionType.EMAIL: 0.6,
            ActionType.SMS: 0.7,
            ActionType.PHONE_CALL: 0.8,
            ActionType.DISCOUNT_OFFER: 0.9,
            ActionType.REFUND: 0.95,
            ActionType.ESCALATE_TO_MANAGER: 0.85,
            ActionType.FOLLOW_UP: 0.5,
            ActionType.SURVEY: 0.4,
            ActionType.CALLBACK_REQUEST: 0.75,
            ActionType.PERSONALIZED_MESSAGE: 0.65
        }
        
        # Action costs (relative scale 1-10)
        self.action_costs = {
            ActionType.EMAIL: 1,
            ActionType.SMS: 2,
            ActionType.PHONE_CALL: 8,
            ActionType.DISCOUNT_OFFER: 6,
            ActionType.REFUND: 10,
            ActionType.ESCALATE_TO_MANAGER: 7,
            ActionType.FOLLOW_UP: 3,
            ActionType.SURVEY: 1,
            ActionType.CALLBACK_REQUEST: 5,
            ActionType.PERSONALIZED_MESSAGE: 2
        }
    
    async def recommend_recovery_actions(
        self, 
        customer_id: str, 
        db: AsyncSession,
        trigger_context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Recommend recovery actions for a customer based on their risk profile
        
        Args:
            customer_id: Customer ID
            db: Database session
            trigger_context: Optional context about what triggered the recovery
                           (e.g., {'type': 'review', 'review_id': '...', 'rating': 1})
        
        Returns:
            List of recommended actions with priorities and scheduling
        """
        # Get customer with risk assessment
        customer = await self._get_customer_with_context(customer_id, db)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Get current risk scores
        risk_data = await self.risk_service.assess_customer_risk(customer_id, db)
        
        # Generate action recommendations
        recommendations = await self._generate_action_recommendations(
            customer, risk_data, trigger_context, db
        )
        
        # Prioritize and schedule actions
        prioritized_actions = self._prioritize_actions(recommendations, customer, risk_data)
        
        # Add scheduling information
        scheduled_actions = self._schedule_actions(prioritized_actions, customer)
        
        return scheduled_actions
    
    async def _get_customer_with_context(
        self, 
        customer_id: str, 
        db: AsyncSession
    ) -> Optional[Customer]:
        """Get customer with all relevant context data"""
        stmt = (
            select(Customer)
            .options(
                selectinload(Customer.reviews),
                selectinload(Customer.support_tickets),
                selectinload(Customer.recovery_actions)
            )
            .where(Customer.id == customer_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _generate_action_recommendations(
        self, 
        customer: Customer, 
        risk_data: Dict, 
        trigger_context: Optional[Dict],
        db: AsyncSession
    ) -> List[Dict]:
        """Generate initial action recommendations based on rules"""
        recommendations = []
        churn_risk = risk_data['churn_risk']
        review_risk = risk_data['bad_review_likelihood']
        
        # Rule 1: Critical churn risk (>0.8)
        if churn_risk >= 0.8:
            recommendations.extend(await self._get_critical_churn_actions(customer, trigger_context, db))
        
        # Rule 2: High churn risk (0.6-0.8)
        elif churn_risk >= 0.6:
            recommendations.extend(await self._get_high_churn_actions(customer, trigger_context, db))
        
        # Rule 3: High bad review risk (>0.7)
        if review_risk >= 0.7:
            recommendations.extend(await self._get_review_prevention_actions(customer, trigger_context, db))
        
        # Rule 4: Recent negative review trigger
        if trigger_context and trigger_context.get('type') == 'review':
            recommendations.extend(await self._get_review_response_actions(customer, trigger_context, db))
        
        # Rule 5: Support ticket trigger
        if trigger_context and trigger_context.get('type') == 'support_ticket':
            recommendations.extend(await self._get_support_recovery_actions(customer, trigger_context, db))
        
        # Rule 6: High-value customer special handling
        if customer.is_high_value:
            recommendations.extend(await self._get_high_value_actions(customer, trigger_context, db))
        
        # Rule 7: Long-term inactive customer
        if customer.days_since_last_interaction and customer.days_since_last_interaction > 90:
            recommendations.extend(await self._get_reactivation_actions(customer, trigger_context, db))
        
        return recommendations
    
    async def _get_critical_churn_actions(
        self, 
        customer: Customer, 
        trigger_context: Optional[Dict],
        db: AsyncSession
    ) -> List[Dict]:
        """Actions for customers at critical churn risk"""
        actions = []
        
        # Immediate manager escalation
        actions.append({
            'action_type': ActionType.ESCALATE_TO_MANAGER,
            'priority': ActionPriority.URGENT,
            'title': 'Critical Customer - Manager Intervention Required',
            'content': f'Customer {customer.display_name} is at critical churn risk. Immediate manager intervention required.',
            'metadata': {
                'churn_risk': customer.churn_risk_score,
                'customer_value': customer.lifetime_value,
                'trigger': trigger_context
            },
            'confidence': 0.95,
            'requires_approval': True
        })
        
        # Personal phone call
        if customer.phone:
            actions.append({
                'action_type': ActionType.PHONE_CALL,
                'priority': ActionPriority.URGENT,
                'title': 'Personal Recovery Call',
                'content': f'Schedule urgent personal call with {customer.display_name} to address concerns and prevent churn.',
                'metadata': {
                    'phone': customer.phone,
                    'preferred_time': 'business_hours',
                    'call_type': 'retention'
                },
                'confidence': 0.9,
                'requires_approval': True
            })
        
        # Significant discount offer (if high value customer)
        if customer.is_high_value:
            actions.append({
                'action_type': ActionType.DISCOUNT_OFFER,
                'priority': ActionPriority.HIGH,
                'title': 'Retention Discount Offer',
                'content': 'Exclusive 25% discount offer for valued customer to prevent churn.',
                'metadata': {
                    'discount_percentage': 25,
                    'valid_days': 7,
                    'min_order_value': 0
                },
                'confidence': 0.85,
                'requires_approval': True
            })
        
        return actions
    
    async def _get_high_churn_actions(
        self, 
        customer: Customer, 
        trigger_context: Optional[Dict],
        db: AsyncSession
    ) -> List[Dict]:
        """Actions for customers at high churn risk"""
        actions = []
        
        # Personalized email
        actions.append({
            'action_type': ActionType.PERSONALIZED_MESSAGE,
            'priority': ActionPriority.HIGH,
            'title': 'Personal Retention Message',
            'content': f'Personalized message to {customer.display_name} addressing their concerns and offering support.',
            'metadata': {
                'message_type': 'retention',
                'personalization_level': 'high'
            },
            'confidence': 0.75
        })
        
        # Callback request
        actions.append({
            'action_type': ActionType.CALLBACK_REQUEST,
            'priority': ActionPriority.MEDIUM,
            'title': 'Schedule Callback',
            'content': 'Offer to schedule a convenient callback to discuss any concerns.',
            'metadata': {
                'callback_type': 'retention',
                'urgency': 'high'
            },
            'confidence': 0.7
        })
        
        # Moderate discount (if appropriate)
        if customer.total_orders > 1:
            actions.append({
                'action_type': ActionType.DISCOUNT_OFFER,
                'priority': ActionPriority.MEDIUM,
                'title': 'Loyalty Discount',
                'content': '15% discount as a thank you for being a valued customer.',
                'metadata': {
                    'discount_percentage': 15,
                    'valid_days': 14,
                    'min_order_value': 50
                },
                'confidence': 0.65
            })
        
        return actions
    
    async def _get_review_prevention_actions(
        self, 
        customer: Customer, 
        trigger_context: Optional[Dict],
        db: AsyncSession
    ) -> List[Dict]:
        """Actions to prevent bad reviews"""
        actions = []
        
        # Proactive outreach
        actions.append({
            'action_type': ActionType.EMAIL,
            'priority': ActionPriority.HIGH,
            'title': 'Proactive Customer Check-in',
            'content': 'Proactive email to check on customer satisfaction and address any concerns.',
            'metadata': {
                'email_type': 'proactive_support',
                'tone': 'caring'
            },
            'confidence': 0.7
        })
        
        # Survey to understand issues
        actions.append({
            'action_type': ActionType.SURVEY,
            'priority': ActionPriority.MEDIUM,
            'title': 'Satisfaction Survey',
            'content': 'Send satisfaction survey to identify and address potential issues.',
            'metadata': {
                'survey_type': 'satisfaction',
                'questions': 5,
                'incentive': 'small_discount'
            },
            'confidence': 0.6
        })
        
        return actions
    
    async def _get_review_response_actions(
        self, 
        customer: Customer, 
        trigger_context: Dict,
        db: AsyncSession
    ) -> List[Dict]:
        """Actions triggered by a specific review"""
        actions = []
        rating = trigger_context.get('rating', 5)
        
        if rating <= 2:  # Negative review
            # Immediate apology and resolution offer
            actions.append({
                'action_type': ActionType.EMAIL,
                'priority': ActionPriority.URGENT,
                'title': 'Immediate Response to Negative Review',
                'content': 'Immediate apology and offer to resolve the issues mentioned in the review.',
                'metadata': {
                    'review_id': trigger_context.get('review_id'),
                    'response_type': 'apology_resolution',
                    'urgency': 'immediate'
                },
                'confidence': 0.9
            })
            
            # Refund offer if appropriate
            if customer.total_orders > 0:
                actions.append({
                    'action_type': ActionType.REFUND,
                    'priority': ActionPriority.HIGH,
                    'title': 'Refund Offer',
                    'content': 'Offer partial or full refund to resolve customer dissatisfaction.',
                    'metadata': {
                        'refund_type': 'goodwill',
                        'max_amount': customer.avg_order_value or 100
                    },
                    'confidence': 0.8,
                    'requires_approval': True
                })
        
        elif rating == 3:  # Neutral review
            # Follow-up to improve experience
            actions.append({
                'action_type': ActionType.FOLLOW_UP,
                'priority': ActionPriority.MEDIUM,
                'title': 'Follow-up on Neutral Review',
                'content': 'Follow up to understand how we can improve the customer experience.',
                'metadata': {
                    'review_id': trigger_context.get('review_id'),
                    'follow_up_type': 'improvement'
                },
                'confidence': 0.6
            })
        
        return actions
    
    async def _get_support_recovery_actions(
        self, 
        customer: Customer, 
        trigger_context: Dict,
        db: AsyncSession
    ) -> List[Dict]:
        """Actions triggered by support tickets"""
        actions = []
        
        # Follow-up after ticket resolution
        actions.append({
            'action_type': ActionType.FOLLOW_UP,
            'priority': ActionPriority.MEDIUM,
            'title': 'Post-Resolution Follow-up',
            'content': 'Follow up to ensure the support issue was resolved satisfactorily.',
            'metadata': {
                'ticket_id': trigger_context.get('ticket_id'),
                'follow_up_type': 'resolution_confirmation'
            },
            'confidence': 0.7
        })
        
        return actions
    
    async def _get_high_value_actions(
        self, 
        customer: Customer, 
        trigger_context: Optional[Dict],
        db: AsyncSession
    ) -> List[Dict]:
        """Special actions for high-value customers"""
        actions = []
        
        # VIP treatment
        actions.append({
            'action_type': ActionType.PERSONALIZED_MESSAGE,
            'priority': ActionPriority.HIGH,
            'title': 'VIP Customer Care',
            'content': 'Personalized VIP message acknowledging their value and offering premium support.',
            'metadata': {
                'customer_tier': 'vip',
                'message_type': 'appreciation',
                'special_offers': True
            },
            'confidence': 0.8
        })
        
        return actions
    
    async def _get_reactivation_actions(
        self, 
        customer: Customer, 
        trigger_context: Optional[Dict],
        db: AsyncSession
    ) -> List[Dict]:
        """Actions for reactivating inactive customers"""
        actions = []
        
        # Win-back campaign
        actions.append({
            'action_type': ActionType.EMAIL,
            'priority': ActionPriority.MEDIUM,
            'title': 'Win-Back Campaign',
            'content': 'We miss you! Special offer to welcome you back.',
            'metadata': {
                'campaign_type': 'win_back',
                'special_offer': True
            },
            'confidence': 0.6
        })
        
        # Reactivation discount
        actions.append({
            'action_type': ActionType.DISCOUNT_OFFER,
            'priority': ActionPriority.MEDIUM,
            'title': 'Welcome Back Discount',
            'content': '20% welcome back discount for returning customers.',
            'metadata': {
                'discount_percentage': 20,
                'valid_days': 30,
                'campaign': 'reactivation'
            },
            'confidence': 0.65
        })
        
        return actions
    
    def _prioritize_actions(
        self, 
        recommendations: List[Dict], 
        customer: Customer, 
        risk_data: Dict
    ) -> List[Dict]:
        """Prioritize actions based on effectiveness, cost, and customer context"""
        for action in recommendations:
            # Calculate priority score
            effectiveness = self.action_effectiveness.get(action['action_type'], 0.5)
            cost = self.action_costs.get(action['action_type'], 5)
            confidence = action.get('confidence', 0.5)
            
            # Adjust for customer value
            value_multiplier = 1.5 if customer.is_high_value else 1.0
            
            # Adjust for risk level
            risk_multiplier = 1.0 + max(risk_data['churn_risk'], risk_data['bad_review_likelihood'])
            
            # Calculate final priority score (higher is better)
            priority_score = (effectiveness * confidence * value_multiplier * risk_multiplier) / (cost / 10)
            
            action['priority_score'] = priority_score
            action['estimated_effectiveness'] = effectiveness
            action['estimated_cost'] = cost
        
        # Sort by priority score (highest first)
        return sorted(recommendations, key=lambda x: x['priority_score'], reverse=True)
    
    def _schedule_actions(
        self, 
        prioritized_actions: List[Dict], 
        customer: Customer
    ) -> List[Dict]:
        """Add scheduling information to actions"""
        now = datetime.now(timezone.utc)
        
        for i, action in enumerate(prioritized_actions):
            # Schedule based on priority and action type
            if action['priority'] == ActionPriority.URGENT:
                # Execute immediately
                action['scheduled_at'] = now
            elif action['priority'] == ActionPriority.HIGH:
                # Execute within 1 hour
                action['scheduled_at'] = now + timedelta(hours=1)
            elif action['priority'] == ActionPriority.MEDIUM:
                # Execute within 4 hours, staggered
                action['scheduled_at'] = now + timedelta(hours=4 + i)
            else:
                # Execute within 24 hours, staggered
                action['scheduled_at'] = now + timedelta(hours=24 + i * 2)
            
            # Adjust for customer timezone if available
            if customer.timezone:
                # In a real implementation, you'd adjust for customer timezone
                # For now, we'll just add a note
                action['customer_timezone'] = customer.timezone
            
            # Set expiration (actions expire after a reasonable time)
            if action['action_type'] in [ActionType.DISCOUNT_OFFER, ActionType.REFUND]:
                action['expires_at'] = action['scheduled_at'] + timedelta(days=7)
            else:
                action['expires_at'] = action['scheduled_at'] + timedelta(days=3)
        
        return prioritized_actions
    
    async def create_recovery_actions(
        self, 
        customer_id: str, 
        recommendations: List[Dict], 
        db: AsyncSession,
        trigger_context: Optional[Dict] = None
    ) -> List[RecoveryAction]:
        """Create RecoveryAction records from recommendations"""
        customer = await db.get(Customer, customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        created_actions = []
        
        for rec in recommendations:
            action = RecoveryAction(
                organization_id=customer.organization_id,
                customer_id=customer.id,
                review_id=trigger_context.get('review_id') if trigger_context else None,
                ticket_id=trigger_context.get('ticket_id') if trigger_context else None,
                action_type=rec['action_type'],
                priority=rec['priority'],
                title=rec['title'],
                content=rec['content'],
                metadata=rec.get('metadata', {}),
                scheduled_at=rec.get('scheduled_at'),
                expires_at=rec.get('expires_at'),
                confidence_score=rec.get('confidence', 0.5),
                trigger_reason=f"Risk assessment: churn={rec.get('churn_risk', 'unknown')}, review_risk={rec.get('review_risk', 'unknown')}",
                requires_approval=rec.get('requires_approval', False)
            )
            
            db.add(action)
            created_actions.append(action)
        
        await db.commit()
        
        # Refresh to get IDs
        for action in created_actions:
            await db.refresh(action)
        
        return created_actions
    
    async def get_pending_actions(
        self, 
        organization_id: str, 
        db: AsyncSession,
        limit: int = 100
    ) -> List[RecoveryAction]:
        """Get pending recovery actions for an organization"""
        stmt = (
            select(RecoveryAction)
            .options(selectinload(RecoveryAction.customer))
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.status.in_(['pending', 'scheduled']),
                    or_(
                        RecoveryAction.expires_at.is_(None),
                        RecoveryAction.expires_at > datetime.now(timezone.utc)
                    )
                )
            )
            .order_by(
                RecoveryAction.priority.desc(),
                RecoveryAction.scheduled_at.asc()
            )
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_overdue_actions(
        self, 
        organization_id: str, 
        db: AsyncSession
    ) -> List[RecoveryAction]:
        """Get overdue recovery actions"""
        now = datetime.now(timezone.utc)
        
        stmt = (
            select(RecoveryAction)
            .options(selectinload(RecoveryAction.customer))
            .where(
                and_(
                    RecoveryAction.organization_id == organization_id,
                    RecoveryAction.status.in_(['pending', 'scheduled']),
                    RecoveryAction.scheduled_at < now,
                    or_(
                        RecoveryAction.expires_at.is_(None),
                        RecoveryAction.expires_at > now
                    )
                )
            )
            .order_by(RecoveryAction.scheduled_at.asc())
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()
