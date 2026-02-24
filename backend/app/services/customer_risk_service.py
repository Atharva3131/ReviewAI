"""
Customer Risk Assessment Service

This service implements algorithms to assess customer churn risk and bad review likelihood
based on various factors including interaction history, sentiment patterns, and behavioral data.
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
from app.models.recovery_action import RecoveryAction


class CustomerRiskAssessmentService:
    """Service for assessing customer churn risk and bad review likelihood"""
    
    def __init__(self):
        # Risk factor weights (can be made configurable)
        self.churn_weights = {
            'recency': 0.25,      # How recently they interacted
            'frequency': 0.20,    # How often they interact
            'sentiment': 0.25,    # Average sentiment of interactions
            'support_load': 0.15, # Number of support tickets
            'escalations': 0.15   # Number of escalated issues
        }
        
        self.review_weights = {
            'recent_sentiment': 0.30,  # Recent sentiment trend
            'support_tickets': 0.25,   # Active support issues
            'escalation_history': 0.20, # Past escalations
            'response_time': 0.15,     # How quickly we respond
            'resolution_rate': 0.10    # How often we resolve issues
        }
    
    async def assess_customer_risk(
        self, 
        customer_id: str, 
        db: AsyncSession
    ) -> Dict[str, float]:
        """
        Assess both churn risk and bad review likelihood for a customer
        
        Returns:
            Dict with 'churn_risk' and 'bad_review_likelihood' scores (0.0-1.0)
        """
        # Get customer with related data
        customer = await self._get_customer_with_data(customer_id, db)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Calculate churn risk
        churn_risk = await self._calculate_churn_risk(customer, db)
        
        # Calculate bad review likelihood
        review_risk = await self._calculate_bad_review_likelihood(customer, db)
        
        return {
            'churn_risk': churn_risk,
            'bad_review_likelihood': review_risk,
            'risk_factors': await self._get_risk_factors(customer, db)
        }
    
    async def _get_customer_with_data(
        self, 
        customer_id: str, 
        db: AsyncSession
    ) -> Optional[Customer]:
        """Get customer with all related data loaded"""
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
    
    async def _calculate_churn_risk(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> float:
        """Calculate churn risk score based on multiple factors"""
        factors = {}
        
        # Factor 1: Recency (how long since last interaction)
        factors['recency'] = self._calculate_recency_risk(customer)
        
        # Factor 2: Frequency (interaction frequency decline)
        factors['frequency'] = await self._calculate_frequency_risk(customer, db)
        
        # Factor 3: Sentiment (declining sentiment trend)
        factors['sentiment'] = await self._calculate_sentiment_risk(customer, db)
        
        # Factor 4: Support load (high number of tickets)
        factors['support_load'] = await self._calculate_support_load_risk(customer, db)
        
        # Factor 5: Escalations (unresolved escalated issues)
        factors['escalations'] = await self._calculate_escalation_risk(customer, db)
        
        # Calculate weighted score
        churn_risk = sum(
            factors[factor] * self.churn_weights[factor] 
            for factor in factors
        )
        
        return min(max(churn_risk, 0.0), 1.0)  # Clamp to 0-1
    
    async def _calculate_bad_review_likelihood(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> float:
        """Calculate likelihood of customer leaving a bad review"""
        factors = {}
        
        # Factor 1: Recent sentiment trend
        factors['recent_sentiment'] = await self._calculate_recent_sentiment_risk(customer, db)
        
        # Factor 2: Active support tickets
        factors['support_tickets'] = await self._calculate_active_support_risk(customer, db)
        
        # Factor 3: Escalation history
        factors['escalation_history'] = await self._calculate_escalation_history_risk(customer, db)
        
        # Factor 4: Response time satisfaction
        factors['response_time'] = await self._calculate_response_time_risk(customer, db)
        
        # Factor 5: Resolution rate
        factors['resolution_rate'] = await self._calculate_resolution_rate_risk(customer, db)
        
        # Calculate weighted score
        review_risk = sum(
            factors[factor] * self.review_weights[factor] 
            for factor in factors
        )
        
        return min(max(review_risk, 0.0), 1.0)  # Clamp to 0-1
    
    def _calculate_recency_risk(self, customer: Customer) -> float:
        """Calculate risk based on time since last interaction"""
        if not customer.last_interaction:
            return 0.8  # High risk if never interacted
        
        days_since = customer.days_since_last_interaction or 0
        
        if days_since <= 7:
            return 0.1  # Very recent interaction
        elif days_since <= 30:
            return 0.3  # Recent interaction
        elif days_since <= 90:
            return 0.6  # Moderate gap
        else:
            return 0.9  # Long gap, high risk
    
    async def _calculate_frequency_risk(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> float:
        """Calculate risk based on interaction frequency decline"""
        # Get interaction counts for last 3 months vs previous 3 months
        now = datetime.now(timezone.utc)
        three_months_ago = now - timedelta(days=90)
        six_months_ago = now - timedelta(days=180)
        
        # Count recent interactions (reviews + tickets)
        recent_reviews = await db.execute(
            select(func.count(Review.id))
            .where(
                and_(
                    Review.customer_id == customer.id,
                    Review.created_at >= three_months_ago
                )
            )
        )
        recent_reviews_count = recent_reviews.scalar() or 0
        
        recent_tickets = await db.execute(
            select(func.count(SupportTicket.id))
            .where(
                and_(
                    SupportTicket.customer_id == customer.id,
                    SupportTicket.created_at >= three_months_ago
                )
            )
        )
        recent_tickets_count = recent_tickets.scalar() or 0
        
        # Count previous interactions
        previous_reviews = await db.execute(
            select(func.count(Review.id))
            .where(
                and_(
                    Review.customer_id == customer.id,
                    Review.created_at >= six_months_ago,
                    Review.created_at < three_months_ago
                )
            )
        )
        previous_reviews_count = previous_reviews.scalar() or 0
        
        previous_tickets = await db.execute(
            select(func.count(SupportTicket.id))
            .where(
                and_(
                    SupportTicket.customer_id == customer.id,
                    SupportTicket.created_at >= six_months_ago,
                    SupportTicket.created_at < three_months_ago
                )
            )
        )
        previous_tickets_count = previous_tickets.scalar() or 0
        
        recent_total = recent_reviews_count + recent_tickets_count
        previous_total = previous_reviews_count + previous_tickets_count
        
        if previous_total == 0:
            return 0.3 if recent_total > 0 else 0.7  # New customer or inactive
        
        # Calculate decline ratio
        decline_ratio = (previous_total - recent_total) / previous_total
        
        if decline_ratio <= 0:
            return 0.2  # Increasing or stable activity
        elif decline_ratio <= 0.3:
            return 0.4  # Slight decline
        elif decline_ratio <= 0.6:
            return 0.7  # Moderate decline
        else:
            return 0.9  # Significant decline
    
    async def _calculate_sentiment_risk(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> float:
        """Calculate risk based on sentiment trend"""
        # Get recent reviews with sentiment scores
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        recent_reviews = await db.execute(
            select(Review.sentiment_score)
            .where(
                and_(
                    Review.customer_id == customer.id,
                    Review.created_at >= thirty_days_ago,
                    Review.sentiment_score.isnot(None)
                )
            )
            .order_by(Review.created_at.desc())
        )
        
        sentiment_scores = [row[0] for row in recent_reviews.fetchall()]
        
        if not sentiment_scores:
            # Use customer's average rating if available
            if customer.avg_rating_given:
                avg_rating = float(customer.avg_rating_given)
                # Convert rating (1-5) to sentiment risk (higher rating = lower risk)
                return max(0.0, (3.0 - avg_rating) / 2.0)
            return 0.5  # Neutral if no data
        
        avg_sentiment = sum(float(score) for score in sentiment_scores) / len(sentiment_scores)
        
        # Convert sentiment score to risk (lower sentiment = higher risk)
        return max(0.0, 1.0 - avg_sentiment)
    
    async def _calculate_support_load_risk(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> float:
        """Calculate risk based on support ticket volume"""
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Count recent tickets
        recent_tickets = await db.execute(
            select(func.count(SupportTicket.id))
            .where(
                and_(
                    SupportTicket.customer_id == customer.id,
                    SupportTicket.created_at >= thirty_days_ago
                )
            )
        )
        ticket_count = recent_tickets.scalar() or 0
        
        # Risk based on ticket volume
        if ticket_count == 0:
            return 0.1
        elif ticket_count <= 2:
            return 0.3
        elif ticket_count <= 5:
            return 0.6
        else:
            return 0.9
    
    async def _calculate_escalation_risk(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> float:
        """Calculate risk based on escalated issues"""
        # Count escalated tickets (assuming priority = 'high' or 'urgent' means escalated)
        escalated_tickets = await db.execute(
            select(func.count(SupportTicket.id))
            .where(
                and_(
                    SupportTicket.customer_id == customer.id,
                    SupportTicket.priority.in_(['high', 'urgent'])
                )
            )
        )
        escalation_count = escalated_tickets.scalar() or 0
        
        # Count unresolved escalations
        unresolved_escalations = await db.execute(
            select(func.count(SupportTicket.id))
            .where(
                and_(
                    SupportTicket.customer_id == customer.id,
                    SupportTicket.priority.in_(['high', 'urgent']),
                    SupportTicket.status.in_(['open', 'in_progress'])
                )
            )
        )
        unresolved_count = unresolved_escalations.scalar() or 0
        
        # Higher risk for unresolved escalations
        base_risk = min(escalation_count * 0.2, 0.8)
        unresolved_risk = min(unresolved_count * 0.3, 0.9)
        
        return max(base_risk, unresolved_risk)
    
    async def _calculate_recent_sentiment_risk(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> float:
        """Calculate bad review risk based on recent sentiment"""
        return await self._calculate_sentiment_risk(customer, db)
    
    async def _calculate_active_support_risk(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> float:
        """Calculate bad review risk based on active support tickets"""
        # Count open tickets
        open_tickets = await db.execute(
            select(func.count(SupportTicket.id))
            .where(
                and_(
                    SupportTicket.customer_id == customer.id,
                    SupportTicket.status.in_(['open', 'in_progress'])
                )
            )
        )
        open_count = open_tickets.scalar() or 0
        
        return min(open_count * 0.3, 1.0)
    
    async def _calculate_escalation_history_risk(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> float:
        """Calculate bad review risk based on escalation history"""
        return await self._calculate_escalation_risk(customer, db)
    
    async def _calculate_response_time_risk(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> float:
        """Calculate bad review risk based on response times"""
        # This would require tracking response times in tickets
        # For now, return moderate risk
        return 0.4
    
    async def _calculate_resolution_rate_risk(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> float:
        """Calculate bad review risk based on resolution rate"""
        # Count resolved vs total tickets
        total_tickets = await db.execute(
            select(func.count(SupportTicket.id))
            .where(SupportTicket.customer_id == customer.id)
        )
        total_count = total_tickets.scalar() or 0
        
        if total_count == 0:
            return 0.3  # No history, moderate risk
        
        resolved_tickets = await db.execute(
            select(func.count(SupportTicket.id))
            .where(
                and_(
                    SupportTicket.customer_id == customer.id,
                    SupportTicket.status == 'resolved'
                )
            )
        )
        resolved_count = resolved_tickets.scalar() or 0
        
        resolution_rate = resolved_count / total_count
        
        # Higher resolution rate = lower risk
        return max(0.0, 1.0 - resolution_rate)
    
    async def _get_risk_factors(
        self, 
        customer: Customer, 
        db: AsyncSession
    ) -> Dict[str, any]:
        """Get detailed risk factor breakdown"""
        return {
            'days_since_last_interaction': customer.days_since_last_interaction,
            'total_reviews': customer.total_reviews,
            'negative_reviews': customer.negative_reviews,
            'avg_rating_given': float(customer.avg_rating_given) if customer.avg_rating_given else None,
            'interaction_count': customer.interaction_count,
            'is_high_value': customer.is_high_value,
            'lifetime_value': float(customer.lifetime_value) if customer.lifetime_value else None
        }
    
    async def update_customer_risk_scores(
        self, 
        customer_id: str, 
        db: AsyncSession
    ) -> Dict[str, float]:
        """Update and save risk scores for a customer"""
        risk_assessment = await self.assess_customer_risk(customer_id, db)
        
        # Update customer record
        customer = await db.get(Customer, customer_id)
        if customer:
            customer.update_risk_scores(
                risk_assessment['churn_risk'],
                risk_assessment['bad_review_likelihood']
            )
            await db.commit()
        
        return risk_assessment
    
    async def get_at_risk_customers(
        self, 
        organization_id: str, 
        db: AsyncSession,
        risk_threshold: float = 0.6,
        limit: int = 100
    ) -> List[Customer]:
        """Get customers above risk threshold"""
        stmt = (
            select(Customer)
            .where(
                and_(
                    Customer.organization_id == organization_id,
                    or_(
                        Customer.churn_risk_score >= risk_threshold,
                        Customer.bad_review_likelihood >= risk_threshold
                    )
                )
            )
            .order_by(
                Customer.churn_risk_score.desc(),
                Customer.bad_review_likelihood.desc()
            )
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def batch_update_risk_scores(
        self, 
        organization_id: str, 
        db: AsyncSession,
        limit: int = 50
    ) -> Dict[str, int]:
        """Update risk scores for multiple customers in batch"""
        # Get customers that need risk score updates
        stmt = (
            select(Customer.id)
            .where(Customer.organization_id == organization_id)
            .order_by(Customer.updated_at.asc())  # Update oldest first
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        customer_ids = [row[0] for row in result.fetchall()]
        
        updated_count = 0
        error_count = 0
        
        for customer_id in customer_ids:
            try:
                await self.update_customer_risk_scores(str(customer_id), db)
                updated_count += 1
            except Exception as e:
                error_count += 1
                # Log error in production
                print(f"Error updating risk scores for customer {customer_id}: {e}")
        
        return {
            'updated': updated_count,
            'errors': error_count,
            'total_processed': len(customer_ids)
        }


# Alias for backward compatibility
CustomerRiskService = CustomerRiskAssessmentService
