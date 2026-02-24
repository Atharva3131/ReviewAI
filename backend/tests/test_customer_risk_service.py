"""
Unit tests for customer risk assessment service
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.customer_risk_service import CustomerRiskAssessmentService
from app.models.customer import Customer
from app.models.review import Review
from app.models.support_ticket import SupportTicket
from app.models.recovery_action import RecoveryAction


class TestCustomerRiskAssessmentService:
    """Test cases for CustomerRiskAssessmentService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = CustomerRiskAssessmentService()
        self.mock_db = AsyncMock(spec=AsyncSession)
    
    def create_mock_customer(self, **kwargs):
        """Create a mock customer with default values"""
        defaults = {
            'id': 'customer-123',
            'organization_id': 'org-123',
            'last_interaction': datetime.now(timezone.utc) - timedelta(days=5),
            'days_since_last_interaction': 5,
            'total_reviews': 10,
            'negative_reviews': 2,
            'avg_rating_given': Decimal('4.0'),
            'interaction_count': 15,
            'is_high_value': False,
            'lifetime_value': Decimal('500.00'),
            'churn_risk_score': None,
            'bad_review_likelihood': None
        }
        defaults.update(kwargs)
        
        customer = MagicMock(spec=Customer)
        for key, value in defaults.items():
            setattr(customer, key, value)
        
        return customer
    
    @pytest.mark.asyncio
    async def test_assess_customer_risk_high_risk(self):
        """Test risk assessment for high-risk customer"""
        # Create high-risk customer
        customer = self.create_mock_customer(
            last_interaction=datetime.now(timezone.utc) - timedelta(days=60),
            days_since_last_interaction=60,
            avg_rating_given=Decimal('2.0'),
            negative_reviews=8,
            total_reviews=10
        )
        
        # Mock database queries
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = customer
        self.mock_db.execute.return_value.scalar.return_value = 0  # No recent interactions
        self.mock_db.execute.return_value.fetchall.return_value = [(0.2,), (0.1,)]  # Low sentiment scores
        
        with patch.object(self.service, '_get_customer_with_data', return_value=customer):
            result = await self.service.assess_customer_risk('customer-123', self.mock_db)
        
        assert 'churn_risk' in result
        assert 'bad_review_likelihood' in result
        assert 'risk_factors' in result
        
        # High-risk customer should have elevated scores
        assert result['churn_risk'] >= 0.5
        assert result['bad_review_likelihood'] >= 0.3
        assert 0.0 <= result['churn_risk'] <= 1.0
        assert 0.0 <= result['bad_review_likelihood'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_assess_customer_risk_low_risk(self):
        """Test risk assessment for low-risk customer"""
        # Create low-risk customer
        customer = self.create_mock_customer(
            last_interaction=datetime.now(timezone.utc) - timedelta(days=2),
            days_since_last_interaction=2,
            avg_rating_given=Decimal('4.5'),
            negative_reviews=1,
            total_reviews=20,
            is_high_value=True
        )
        
        # Mock database queries for positive scenario
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = customer
        self.mock_db.execute.return_value.scalar.return_value = 5  # Recent interactions
        self.mock_db.execute.return_value.fetchall.return_value = [(0.8,), (0.9,)]  # High sentiment scores
        
        with patch.object(self.service, '_get_customer_with_data', return_value=customer):
            result = await self.service.assess_customer_risk('customer-123', self.mock_db)
        
        # Low-risk customer should have lower scores
        assert result['churn_risk'] <= 0.5
        assert result['bad_review_likelihood'] <= 0.5
        assert 0.0 <= result['churn_risk'] <= 1.0
        assert 0.0 <= result['bad_review_likelihood'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_assess_customer_risk_customer_not_found(self):
        """Test risk assessment when customer is not found"""
        with patch.object(self.service, '_get_customer_with_data', return_value=None):
            with pytest.raises(ValueError, match="Customer customer-123 not found"):
                await self.service.assess_customer_risk('customer-123', self.mock_db)
    
    def test_calculate_recency_risk(self):
        """Test recency risk calculation"""
        # No interaction history
        customer_no_interaction = self.create_mock_customer(last_interaction=None)
        risk = self.service._calculate_recency_risk(customer_no_interaction)
        assert risk == 0.8
        
        # Very recent interaction (2 days)
        customer_recent = self.create_mock_customer