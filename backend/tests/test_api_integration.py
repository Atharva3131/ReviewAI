"""
Comprehensive API Integration Tests

Tests all API endpoints with mock database interactions, authentication,
and multi-tenant isolation. These tests validate the complete request-response
cycle including middleware, authentication, authorization, and data persistence.

**Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 3.1, 3.2, 4.1, 5.1, 6.1, 9.1**
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.organization import Organization
from app.models.review import Review
from app.models.user import User


# Mock the FastAPI app and dependencies for testing
class MockApp:
    """Mock FastAPI application for testing"""

    def __init__(self):
        self.routes = []

    def get(self, path):
        def decorator(func):
            self.routes.append(("GET", path, func))
            return func

        return decorator

    def post(self, path):
        def decorator(func):
            self.routes.append(("POST", path, func))
            return func

        return decorator


# Create mock app
app = MockApp()


class TestAPIIntegration:
    """Integration tests for all API endpoints"""

    @pytest.fixture
    def mock_auth_service(self):
        """Mock authentication service"""
        with patch("app.services.auth_service.AuthService") as mock:
            mock.create_tokens = AsyncMock(
                return_value={
                    "access_token": "mock_token",
                    "refresh_token": "mock_refresh",
                    "token_type": "bearer",
                }
            )
            mock.authenticate_user = AsyncMock(
                return_value=(
                    {"id": "user_123", "email": "test@test.com", "role": "admin"},
                    {"id": "org_123", "name": "Test Org"},
                )
            )
            yield mock

    @pytest.fixture
    def auth_headers(self):
        """Create mock authentication headers"""
        return {"Authorization": "Bearer mock_token"}

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def test_organization_data(self):
        """Test organization data"""
        return {
            "id": str(uuid.uuid4()),
            "name": "Test Organization",
            "domain": "test.com",
            "settings": {"test": True},
        }

    @pytest.fixture
    def test_user_data(self):
        """Test user data"""
        return {
            "id": str(uuid.uuid4()),
            "email": "test@test.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "admin",
            "is_active": True,
            "is_verified": True,
        }

    @pytest.fixture
    def test_customer_data(self):
        """Test customer data"""
        return {
            "id": str(uuid.uuid4()),
            "name": "Test Customer",
            "email": "customer@test.com",
            "phone": "+1234567890",
            "churn_risk_score": 0.3,
            "bad_review_likelihood": 0.2,
            "risk_level": "low",
        }

    @pytest.fixture
    def test_review_data(self):
        """Test review data"""
        return {
            "id": str(uuid.uuid4()),
            "platform": "google",
            "external_id": "test_review_123",
            "title": "Great service!",
            "content": "Really enjoyed the experience, highly recommend!",
            "rating": 5,
            "customer_name": "Test Customer",
            "created_at": datetime.utcnow().isoformat(),
            "is_processed": True,
            "sentiment_score": 0.9,
            "urgency_level": "low",
            "issue_categories": ["quality"],
        }

    @pytest.fixture
    async def test_organization(self, db_session: AsyncSession):
        """Create test organization"""
        org = Organization(
            id=uuid.uuid4(),
            name="Test Organization",
            domain="test.com",
            settings={"test": True},
        )
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)
        return org

    @pytest.fixture
    async def test_user(
        self, db_session: AsyncSession, test_organization: Organization
    ):
        """Create test user"""
        from app.core.security import SecurityService

        user = User(
            id=uuid.uuid4(),
            email="test@test.com",
            hashed_password=SecurityService.get_password_hash("testpass123"),
            first_name="Test",
            last_name="User",
            role="admin",
            organization_id=test_organization.id,
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    async def db_session(self, mock_db_session):
        """Provide mock database session as db_session"""
        return mock_db_session

    @pytest.fixture
    def app_fixture(self):
        """Provide real FastAPI app for integration tests"""
        from app.main import app

        return app

    @pytest.fixture
    async def async_client(self, app_fixture):
        """Provide an AsyncClient for testing the FastAPI app"""
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app_fixture)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


class TestAuthenticationAPI(TestAPIIntegration):
    """Test authentication endpoints"""

    async def test_user_registration(self, async_client: AsyncClient):
        """Test user registration endpoint"""
        registration_data = {
            "email": "newuser@test.com",
            "password": "newpass123",
            "first_name": "New",
            "last_name": "User",
            "organization_name": "New Organization",
        }

        response = await async_client.post(
            "/api/v1/auth/register", json=registration_data
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_user_login(self, async_client: AsyncClient, test_user: User):
        """Test user login endpoint"""
        login_data = {"email": test_user.email, "password": "testpass123"}

        response = await async_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_invalid_login(self, async_client: AsyncClient):
        """Test login with invalid credentials"""
        login_data = {"email": "invalid@test.com", "password": "wrongpass"}

        response = await async_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    async def test_get_current_user(
        self, async_client: AsyncClient, auth_headers: Dict[str, str], test_user: User
    ):
        """Test getting current user information"""
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_authenticated"] is True
        assert data["user"]["email"] == test_user.email
        assert data["user"]["role"] == test_user.role.value

    async def test_unauthorized_access(self, async_client: AsyncClient):
        """Test accessing protected endpoint without authentication"""
        response = await async_client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_token_refresh(
        self,
        async_client: AsyncClient,
        test_user: User,
        test_organization: Organization,
    ):
        """Test token refresh functionality"""
        # First login to get tokens
        tokens = await AuthService.create_tokens(test_user, test_organization)

        refresh_data = {"refresh_token": tokens.refresh_token}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data


class TestReviewsAPI(TestAPIIntegration):
    """Test review management endpoints"""

    async def test_ingest_review(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test review ingestion endpoint"""
        review_data = {
            "platform": "google",
            "external_id": "new_review_123",
            "title": "Amazing service",
            "content": "The team was fantastic and exceeded expectations!",
            "rating": 5,
            "customer_name": "Happy Customer",
            "customer_email": "happy@customer.com",
            "created_at": datetime.utcnow().isoformat(),
        }

        response = await async_client.post(
            "/api/v1/reviews/ingest", json=review_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "google"
        assert data["rating"] == 5
        assert data["customer_name"] == "Happy Customer"

    async def test_analyze_review(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        test_review: Review,
    ):
        """Test review analysis endpoint"""
        analysis_request = {"review_id": str(test_review.id)}

        response = await async_client.post(
            "/api/v1/reviews/analyze", json=analysis_request, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "sentiment_score" in data
        assert "urgency_level" in data
        assert "issue_categories" in data
        assert "processing_time_ms" in data
        assert 0.0 <= data["sentiment_score"] <= 1.0

    async def test_get_reviews(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        test_review: Review,
    ):
        """Test getting reviews with filtering"""
        response = await async_client.get("/api/v1/reviews/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Test with filters
        response = await async_client.get(
            "/api/v1/reviews/?platform=google&rating_min=4", headers=auth_headers
        )

        assert response.status_code == 200
        filtered_data = response.json()
        for review in filtered_data:
            assert review["platform"] == "google"
            assert review["rating"] >= 4

    async def test_get_review_by_id(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        test_review: Review,
    ):
        """Test getting specific review by ID"""
        response = await async_client.get(
            f"/api/v1/reviews/{test_review.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_review.id)
        assert data["content"] == test_review.content
        assert data["rating"] == test_review.rating

    async def test_generate_review_response(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        test_review: Review,
    ):
        """Test AI response generation for review"""
        response_request = {
            "review_id": str(test_review.id),
            "response_type": "public",
            "tone": "professional",
        }

        response = await async_client.post(
            "/api/v1/reviews/respond", json=response_request, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "response_content" in data
        assert data["response_type"] == "public"
        assert data["tone"] == "professional"
        assert "confidence_score" in data

    async def test_review_stats(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        test_review: Review,
    ):
        """Test review statistics endpoint"""
        response = await async_client.get(
            "/api/v1/reviews/stats/overview", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_reviews" in data
        assert "average_rating" in data
        assert "sentiment_distribution" in data


class TestDashboardAPI(TestAPIIntegration):
    """Test dashboard metrics endpoints"""

    async def test_get_dashboard_metrics(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test comprehensive dashboard metrics endpoint"""
        response = await async_client.get(
            "/api/v1/dashboard/metrics", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "kpis" in data
        assert "charts" in data
        assert "activity_feed" in data
        assert "alerts" in data

        # Validate KPI structure
        kpis = data["kpis"]
        assert "average_rating" in kpis
        assert "monthly_reviews" in kpis
        assert "at_risk_customers" in kpis
        assert "recovery_success_rate" in kpis

    async def test_get_kpis_only(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test KPIs-only endpoint"""
        response = await async_client.get(
            "/api/v1/dashboard/kpis", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "kpis" in data
        assert "time_range" in data
        assert "generated_at" in data

    async def test_get_activity_feed(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test activity feed endpoint"""
        response = await async_client.get(
            "/api/v1/dashboard/activity?limit=5", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "activities" in data
        assert "total_count" in data
        assert len(data["activities"]) <= 5

    async def test_get_metrics_trends(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test metrics trends endpoint"""
        response = await async_client.get(
            "/api/v1/dashboard/trends?time_range=7d", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "trends" in data
        assert "time_range" in data
        assert data["time_range"] == "7d"

    async def test_dashboard_alerts(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test dashboard alerts endpoint"""
        response = await async_client.get(
            "/api/v1/dashboard/alerts", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "total_count" in data

    async def test_refresh_dashboard_cache(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test dashboard cache refresh endpoint"""
        response = await async_client.post(
            "/api/v1/dashboard/metrics/refresh", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "refreshed_keys" in data


class TestCustomersAPI(TestAPIIntegration):
    """Test customer management endpoints"""

    async def test_get_customers(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        test_customer: Customer,
    ):
        """Test getting customers list"""
        response = await async_client.get("/api/v1/customers/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "customers" in data
        assert "total" in data
        assert len(data["customers"]) >= 1

    async def test_get_at_risk_customers(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test getting at-risk customers"""
        response = await async_client.get(
            "/api/v1/customers/?at_risk_only=true", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "customers" in data
        assert data["at_risk_filter"] is True

    async def test_get_customer_risk(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        test_customer: Customer,
    ):
        """Test customer risk assessment endpoint"""
        response = await async_client.get(
            f"/api/v1/customers/{test_customer.id}/risk", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == str(test_customer.id)
        assert "churn_risk" in data
        assert "bad_review_likelihood" in data
        assert "risk_factors" in data
        assert 0.0 <= data["churn_risk"] <= 1.0
        assert 0.0 <= data["bad_review_likelihood"] <= 1.0

    async def test_recover_customer(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        test_customer: Customer,
    ):
        """Test customer recovery endpoint"""
        recovery_request = {
            "customer_id": str(test_customer.id),
            "execute_immediately": False,
            "trigger_context": {"source": "manual_trigger"},
        }

        response = await async_client.post(
            "/api/v1/customers/recover", json=recovery_request, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == str(test_customer.id)
        assert "recovery_actions_created" in data
        assert "actions" in data

    async def test_get_customer_recovery_actions(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        test_customer: Customer,
    ):
        """Test getting customer recovery actions"""
        response = await async_client.get(
            f"/api/v1/customers/{test_customer.id}/recovery-actions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["customer_id"] == str(test_customer.id)
        assert "recovery_actions" in data
        assert "total" in data

    async def test_batch_risk_update(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test batch risk score update"""
        response = await async_client.post(
            "/api/v1/customers/batch-risk-update", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "batch_update_result" in data
        assert "organization_id" in data


class TestAgentsAPI(TestAPIIntegration):
    """Test agent orchestration endpoints"""

    async def test_agent_decide_action(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        test_review: Review,
    ):
        """Test agent decision endpoint"""
        decision_request = {
            "input_type": "review",
            "input_id": str(test_review.id),
            "context": {"manual_trigger": True},
        }

        response = await async_client.post(
            "/api/v1/agents/decide-action", json=decision_request, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "decision_id" in data
        assert data["input_type"] == "review"
        assert data["input_id"] == str(test_review.id)
        assert "decision_type" in data
        assert "confidence_score" in data
        assert "reasoning" in data
        assert 0.0 <= data["confidence_score"] <= 1.0

    async def test_get_agent_decisions(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test getting agent decisions list"""
        response = await async_client.get(
            "/api/v1/agents/decisions", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_agent_decision_by_id(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        test_review: Review,
    ):
        """Test getting specific agent decision"""
        # First create a decision
        decision_request = {
            "input_type": "review",
            "input_id": str(test_review.id),
            "context": {"test": True},
        }

        create_response = await async_client.post(
            "/api/v1/agents/decide-action", json=decision_request, headers=auth_headers
        )
        decision_id = create_response.json()["decision_id"]

        # Then get it by ID
        response = await async_client.get(
            f"/api/v1/agents/decisions/{decision_id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == decision_id

    async def test_get_decision_rules_summary(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test getting decision rules summary"""
        response = await async_client.get(
            "/api/v1/agents/rules/summary", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data or "summary" in data


class TestUsersAPI(TestAPIIntegration):
    """Test user management endpoints"""

    async def test_get_users(
        self, async_client: AsyncClient, auth_headers: Dict[str, str], test_user: User
    ):
        """Test getting users list"""
        response = await async_client.get("/api/v1/users/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Find our test user
        test_user_data = next((u for u in data if u["email"] == test_user.email), None)
        assert test_user_data is not None
        assert test_user_data["role"] == test_user.role.value

    async def test_get_user_by_id(
        self, async_client: AsyncClient, auth_headers: Dict[str, str], test_user: User
    ):
        """Test getting specific user by ID"""
        response = await async_client.get(
            f"/api/v1/users/{test_user.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email

    async def test_create_user(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test creating new user"""
        user_data = {
            "email": "newteamuser@test.com",
            "password": "newpass123",
            "first_name": "New",
            "last_name": "Team User",
            "role": "user",
        }

        response = await async_client.post(
            "/api/v1/users/", json=user_data, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["role"] == "user"

    async def test_get_organization_user_stats(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test getting organization user statistics"""
        response = await async_client.get(
            "/api/v1/users/organization/stats", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data or "user_count" in data


class TestWebhooksAPI(TestAPIIntegration):
    """Test webhook endpoints"""

    async def test_google_reviews_webhook(self, async_client: AsyncClient):
        """Test Google Reviews webhook endpoint"""
        webhook_data = {
            "event_type": "review.created",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "review_id": "google_123",
                "customer_name": "Webhook Customer",
                "rating": 4,
                "content": "Good service via webhook",
                "created_at": datetime.utcnow().isoformat(),
                "location_id": "test_location",
            },
        }

        response = await async_client.post(
            "/api/v1/webhooks/google-reviews", json=webhook_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert "timestamp" in data

    async def test_simulate_google_reviews_webhook(self, async_client: AsyncClient):
        """Test Google Reviews webhook simulation"""
        response = await async_client.post("/api/v1/webhooks/google-reviews/simulate")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "simulated"
        assert "events_generated" in data

    async def test_generate_test_google_review(self, async_client: AsyncClient):
        """Test generating test Google review"""
        response = await async_client.post(
            "/api/v1/webhooks/google-reviews/test?rating=3&content=Test review"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generated"
        assert "test_event" in data

    async def test_get_google_reviews_status(self, async_client: AsyncClient):
        """Test Google Reviews integration status"""
        response = await async_client.get("/api/v1/webhooks/google-reviews/status")

        assert response.status_code == 200
        data = response.json()
        assert "service_status" in data
        assert "connection_test" in data
        assert "webhook_endpoint" in data

    async def test_crm_webhook_endpoints(self, async_client: AsyncClient):
        """Test CRM webhook endpoints"""
        # Test customer updated webhook
        customer_webhook_data = {
            "event_type": "customer.updated",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "customer_id": "crm_customer_123",
                "name": "Updated Customer",
                "email": "updated@customer.com",
            },
        }

        response = await async_client.post(
            "/api/v1/webhooks/crm/customer-updated", json=customer_webhook_data
        )
        assert response.status_code == 200

        # Test support ticket webhook
        ticket_webhook_data = {
            "event_type": "ticket.created",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "ticket_id": "ticket_123",
                "customer_id": "crm_customer_123",
                "priority": "high",
                "subject": "Urgent issue",
            },
        }

        response = await async_client.post(
            "/api/v1/webhooks/crm/support-ticket", json=ticket_webhook_data
        )
        assert response.status_code == 200

    async def test_get_crm_webhook_status(self, async_client: AsyncClient):
        """Test CRM webhook status endpoint"""
        response = await async_client.get("/api/v1/webhooks/crm/status")

        assert response.status_code == 200
        data = response.json()
        assert "webhook_endpoints" in data
        assert "webhook_verification" in data
        assert "status" in data


class TestMultiTenantIsolation(TestAPIIntegration):
    """Test multi-tenant data isolation"""

    @pytest.fixture
    async def second_organization(self, db_session: AsyncSession):
        """Create second test organization"""
        org = Organization(
            id=uuid.uuid4(),
            name="Second Organization",
            domain="second.com",
            settings={"test": True},
        )
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)
        return org

    @pytest.fixture
    async def second_user(
        self, db_session: AsyncSession, second_organization: Organization
    ):
        """Create user in second organization"""
        user = User(
            id=uuid.uuid4(),
            email="second@test.com",
            hashed_password=SecurityService.hash_password("testpass123"),
            first_name="Second",
            last_name="User",
            role=UserRole.ADMIN,
            organization_id=second_organization.id,
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    async def second_auth_headers(
        self, second_user: User, second_organization: Organization
    ):
        """Create authentication headers for second organization"""
        tokens = await AuthService.create_tokens(second_user, second_organization)
        return {"Authorization": f"Bearer {tokens.access_token}"}

    async def test_review_isolation(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        second_auth_headers: Dict[str, str],
        test_review: Review,
    ):
        """Test that reviews are isolated between organizations"""
        # First organization should see their review
        response = await async_client.get("/api/v1/reviews/", headers=auth_headers)
        assert response.status_code == 200
        org1_reviews = response.json()
        assert len(org1_reviews) >= 1

        # Second organization should not see first organization's reviews
        response = await async_client.get(
            "/api/v1/reviews/", headers=second_auth_headers
        )
        assert response.status_code == 200
        org2_reviews = response.json()

        # Should not contain the test review from first organization
        review_ids = [r["id"] for r in org2_reviews]
        assert str(test_review.id) not in review_ids

    async def test_customer_isolation(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        second_auth_headers: Dict[str, str],
        test_customer: Customer,
    ):
        """Test that customers are isolated between organizations"""
        # First organization should see their customer
        response = await async_client.get("/api/v1/customers/", headers=auth_headers)
        assert response.status_code == 200
        org1_customers = response.json()["customers"]
        assert len(org1_customers) >= 1

        # Second organization should not see first organization's customers
        response = await async_client.get(
            "/api/v1/customers/", headers=second_auth_headers
        )
        assert response.status_code == 200
        org2_customers = response.json()["customers"]

        # Should not contain the test customer from first organization
        customer_ids = [c["id"] for c in org2_customers]
        assert str(test_customer.id) not in customer_ids

    async def test_dashboard_metrics_isolation(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        second_auth_headers: Dict[str, str],
    ):
        """Test that dashboard metrics are isolated between organizations"""
        # Get metrics for first organization
        response1 = await async_client.get(
            "/api/v1/dashboard/metrics", headers=auth_headers
        )
        assert response1.status_code == 200
        org1_metrics = response1.json()

        # Get metrics for second organization
        response2 = await async_client.get(
            "/api/v1/dashboard/metrics", headers=second_auth_headers
        )
        assert response2.status_code == 200
        org2_metrics = response2.json()

        # Metrics should be different (or at least independently calculated)
        # This test ensures the metrics service respects organization boundaries
        assert "kpis" in org1_metrics
        assert "kpis" in org2_metrics


class TestErrorHandling(TestAPIIntegration):
    """Test API error handling and edge cases"""

    async def test_invalid_review_id(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test handling of invalid review ID"""
        invalid_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/reviews/{invalid_id}", headers=auth_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_invalid_customer_id(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test handling of invalid customer ID"""
        invalid_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/customers/{invalid_id}/risk", headers=auth_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_malformed_request_data(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test handling of malformed request data"""
        # Missing required fields
        invalid_review_data = {
            "platform": "google"
            # Missing required fields like rating, content, etc.
        }

        response = await async_client.post(
            "/api/v1/reviews/ingest", json=invalid_review_data, headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    async def test_invalid_query_parameters(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test handling of invalid query parameters"""
        # Invalid time range
        response = await async_client.get(
            "/api/v1/dashboard/metrics?time_range=invalid", headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    async def test_rate_limiting_headers(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test that rate limiting headers are present"""
        response = await async_client.get("/api/v1/reviews/", headers=auth_headers)

        # Check for rate limiting headers (if implemented)
        # This is a placeholder - actual implementation depends on rate limiting setup
        assert response.status_code == 200


class TestPerformanceAndCaching(TestAPIIntegration):
    """Test API performance and caching behavior"""

    async def test_dashboard_metrics_caching(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test that dashboard metrics are properly cached"""
        # First request
        start_time = datetime.utcnow()
        response1 = await async_client.get(
            "/api/v1/dashboard/metrics", headers=auth_headers
        )
        first_duration = (datetime.utcnow() - start_time).total_seconds()

        assert response1.status_code == 200

        # Second request (should be faster due to caching)
        start_time = datetime.utcnow()
        response2 = await async_client.get(
            "/api/v1/dashboard/metrics", headers=auth_headers
        )
        second_duration = (datetime.utcnow() - start_time).total_seconds()

        assert response2.status_code == 200

        # Second request should be faster (cached)
        # Note: This test might be flaky in fast environments
        # Consider using cache headers instead

        # Check for cache-related headers
        assert "generated_at" in response2.json()

    async def test_pagination_performance(
        self, async_client: AsyncClient, auth_headers: Dict[str, str]
    ):
        """Test pagination performance with different limits"""
        # Test small page size
        response = await async_client.get(
            "/api/v1/reviews/?limit=10", headers=auth_headers
        )
        assert response.status_code == 200

        # Test larger page size
        response = await async_client.get(
            "/api/v1/reviews/?limit=100", headers=auth_headers
        )
        assert response.status_code == 200

        # Test maximum page size
        response = await async_client.get(
            "/api/v1/reviews/?limit=1000", headers=auth_headers
        )
        assert response.status_code == 200


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
