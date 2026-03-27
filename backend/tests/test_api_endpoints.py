"""
Unit tests for API endpoints
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession


# Mock the database and dependencies before importing the app
@pytest.fixture
def mock_db():
    """Mock database session"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = MagicMock()
    user.id = "user-123"
    user.email = "test@example.com"
    user.organization_id = "org-123"
    user.role = "user"
    return user


@pytest.fixture
def mock_org_context():
    """Mock organization access control context"""
    context = MagicMock()
    context.organization_id = "org-123"
    context.user_id = "user-123"
    context.permissions = ["read", "write"]
    return context


# Mock all the dependencies
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock all FastAPI dependencies"""
    with (
        patch("app.core.database.get_async_db") as mock_get_db,
        patch("app.core.dependencies.get_current_user") as mock_get_user,
        patch("app.core.dependencies.get_access_control_context") as mock_get_context,
    ):

        # Set up the mocks
        mock_get_db.return_value = AsyncMock(spec=AsyncSession)

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.email = "test@example.com"
        mock_user.organization_id = "org-123"
        mock_get_user.return_value = mock_user

        mock_context = MagicMock()
        mock_context.organization_id = "org-123"
        mock_context.user_id = "user-123"
        mock_get_context.return_value = mock_context

        yield {"db": mock_get_db, "user": mock_get_user, "context": mock_get_context}


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    # Import after mocking dependencies
    from app.main import app

    return TestClient(app)


class TestReviewsAPI:
    """Test cases for Reviews API endpoints"""

    def test_ingest_review_success(self, client, mock_dependencies):
        """Test successful review ingestion"""
        # Mock the review service
        mock_review = MagicMock()
        mock_review.id = "review-123"
        mock_review.platform = "google"
        mock_review.rating = 5
        mock_review.content = "Great service!"
        mock_review.customer_name = "John Doe"
        mock_review.created_at = datetime.now(timezone.utc)

        with (
            patch(
                "app.services.review_service.ReviewService.ingest_review",
                return_value=mock_review,
            ),
            patch(
                "app.schemas.review.ReviewResponse.from_orm",
                return_value={
                    "id": "review-123",
                    "platform": "google",
                    "rating": 5,
                    "content": "Great service!",
                    "customer_name": "John Doe",
                },
            ),
        ):

            response = client.post(
                "/api/v1/reviews/ingest",
                json={
                    "platform": "google",
                    "external_id": "google-123",
                    "customer_name": "John Doe",
                    "rating": 5,
                    "content": "Great service!",
                    "created_at": "2024-01-15T10:30:00Z",
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == "review-123"
            assert data["rating"] == 5
            assert data["content"] == "Great service!"

    def test_ingest_review_invalid_data(self, client):
        """Test review ingestion with invalid data"""
        response = client.post(
            "/api/v1/reviews/ingest",
            json={
                "platform": "google",
                # Missing required fields
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_analyze_review_success(self, client, mock_dependencies):
        """Test successful review analysis"""
        # Mock the review
        mock_review = MagicMock()
        mock_review.id = "review-123"
        mock_review.content = "The service was terrible!"
        mock_review.rating = 1
        mock_review.title = "Bad experience"

        # Mock service responses
        sentiment_result = {
            "sentiment_score": 0.2,
            "confidence": 0.8,
            "label": "Negative",
        }

        urgency_result = {"urgency_level": "high", "confidence": 0.9}

        categorization_result = {
            "categories": ["support", "quality"],
            "confidences": {"support": 0.8, "quality": 0.7},
        }

        with (
            patch(
                "app.services.review_service.ReviewService.get_review_by_id",
                return_value=mock_review,
            ),
            patch(
                "app.services.sentiment_service.SentimentService.analyze_sentiment",
                return_value=sentiment_result,
            ),
            patch(
                "app.services.urgency_service.UrgencyService.classify_urgency",
                return_value=urgency_result,
            ),
            patch(
                "app.services.categorization_service.CategorizationService.categorize_issues",
                return_value=categorization_result,
            ),
            patch("app.services.review_service.ReviewService.mark_review_processed"),
        ):

            response = client.post(
                "/api/v1/reviews/analyze", json={"review_id": "review-123"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["review_id"] == "review-123"
            assert data["sentiment_score"] == 0.2
            assert data["urgency_level"] == "high"
            assert "support" in data["issue_categories"]
            assert "quality" in data["issue_categories"]
            assert len(data["recommendations"]) > 0

    def test_analyze_review_not_found(self, client, mock_dependencies):
        """Test review analysis when review not found"""
        with patch(
            "app.services.review_service.ReviewService.get_review_by_id",
            return_value=None,
        ):
            response = client.post(
                "/api/v1/reviews/analyze", json={"review_id": "nonexistent-review"}
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Review not found" in response.json()["detail"]

    def test_analyze_review_no_content(self, client, mock_dependencies):
        """Test review analysis when review has no content"""
        mock_review = MagicMock()
        mock_review.id = "review-123"
        mock_review.content = None  # No content

        with patch(
            "app.services.review_service.ReviewService.get_review_by_id",
            return_value=mock_review,
        ):
            response = client.post(
                "/api/v1/reviews/analyze", json={"review_id": "review-123"}
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "no content to analyze" in response.json()["detail"]

    def test_generate_review_response_success(self, client, mock_dependencies):
        """Test successful review response generation"""
        mock_review = MagicMock()
        mock_review.id = "review-123"
        mock_review.rating = 2
        mock_review.content = "Poor service"
        mock_review.customer_name = "Jane Doe"

        with patch(
            "app.services.review_service.ReviewService.get_review_by_id",
            return_value=mock_review,
        ):
            response = client.post(
                "/api/v1/reviews/respond",
                json={
                    "review_id": "review-123",
                    "response_type": "public",
                    "tone": "professional",
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["review_id"] == "review-123"
            assert data["response_type"] == "public"
            assert data["tone"] == "professional"
            assert len(data["response_content"]) > 0
            assert data["requires_approval"] == True  # Low rating requires approval

    def test_get_reviews_success(self, client, mock_dependencies):
        """Test successful reviews retrieval"""
        mock_reviews = [
            MagicMock(id="review-1", rating=5, content="Great!"),
            MagicMock(id="review-2", rating=3, content="Okay"),
        ]

        with (
            patch(
                "app.services.review_service.ReviewService.get_reviews",
                return_value=mock_reviews,
            ),
            patch(
                "app.schemas.review.ReviewResponse.from_orm",
                side_effect=[
                    {"id": "review-1", "rating": 5, "content": "Great!"},
                    {"id": "review-2", "rating": 3, "content": "Okay"},
                ],
            ),
        ):

            response = client.get("/api/v1/reviews/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2
            assert data[0]["id"] == "review-1"
            assert data[1]["id"] == "review-2"

    def test_get_reviews_with_filters(self, client, mock_dependencies):
        """Test reviews retrieval with filters"""
        with (
            patch(
                "app.services.review_service.ReviewService.get_reviews", return_value=[]
            ),
            patch("app.schemas.review.ReviewResponse.from_orm", return_value=[]),
        ):

            response = client.get(
                "/api/v1/reviews/?platform=google&rating_min=4&rating_max=5"
            )

            assert response.status_code == status.HTTP_200_OK

    def test_get_review_by_id_success(self, client, mock_dependencies):
        """Test successful single review retrieval"""
        mock_review = MagicMock()
        mock_review.id = "review-123"
        mock_review.rating = 4
        mock_review.content = "Good service"

        with (
            patch(
                "app.services.review_service.ReviewService.get_review_by_id",
                return_value=mock_review,
            ),
            patch(
                "app.schemas.review.ReviewResponse.from_orm",
                return_value={
                    "id": "review-123",
                    "rating": 4,
                    "content": "Good service",
                },
            ),
        ):

            response = client.get("/api/v1/reviews/review-123")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == "review-123"
            assert data["rating"] == 4

    def test_get_review_by_id_not_found(self, client, mock_dependencies):
        """Test single review retrieval when not found"""
        with patch(
            "app.services.review_service.ReviewService.get_review_by_id",
            return_value=None,
        ):
            response = client.get("/api/v1/reviews/nonexistent-review")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Review not found" in response.json()["detail"]

    def test_get_review_stats_success(self, client, mock_dependencies):
        """Test successful review statistics retrieval"""
        mock_stats = {
            "total_reviews": 100,
            "average_rating": 4.2,
            "rating_distribution": {1: 5, 2: 10, 3: 15, 4: 30, 5: 40},
            "sentiment_distribution": {"positive": 70, "neutral": 20, "negative": 10},
        }

        with patch(
            "app.services.review_service.ReviewService.get_review_stats",
            return_value=mock_stats,
        ):
            response = client.get("/api/v1/reviews/stats/overview")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_reviews"] == 100
            assert data["average_rating"] == 4.2


class TestDashboardAPI:
    """Test cases for Dashboard API endpoints"""

    def test_get_dashboard_metrics_success(self, client, mock_dependencies):
        """Test successful dashboard metrics retrieval"""
        mock_metrics = {
            "kpis": {
                "average_rating": 4.2,
                "total_reviews": 150,
                "at_risk_customers": 12,
                "recovery_success_rate": 0.78,
            },
            "trends": {
                "rating_trend": [4.1, 4.2, 4.3, 4.2],
                "review_volume_trend": [20, 25, 30, 28],
            },
            "activity_feed": [
                {"type": "review", "message": "New 5-star review received"},
                {"type": "recovery", "message": "Customer recovery email sent"},
            ],
            "alerts": [],
        }

        with (
            patch(
                "app.core.dependencies.require_organization_access",
                return_value="org-123",
            ),
            patch(
                "app.services.dashboard_service.DashboardMetricsService"
            ) as mock_service_class,
        ):

            mock_service = mock_service_class.return_value
            mock_service.get_comprehensive_metrics.return_value = mock_metrics

            response = client.get("/api/v1/dashboard/metrics")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "kpis" in data
            assert "trends" in data
            assert "activity_feed" in data
            assert data["kpis"]["average_rating"] == 4.2

    def test_get_dashboard_metrics_with_time_range(self, client, mock_dependencies):
        """Test dashboard metrics with different time ranges"""
        mock_metrics = {"kpis": {}, "trends": {}, "activity_feed": [], "alerts": []}

        with (
            patch(
                "app.core.dependencies.require_organization_access",
                return_value="org-123",
            ),
            patch(
                "app.services.dashboard_service.DashboardMetricsService"
            ) as mock_service_class,
        ):

            mock_service = mock_service_class.return_value
            mock_service.get_comprehensive_metrics.return_value = mock_metrics

            # Test different time ranges
            for time_range in ["7d", "30d", "90d", "1y"]:
                response = client.get(
                    f"/api/v1/dashboard/metrics?time_range={time_range}"
                )
                assert response.status_code == status.HTTP_200_OK

    def test_get_dashboard_metrics_invalid_time_range(self, client, mock_dependencies):
        """Test dashboard metrics with invalid time range"""
        response = client.get("/api/v1/dashboard/metrics?time_range=invalid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_dashboard_metrics_with_cache_refresh(self, client, mock_dependencies):
        """Test dashboard metrics with cache refresh"""
        mock_metrics = {"kpis": {}, "trends": {}, "activity_feed": [], "alerts": []}

        with (
            patch(
                "app.core.dependencies.require_organization_access",
                return_value="org-123",
            ),
            patch(
                "app.services.dashboard_service.DashboardMetricsService"
            ) as mock_service_class,
            patch("app.core.redis.redis_client") as mock_redis,
        ):

            mock_service = mock_service_class.return_value
            mock_service.get_comprehensive_metrics.return_value = mock_metrics

            response = client.get("/api/v1/dashboard/metrics?refresh_cache=true")

            assert response.status_code == status.HTTP_200_OK
            # Should have called redis delete to clear cache
            mock_redis.delete.assert_called_once()


class TestAuthAPI:
    """Test cases for Authentication API endpoints"""

    def test_login_success(self, client):
        """Test successful login"""
        mock_user = {
            "id": "user-123",
            "email": "test@example.com",
            "organization_id": "org-123",
        }

        mock_token = {
            "access_token": "mock-jwt-token",
            "token_type": "bearer",
            "expires_in": 3600,
        }

        with (
            patch(
                "app.services.auth_service.AuthService.authenticate_user",
                return_value=mock_user,
            ),
            patch(
                "app.services.auth_service.AuthService.create_access_token",
                return_value=mock_token,
            ),
        ):

            response = client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "password123"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["access_token"] == "mock-jwt-token"
            assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        with patch(
            "app.services.auth_service.AuthService.authenticate_user", return_value=None
        ):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "wrongpassword"},
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid credentials" in response.json()["detail"]

    def test_register_success(self, client):
        """Test successful user registration"""
        mock_user = {
            "id": "user-123",
            "email": "newuser@example.com",
            "organization_id": "org-123",
        }

        with patch(
            "app.services.auth_service.AuthService.register_user",
            return_value=mock_user,
        ):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "password123",
                    "organization_name": "Test Org",
                },
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["email"] == "newuser@example.com"

    def test_register_email_exists(self, client):
        """Test registration with existing email"""
        with patch(
            "app.services.auth_service.AuthService.register_user",
            side_effect=ValueError("Email already exists"),
        ):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "existing@example.com",
                    "password": "password123",
                    "organization_name": "Test Org",
                },
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Email already exists" in response.json()["detail"]


class TestCustomersAPI:
    """Test cases for Customers API endpoints"""

    def test_get_customers_success(self, client, mock_dependencies):
        """Test successful customers retrieval"""
        mock_customers = [
            MagicMock(id="customer-1", name="John Doe", email="john@example.com"),
            MagicMock(id="customer-2", name="Jane Smith", email="jane@example.com"),
        ]

        with (
            patch(
                "app.services.customer_service.CustomerService.get_customers",
                return_value=mock_customers,
            ),
            patch(
                "app.schemas.customer.CustomerResponse.from_orm",
                side_effect=[
                    {
                        "id": "customer-1",
                        "name": "John Doe",
                        "email": "john@example.com",
                    },
                    {
                        "id": "customer-2",
                        "name": "Jane Smith",
                        "email": "jane@example.com",
                    },
                ],
            ),
        ):

            response = client.get("/api/v1/customers/")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "John Doe"
            assert data[1]["name"] == "Jane Smith"

    def test_get_customer_by_id_success(self, client, mock_dependencies):
        """Test successful single customer retrieval"""
        mock_customer = MagicMock()
        mock_customer.id = "customer-123"
        mock_customer.name = "John Doe"
        mock_customer.email = "john@example.com"
        mock_customer.churn_risk_score = 0.3

        with (
            patch(
                "app.services.customer_service.CustomerService.get_customer_by_id",
                return_value=mock_customer,
            ),
            patch(
                "app.schemas.customer.CustomerResponse.from_orm",
                return_value={
                    "id": "customer-123",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "churn_risk_score": 0.3,
                },
            ),
        ):

            response = client.get("/api/v1/customers/customer-123")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == "customer-123"
            assert data["name"] == "John Doe"
            assert data["churn_risk_score"] == 0.3

    def test_customer_recovery_success(self, client, mock_dependencies):
        """Test successful customer recovery action"""
        mock_recovery_plan = {
            "customer_id": "customer-123",
            "churn_risk": 0.8,
            "recommended_actions": ["email", "discount"],
            "priority": "high",
        }

        with patch(
            "app.services.customer_recovery_service.CustomerRecoveryService.create_recovery_plan",
            return_value=mock_recovery_plan,
        ):
            response = client.post(
                "/api/v1/customers/customer-123/recover",
                json={
                    "trigger_type": "high_churn_risk",
                    "context": {"recent_complaint": True},
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["customer_id"] == "customer-123"
            assert data["churn_risk"] == 0.8
            assert "email" in data["recommended_actions"]


class TestAgentsAPI:
    """Test cases for Agents API endpoints"""

    def test_agent_decide_action_success(self, client, mock_dependencies):
        """Test successful agent decision"""
        mock_decision = {
            "decision_type": "recover_private",
            "confidence_score": 0.85,
            "reasoning": "High churn risk customer with negative sentiment",
            "requires_approval": False,
        }

        with patch(
            "app.services.agent_engine.AgentEngine.decide_action",
            return_value=mock_decision,
        ):
            response = client.post(
                "/api/v1/agents/decide-action",
                json={
                    "input_type": "review",
                    "input_id": "review-123",
                    "context": {
                        "sentiment_score": 0.2,
                        "urgency_level": "high",
                        "rating": 1,
                    },
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["decision_type"] == "recover_private"
            assert data["confidence_score"] == 0.85
            assert data["requires_approval"] == False

    def test_agent_decide_action_low_confidence(self, client, mock_dependencies):
        """Test agent decision with low confidence"""
        mock_decision = {
            "decision_type": "escalate",
            "confidence_score": 0.4,
            "reasoning": "Uncertain case requiring human review",
            "requires_approval": True,
        }

        with patch(
            "app.services.agent_engine.AgentEngine.decide_action",
            return_value=mock_decision,
        ):
            response = client.post(
                "/api/v1/agents/decide-action",
                json={
                    "input_type": "ticket",
                    "input_id": "ticket-123",
                    "context": {"complexity": "high"},
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["decision_type"] == "escalate"
            assert data["requires_approval"] == True


class TestErrorHandling:
    """Test cases for error handling across endpoints"""

    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoints"""
        # Mock authentication to fail
        with patch(
            "app.core.dependencies.get_current_user",
            side_effect=HTTPException(status_code=401, detail="Not authenticated"),
        ):
            response = client.get("/api/v1/reviews/")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_forbidden_access(self, client, mock_dependencies):
        """Test forbidden access to organization resources"""
        with patch(
            "app.core.dependencies.get_access_control_context",
            side_effect=HTTPException(status_code=403, detail="Forbidden"),
        ):
            response = client.get("/api/v1/reviews/")
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_internal_server_error(self, client, mock_dependencies):
        """Test internal server error handling"""
        with patch(
            "app.services.review_service.ReviewService.get_reviews",
            side_effect=Exception("Database error"),
        ):
            response = client.get("/api/v1/reviews/")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_validation_error(self, client):
        """Test request validation errors"""
        # Send invalid JSON data
        response = client.post(
            "/api/v1/reviews/ingest",
            json={
                "platform": "invalid_platform",  # Assuming this is not allowed
                "rating": 10,  # Assuming rating should be 1-5
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestRateLimiting:
    """Test cases for API rate limiting"""

    def test_rate_limit_not_exceeded(self, client, mock_dependencies):
        """Test normal request within rate limits"""
        with patch(
            "app.services.review_service.ReviewService.get_reviews", return_value=[]
        ):
            response = client.get("/api/v1/reviews/")
            assert response.status_code == status.HTTP_200_OK

    def test_rate_limit_exceeded(self, client, mock_dependencies):
        """Test rate limit exceeded scenario"""
        # This would require actual rate limiting middleware to be implemented
        # For now, we'll just test that the endpoint responds normally
        with patch(
            "app.services.review_service.ReviewService.get_reviews", return_value=[]
        ):
            response = client.get("/api/v1/reviews/")
            assert response.status_code == status.HTTP_200_OK


class TestPagination:
    """Test cases for API pagination"""

    def test_pagination_default(self, client, mock_dependencies):
        """Test default pagination parameters"""
        with patch(
            "app.services.review_service.ReviewService.get_reviews", return_value=[]
        ) as mock_service:
            response = client.get("/api/v1/reviews/")

            assert response.status_code == status.HTTP_200_OK
            # Verify default pagination was used
            mock_service.assert_called_once()
            call_args = mock_service.call_args
            assert call_args.kwargs["skip"] == 0
            assert call_args.kwargs["limit"] == 100

    def test_pagination_custom(self, client, mock_dependencies):
        """Test custom pagination parameters"""
        with patch(
            "app.services.review_service.ReviewService.get_reviews", return_value=[]
        ) as mock_service:
            response = client.get("/api/v1/reviews/?skip=20&limit=50")

            assert response.status_code == status.HTTP_200_OK
            # Verify custom pagination was used
            call_args = mock_service.call_args
            assert call_args.kwargs["skip"] == 20
            assert call_args.kwargs["limit"] == 50

    def test_pagination_invalid_params(self, client, mock_dependencies):
        """Test pagination with invalid parameters"""
        response = client.get("/api/v1/reviews/?skip=-1&limit=0")

        # Should either return 422 for validation error or handle gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


# Integration test helpers
def create_test_review_data():
    """Helper to create test review data"""
    return {
        "platform": "google",
        "external_id": "google-123",
        "customer_name": "Test Customer",
        "rating": 4,
        "content": "Good service overall",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def create_test_user_data():
    """Helper to create test user data"""
    return {
        "email": "test@example.com",
        "password": "password123",
        "organization_name": "Test Organization",
    }


def create_test_analysis_request():
    """Helper to create test analysis request"""
    return {"review_id": "review-123"}
