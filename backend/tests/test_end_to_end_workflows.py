"""
End-to-End Workflow Tests

**Validates: Requirements 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 6.1, 6.2**

These tests validate complete user workflows from start to finish,
ensuring all system components work together correctly.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.main import app
from app.models.agent_decision import AgentDecision
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.recovery_action import RecoveryAction
from app.models.review import Review
from app.models.user import User
from app.services.auth_service import AuthService


class TestCompleteReviewWorkflow:
    """Test complete review processing workflow from ingestion to response"""

    @pytest.mark.asyncio
    async def test_complete_review_ingestion_and_processing_workflow(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: Dict[str, str],
    ):
        """
        Test complete workflow: Review ingestion → Analysis → Agent decision → Response generation

        **Validates: Requirements 1.1, 2.1, 4.1, 4.2, 5.1**
        """
        # Step 1: Ingest a negative review
        review_data = {
            "platform": "google",
            "external_id": f"test_review_{uuid.uuid4()}",
            "customer_name": "John Doe",
            "customer_email": "john.doe@example.com",
            "title": "Terrible service experience",
            "content": "The service was absolutely horrible. Staff was rude, food was cold, and the wait time was unacceptable. I will never come back and will tell everyone to avoid this place.",
            "rating": 1,
            "review_date": datetime.utcnow().isoformat(),
            "reviewer_location": "New York, NY",
        }

        # Ingest review
        ingest_response = await async_client.post(
            "/api/v1/reviews/ingest", json=review_data, headers=auth_headers
        )
        assert ingest_response.status_code == 200
        review_result = ingest_response.json()
        review_id = review_result["id"]

        # Verify review was created
        assert review_result["platform"] == "google"
        assert review_result["rating"] == 1
        assert review_result["customer_name"] == "John Doe"

        # Step 2: Analyze the review
        analysis_request = {"review_id": review_id}
        analysis_response = await async_client.post(
            "/api/v1/reviews/analyze", json=analysis_request, headers=auth_headers
        )
        assert analysis_response.status_code == 200
        analysis_result = analysis_response.json()

        # Verify analysis results
        assert analysis_result["review_id"] == review_id
        assert analysis_result["sentiment_score"] < 0.5  # Should be negative
        assert analysis_result["urgency_level"] in ["medium", "high"]
        assert len(analysis_result["issue_categories"]) > 0
        assert (
            "Consider private recovery outreach" in analysis_result["recommendations"]
        )

        # Step 3: Get agent decision
        agent_request = {
            "input_type": "review",
            "input_id": review_id,
            "context": {"trigger": "negative_review_analysis"},
        }
        agent_response = await async_client.post(
            "/api/v1/agents/decide-action", json=agent_request, headers=auth_headers
        )
        assert agent_response.status_code == 200
        agent_result = agent_response.json()

        # Verify agent decision
        assert agent_result["input_type"] == "review"
        assert agent_result["input_id"] == review_id
        assert agent_result["decision_type"] in [
            "respond_publicly",
            "escalate_to_human",
            "initiate_recovery",
        ]
        assert agent_result["confidence_score"] > 0.5
        assert len(agent_result["reasoning"]) > 0

        # Step 4: Generate response
        response_request = {
            "review_id": review_id,
            "response_type": "public",
            "tone": "empathetic",
        }
        response_response = await async_client.post(
            "/api/v1/reviews/respond", json=response_request, headers=auth_headers
        )
        assert response_response.status_code == 200
        response_result = response_response.json()

        # Verify response generation
        assert response_result["review_id"] == review_id
        assert response_result["response_type"] == "public"
        assert response_result["tone"] == "empathetic"
        assert len(response_result["response_content"]) > 0
        assert (
            response_result["requires_approval"] is True
        )  # Low rating should require approval

        # Step 5: Verify review can be retrieved with all data
        get_response = await async_client.get(
            f"/api/v1/reviews/{review_id}", headers=auth_headers
        )
        assert get_response.status_code == 200
        final_review = get_response.json()

        # Verify complete review data
        assert final_review["id"] == review_id
        assert final_review["processed"] is True
        assert final_review["sentiment_score"] is not None
        assert final_review["urgency_level"] is not None
        assert final_review["issue_categories"] is not None


class TestCustomerRecoveryWorkflow:
    """Test complete customer recovery workflow"""

    @pytest.mark.asyncio
    async def test_complete_customer_recovery_workflow(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: Dict[str, str],
        async_db: AsyncSession,
    ):
        """
        Test complete workflow: Customer risk assessment → Recovery recommendation → Action execution

        **Validates: Requirements 6.1, 6.2, 3.2**
        """
        # Step 1: Create a high-risk customer
        customer_data = {
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone": "+1234567890",
            "organization_id": str(test_organization.id),
            "churn_risk_score": 0.85,
            "bad_review_likelihood": 0.75,
            "risk_level": "high",
            "total_reviews": 5,
            "average_rating": 2.2,
            "support_tickets_count": 3,
            "last_interaction": datetime.utcnow() - timedelta(days=2),
        }

        customer = Customer(**customer_data)
        async_db.add(customer)
        await async_db.commit()
        await async_db.refresh(customer)

        # Step 2: Get customer risk assessment
        risk_response = await async_client.get(
            f"/api/v1/customers/{customer.id}/risk", headers=auth_headers
        )
        assert risk_response.status_code == 200
        risk_result = risk_response.json()

        # Verify risk assessment
        assert risk_result["customer_id"] == str(customer.id)
        assert risk_result["churn_risk"] >= 0.8
        assert risk_result["bad_review_likelihood"] >= 0.7
        assert risk_result["risk_level"] == "high"
        assert "risk_factors" in risk_result

        # Step 3: Initiate recovery process
        recovery_request = {
            "customer_id": str(customer.id),
            "trigger_context": {
                "trigger_type": "high_risk_detected",
                "risk_score": 0.85,
                "last_review_rating": 2,
            },
            "execute_immediately": False,
        }

        recovery_response = await async_client.post(
            "/api/v1/customers/recover", json=recovery_request, headers=auth_headers
        )
        assert recovery_response.status_code == 200
        recovery_result = recovery_response.json()

        # Verify recovery actions created
        assert recovery_result["customer_id"] == str(customer.id)
        assert recovery_result["recovery_actions_created"] > 0
        assert len(recovery_result["actions"]) > 0

        # Verify action details
        actions = recovery_result["actions"]
        action_types = [action["action_type"] for action in actions]
        assert any(
            action_type in ["email_outreach", "phone_call", "discount_offer"]
            for action_type in action_types
        )

        # Step 4: Get recovery actions for customer
        actions_response = await async_client.get(
            f"/api/v1/customers/{customer.id}/recovery-actions", headers=auth_headers
        )
        assert actions_response.status_code == 200
        actions_result = actions_response.json()

        # Verify actions retrieved
        assert actions_result["customer_id"] == str(customer.id)
        assert len(actions_result["recovery_actions"]) > 0

        # Step 5: Execute recovery with immediate execution
        immediate_recovery_request = {
            "customer_id": str(customer.id),
            "trigger_context": {
                "trigger_type": "manual_intervention",
                "urgency": "high",
            },
            "execute_immediately": True,
        }

        immediate_response = await async_client.post(
            "/api/v1/customers/recover",
            json=immediate_recovery_request,
            headers=auth_headers,
        )
        assert immediate_response.status_code == 200
        immediate_result = immediate_response.json()

        # Verify immediate execution
        assert immediate_result["executed_immediately"] >= 0
        if immediate_result["executed_immediately"] > 0:
            assert len(immediate_result["execution_results"]) > 0


class TestDashboardMetricsWorkflow:
    """Test complete dashboard metrics workflow"""

    @pytest.mark.asyncio
    async def test_complete_dashboard_metrics_workflow(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: Dict[str, str],
        async_db: AsyncSession,
    ):
        """
        Test complete workflow: Data creation → Metrics calculation → Dashboard display

        **Validates: Requirements 2.2, 3.1**
        """
        # Step 1: Create test data (reviews, customers, recovery actions)
        # Create multiple reviews with different ratings
        reviews_data = [
            {"rating": 5, "sentiment_score": 0.9, "platform": "google"},
            {"rating": 4, "sentiment_score": 0.7, "platform": "yelp"},
            {"rating": 2, "sentiment_score": 0.3, "platform": "google"},
            {"rating": 1, "sentiment_score": 0.1, "platform": "facebook"},
            {"rating": 3, "sentiment_score": 0.5, "platform": "yelp"},
        ]

        for i, review_data in enumerate(reviews_data):
            review = Review(
                id=uuid.uuid4(),
                organization_id=test_organization.id,
                platform=review_data["platform"],
                external_id=f"test_review_{i}",
                customer_name=f"Customer {i}",
                customer_email=f"customer{i}@example.com",
                title=f"Review {i}",
                content=f"Review content {i}",
                rating=review_data["rating"],
                sentiment_score=review_data["sentiment_score"],
                processed=True,
                review_date=datetime.utcnow() - timedelta(days=i),
                created_at=datetime.utcnow() - timedelta(days=i),
            )
            async_db.add(review)

        # Create customers with different risk levels
        customers_data = [
            {
                "churn_risk_score": 0.8,
                "bad_review_likelihood": 0.7,
                "risk_level": "high",
            },
            {
                "churn_risk_score": 0.6,
                "bad_review_likelihood": 0.5,
                "risk_level": "medium",
            },
            {
                "churn_risk_score": 0.3,
                "bad_review_likelihood": 0.2,
                "risk_level": "low",
            },
        ]

        for i, customer_data in enumerate(customers_data):
            customer = Customer(
                id=uuid.uuid4(),
                organization_id=test_organization.id,
                name=f"Customer {i}",
                email=f"customer{i}@example.com",
                churn_risk_score=customer_data["churn_risk_score"],
                bad_review_likelihood=customer_data["bad_review_likelihood"],
                risk_level=customer_data["risk_level"],
            )
            async_db.add(customer)

        await async_db.commit()

        # Step 2: Get comprehensive dashboard metrics
        metrics_response = await async_client.get(
            "/api/v1/dashboard/metrics?time_range=30d", headers=auth_headers
        )
        assert metrics_response.status_code == 200
        metrics_result = metrics_response.json()

        # Verify comprehensive metrics structure
        assert "kpis" in metrics_result
        assert "charts" in metrics_result
        assert "activity_feed" in metrics_result
        assert "alerts" in metrics_result

        # Verify KPIs
        kpis = metrics_result["kpis"]
        assert "average_rating" in kpis
        assert "monthly_reviews" in kpis
        assert "at_risk_customers" in kpis
        assert "recovery_success_rate" in kpis

        # Step 3: Get individual KPI details
        kpis_response = await async_client.get(
            "/api/v1/dashboard/kpis?time_range=30d", headers=auth_headers
        )
        assert kpis_response.status_code == 200
        kpis_result = kpis_response.json()

        # Verify KPI details
        assert kpis_result["time_range"] == "30d"
        assert "kpis" in kpis_result
        assert "generated_at" in kpis_result

        # Step 4: Get activity feed
        activity_response = await async_client.get(
            "/api/v1/dashboard/activity?limit=10", headers=auth_headers
        )
        assert activity_response.status_code == 200
        activity_result = activity_response.json()

        # Verify activity feed
        assert "activities" in activity_result
        assert "total_count" in activity_result
        assert activity_result["total_count"] >= 0

        # Step 5: Get trends data
        trends_response = await async_client.get(
            "/api/v1/dashboard/trends?time_range=30d", headers=auth_headers
        )
        assert trends_response.status_code == 200
        trends_result = trends_response.json()

        # Verify trends structure
        assert "trends" in trends_result
        assert "time_range" in trends_result
        assert trends_result["time_range"] == "30d"

        # Step 6: Get alerts
        alerts_response = await async_client.get(
            "/api/v1/dashboard/alerts", headers=auth_headers
        )
        assert alerts_response.status_code == 200
        alerts_result = alerts_response.json()

        # Verify alerts structure
        assert "alerts" in alerts_result
        assert "total_count" in alerts_result
        assert alerts_result["total_count"] >= 0


class TestMultiTenantWorkflow:
    """Test multi-tenant isolation workflow"""

    @pytest.mark.asyncio
    async def test_multi_tenant_data_isolation_workflow(
        self, async_client: AsyncClient, async_db: AsyncSession
    ):
        """
        Test complete workflow: Multiple organizations → Data isolation → Access control

        **Validates: Requirements 3.1, 3.2**
        """
        # Step 1: Create two organizations
        org1 = Organization(
            id=uuid.uuid4(),
            name="Organization 1",
            domain="org1.com",
            settings={"timezone": "UTC"},
        )
        org2 = Organization(
            id=uuid.uuid4(),
            name="Organization 2",
            domain="org2.com",
            settings={"timezone": "EST"},
        )

        async_db.add_all([org1, org2])
        await async_db.commit()

        # Step 2: Create users for each organization
        auth_service = AuthService()

        user1_data = {
            "email": "user1@org1.com",
            "password": "password123",
            "full_name": "User One",
            "organization_id": str(org1.id),
        }
        user1 = await auth_service.create_user(async_db, **user1_data)

        user2_data = {
            "email": "user2@org2.com",
            "password": "password123",
            "full_name": "User Two",
            "organization_id": str(org2.id),
        }
        user2 = await auth_service.create_user(async_db, **user2_data)

        # Step 3: Login both users and get tokens
        login1_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "user1@org1.com", "password": "password123"},
        )
        assert login1_response.status_code == 200
        token1 = login1_response.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        login2_response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "user2@org2.com", "password": "password123"},
        )
        assert login2_response.status_code == 200
        token2 = login2_response.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Step 4: Create data for each organization
        # Create review for org1
        review1_data = {
            "platform": "google",
            "external_id": "org1_review_1",
            "customer_name": "Org1 Customer",
            "customer_email": "customer@org1.com",
            "title": "Great service",
            "content": "Excellent experience",
            "rating": 5,
            "review_date": datetime.utcnow().isoformat(),
        }

        review1_response = await async_client.post(
            "/api/v1/reviews/ingest", json=review1_data, headers=headers1
        )
        assert review1_response.status_code == 200
        review1_id = review1_response.json()["id"]

        # Create review for org2
        review2_data = {
            "platform": "yelp",
            "external_id": "org2_review_1",
            "customer_name": "Org2 Customer",
            "customer_email": "customer@org2.com",
            "title": "Poor service",
            "content": "Bad experience",
            "rating": 2,
            "review_date": datetime.utcnow().isoformat(),
        }

        review2_response = await async_client.post(
            "/api/v1/reviews/ingest", json=review2_data, headers=headers2
        )
        assert review2_response.status_code == 200
        review2_id = review2_response.json()["id"]

        # Step 5: Verify data isolation - user1 cannot access org2 data
        org1_access_org2_review = await async_client.get(
            f"/api/v1/reviews/{review2_id}", headers=headers1
        )
        assert org1_access_org2_review.status_code == 404

        # Step 6: Verify data isolation - user2 cannot access org1 data
        org2_access_org1_review = await async_client.get(
            f"/api/v1/reviews/{review1_id}", headers=headers2
        )
        assert org2_access_org1_review.status_code == 404

        # Step 7: Verify users can access their own organization's data
        org1_access_own_review = await async_client.get(
            f"/api/v1/reviews/{review1_id}", headers=headers1
        )
        assert org1_access_own_review.status_code == 200
        assert org1_access_own_review.json()["id"] == review1_id

        org2_access_own_review = await async_client.get(
            f"/api/v1/reviews/{review2_id}", headers=headers2
        )
        assert org2_access_own_review.status_code == 200
        assert org2_access_own_review.json()["id"] == review2_id

        # Step 8: Verify dashboard metrics are isolated
        org1_metrics = await async_client.get(
            "/api/v1/dashboard/metrics", headers=headers1
        )
        assert org1_metrics.status_code == 200

        org2_metrics = await async_client.get(
            "/api/v1/dashboard/metrics", headers=headers2
        )
        assert org2_metrics.status_code == 200

        # Metrics should be different for each organization
        org1_data = org1_metrics.json()
        org2_data = org2_metrics.json()

        # They should have different review counts (1 each)
        assert org1_data["kpis"]["monthly_reviews"] == 1
        assert org2_data["kpis"]["monthly_reviews"] == 1

        # They should have different average ratings
        assert org1_data["kpis"]["average_rating"] == 5.0
        assert org2_data["kpis"]["average_rating"] == 2.0


class TestErrorHandlingWorkflow:
    """Test error handling across workflows"""

    @pytest.mark.asyncio
    async def test_error_handling_workflow(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: Dict[str, str],
    ):
        """
        Test error handling across different workflow scenarios

        **Validates: Requirements 1.2, 2.1, 4.1**
        """
        # Test 1: Invalid review data
        invalid_review_data = {
            "platform": "invalid_platform",
            "rating": 10,  # Invalid rating (should be 1-5)
            "content": "",  # Empty content
        }

        invalid_response = await async_client.post(
            "/api/v1/reviews/ingest", json=invalid_review_data, headers=auth_headers
        )
        assert invalid_response.status_code == 422  # Validation error

        # Test 2: Non-existent review analysis
        fake_review_id = str(uuid.uuid4())
        analysis_request = {"review_id": fake_review_id}

        analysis_response = await async_client.post(
            "/api/v1/reviews/analyze", json=analysis_request, headers=auth_headers
        )
        assert analysis_response.status_code == 404

        # Test 3: Non-existent customer recovery
        fake_customer_id = str(uuid.uuid4())
        recovery_request = {
            "customer_id": fake_customer_id,
            "execute_immediately": False,
        }

        recovery_response = await async_client.post(
            "/api/v1/customers/recover", json=recovery_request, headers=auth_headers
        )
        assert recovery_response.status_code == 404

        # Test 4: Invalid agent decision request
        invalid_agent_request = {"input_type": "invalid_type", "input_id": "invalid_id"}

        agent_response = await async_client.post(
            "/api/v1/agents/decide-action",
            json=invalid_agent_request,
            headers=auth_headers,
        )
        assert agent_response.status_code == 400

        # Test 5: Unauthorized access (no auth headers)
        no_auth_response = await async_client.get("/api/v1/dashboard/metrics")
        assert no_auth_response.status_code == 401


class TestPerformanceWorkflow:
    """Test performance aspects of workflows"""

    @pytest.mark.asyncio
    async def test_bulk_operations_performance(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: Dict[str, str],
        async_db: AsyncSession,
    ):
        """
        Test performance with bulk operations

        **Validates: Requirements 2.2, 4.2**
        """
        import time

        # Test 1: Bulk review ingestion performance
        start_time = time.time()

        review_ids = []
        for i in range(10):  # Create 10 reviews
            review_data = {
                "platform": "google",
                "external_id": f"bulk_review_{i}",
                "customer_name": f"Customer {i}",
                "customer_email": f"customer{i}@example.com",
                "title": f"Review {i}",
                "content": f"Review content {i} with some text to analyze",
                "rating": (i % 5) + 1,  # Ratings 1-5
                "review_date": datetime.utcnow().isoformat(),
            }

            response = await async_client.post(
                "/api/v1/reviews/ingest", json=review_data, headers=auth_headers
            )
            assert response.status_code == 200
            review_ids.append(response.json()["id"])

        ingestion_time = time.time() - start_time
        assert ingestion_time < 10.0  # Should complete within 10 seconds

        # Test 2: Bulk analysis performance
        start_time = time.time()

        for review_id in review_ids:
            analysis_request = {"review_id": review_id}
            response = await async_client.post(
                "/api/v1/reviews/analyze", json=analysis_request, headers=auth_headers
            )
            assert response.status_code == 200

            # Verify processing time is reasonable
            result = response.json()
            assert (
                result["processing_time_ms"] < 5000
            )  # Less than 5 seconds per analysis

        analysis_time = time.time() - start_time
        assert analysis_time < 30.0  # Should complete within 30 seconds for 10 reviews

        # Test 3: Dashboard metrics performance with data
        start_time = time.time()

        metrics_response = await async_client.get(
            "/api/v1/dashboard/metrics?time_range=30d", headers=auth_headers
        )
        assert metrics_response.status_code == 200

        metrics_time = time.time() - start_time
        assert metrics_time < 5.0  # Dashboard should load within 5 seconds

        # Test 4: Batch customer risk update performance
        # Create some customers first
        for i in range(5):
            customer = Customer(
                id=uuid.uuid4(),
                organization_id=test_organization.id,
                name=f"Bulk Customer {i}",
                email=f"bulk_customer{i}@example.com",
                churn_risk_score=0.5,
                bad_review_likelihood=0.4,
            )
            async_db.add(customer)

        await async_db.commit()

        start_time = time.time()

        batch_response = await async_client.post(
            "/api/v1/customers/batch-risk-update?limit=5", headers=auth_headers
        )
        assert batch_response.status_code == 200

        batch_time = time.time() - start_time
        assert batch_time < 10.0  # Batch update should complete within 10 seconds
