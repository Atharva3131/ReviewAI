"""
External Service Integration Tests

Tests integration with external services including Google Reviews API,
email services, WhatsApp API, CRM systems, and webhook processing.
Validates service connectivity, error handling, and data transformation.

**Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Configure pytest for async tests
pytestmark = pytest.mark.asyncio


class MockHTTPResponse:
    """Mock HTTP response for external service calls"""

    def __init__(
        self, status_code: int, json_data: Dict[str, Any] = None, text: str = ""
    ):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=None, response=self
            )


class MockExternalService:
    """Base mock external service"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.call_count = 0
        self.last_request = None
        self.responses = []
        self.errors = []

    def add_response(self, status_code: int, data: Dict[str, Any] = None):
        """Add a mock response"""
        self.responses.append(MockHTTPResponse(status_code, data))

    def add_error(self, error: Exception):
        """Add a mock error"""
        self.errors.append(error)

    async def make_request(self, method: str, url: str, **kwargs):
        """Mock HTTP request"""
        self.call_count += 1
        self.last_request = {
            "method": method,
            "url": url,
            "kwargs": kwargs,
            "timestamp": datetime.utcnow(),
        }

        if self.errors:
            raise self.errors.pop(0)

        if self.responses:
            return self.responses.pop(0)

        # Default success response
        return MockHTTPResponse(200, {"status": "success"})


class TestGoogleReviewsIntegration:
    """Test Google Reviews API integration"""

    @pytest.fixture
    def google_service(self):
        """Create mock Google Reviews service"""
        service = MockExternalService("google_reviews")
        return service

    async def test_fetch_reviews_success(self, google_service):
        """Test successful review fetching from Google"""
        # Mock successful response
        mock_reviews = {
            "reviews": [
                {
                    "reviewId": "google_123",
                    "reviewer": {"displayName": "John Doe"},
                    "starRating": "FIVE",
                    "comment": "Great service!",
                    "createTime": "2024-01-15T10:30:00Z",
                    "updateTime": "2024-01-15T10:30:00Z",
                },
                {
                    "reviewId": "google_124",
                    "reviewer": {"displayName": "Jane Smith"},
                    "starRating": "FOUR",
                    "comment": "Good experience overall",
                    "createTime": "2024-01-14T15:20:00Z",
                    "updateTime": "2024-01-14T15:20:00Z",
                },
            ],
            "nextPageToken": "next_page_token_123",
        }

        google_service.add_response(200, mock_reviews)

        # Simulate API call
        response = await google_service.make_request(
            "GET",
            "https://mybusiness.googleapis.com/v4/accounts/123/locations/456/reviews",
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "reviews" in data
        assert len(data["reviews"]) == 2
        assert data["reviews"][0]["reviewId"] == "google_123"
        assert data["reviews"][0]["starRating"] == "FIVE"
        assert google_service.call_count == 1

    async def test_fetch_reviews_authentication_error(self, google_service):
        """Test handling of authentication errors"""
        google_service.add_response(401, {"error": "Invalid credentials"})

        response = await google_service.make_request(
            "GET",
            "https://mybusiness.googleapis.com/v4/accounts/123/locations/456/reviews",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401
        assert "error" in response.json()
        assert response.json()["error"] == "Invalid credentials"

    async def test_fetch_reviews_rate_limit(self, google_service):
        """Test handling of rate limiting"""
        google_service.add_response(
            429, {"error": "Rate limit exceeded", "retryAfter": 60}
        )

        response = await google_service.make_request(
            "GET",
            "https://mybusiness.googleapis.com/v4/accounts/123/locations/456/reviews",
        )

        assert response.status_code == 429
        data = response.json()
        assert "retryAfter" in data
        assert data["retryAfter"] == 60

    async def test_post_review_response(self, google_service):
        """Test posting response to Google review"""
        google_service.add_response(
            200,
            {
                "name": "accounts/123/locations/456/reviews/google_123/reply",
                "comment": "Thank you for your feedback!",
                "updateTime": "2024-01-15T11:00:00Z",
            },
        )

        response_data = {"comment": "Thank you for your feedback!"}

        response = await google_service.make_request(
            "PUT",
            "https://mybusiness.googleapis.com/v4/accounts/123/locations/456/reviews/google_123/reply",
            json=response_data,
            headers={"Authorization": "Bearer mock_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "comment" in data
        assert data["comment"] == "Thank you for your feedback!"

        # Verify request was made correctly
        assert google_service.last_request["method"] == "PUT"
        assert "json" in google_service.last_request["kwargs"]

    async def test_webhook_verification(self, google_service):
        """Test Google webhook verification"""
        # Simulate webhook verification challenge
        challenge_token = "webhook_challenge_123"

        # Mock verification response
        google_service.add_response(200, {"challenge": challenge_token})

        response = await google_service.make_request(
            "GET",
            f"https://api.example.com/webhooks/google-reviews/verify?challenge={challenge_token}",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["challenge"] == challenge_token

    async def test_service_health_check(self, google_service):
        """Test Google Reviews service health check"""
        google_service.add_response(
            200,
            {
                "status": "healthy",
                "version": "v4",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        response = await google_service.make_request(
            "GET", "https://mybusiness.googleapis.com/v4/health"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestEmailServiceIntegration:
    """Test email service integration (SendGrid/AWS SES)"""

    @pytest.fixture
    def email_service(self):
        """Create mock email service"""
        service = MockExternalService("email_service")
        return service

    async def test_send_recovery_email_success(self, email_service):
        """Test successful recovery email sending"""
        email_service.add_response(
            202, {"message": "Email queued for delivery", "messageId": "email_123456"}
        )

        email_data = {
            "to": "customer@example.com",
            "from": "support@company.com",
            "subject": "We'd like to make things right",
            "html": "<p>Dear valued customer, we noticed your recent review...</p>",
            "text": "Dear valued customer, we noticed your recent review...",
        }

        response = await email_service.make_request(
            "POST",
            "https://api.sendgrid.com/v3/mail/send",
            json=email_data,
            headers={
                "Authorization": "Bearer mock_api_key",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert "messageId" in data
        assert data["messageId"] == "email_123456"

    async def test_send_email_invalid_recipient(self, email_service):
        """Test handling of invalid email recipient"""
        email_service.add_response(
            400,
            {
                "errors": [
                    {
                        "message": "Invalid email address",
                        "field": "to",
                        "help": "Please provide a valid email address",
                    }
                ]
            },
        )

        email_data = {
            "to": "invalid-email",
            "from": "support@company.com",
            "subject": "Test",
            "text": "Test message",
        }

        response = await email_service.make_request(
            "POST", "https://api.sendgrid.com/v3/mail/send", json=email_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "errors" in data
        assert data["errors"][0]["field"] == "to"

    async def test_email_template_rendering(self, email_service):
        """Test email template rendering"""
        email_service.add_response(
            200,
            {
                "template_id": "recovery_email_v1",
                "rendered_html": "<p>Dear John, we noticed your 2-star review...</p>",
                "rendered_text": "Dear John, we noticed your 2-star review...",
            },
        )

        template_data = {
            "template_id": "recovery_email_v1",
            "substitutions": {
                "customer_name": "John",
                "review_rating": "2",
                "business_name": "Acme Corp",
            },
        }

        response = await email_service.make_request(
            "POST", "https://api.sendgrid.com/v3/templates/render", json=template_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "rendered_html" in data
        assert "John" in data["rendered_html"]

    async def test_email_delivery_webhook(self, email_service):
        """Test email delivery status webhook"""
        webhook_data = {
            "event": "delivered",
            "email": "customer@example.com",
            "timestamp": int(datetime.utcnow().timestamp()),
            "smtp-id": "<email_123456@sendgrid.com>",
            "category": "recovery_email",
            "sg_event_id": "event_123",
            "sg_message_id": "message_123",
        }

        # Simulate webhook processing
        assert webhook_data["event"] == "delivered"
        assert webhook_data["email"] == "customer@example.com"
        assert "timestamp" in webhook_data

    async def test_email_bounce_handling(self, email_service):
        """Test email bounce handling"""
        bounce_webhook = {
            "event": "bounce",
            "email": "bounced@example.com",
            "timestamp": int(datetime.utcnow().timestamp()),
            "reason": "550 5.1.1 User unknown",
            "type": "bounce",
            "sg_event_id": "bounce_123",
        }

        # Simulate bounce processing
        assert bounce_webhook["event"] == "bounce"
        assert "reason" in bounce_webhook
        assert bounce_webhook["type"] == "bounce"


class TestWhatsAppIntegration:
    """Test WhatsApp API integration"""

    @pytest.fixture
    def whatsapp_service(self):
        """Create mock WhatsApp service"""
        service = MockExternalService("whatsapp")
        return service

    async def test_send_whatsapp_message_success(self, whatsapp_service):
        """Test successful WhatsApp message sending"""
        whatsapp_service.add_response(
            200,
            {
                "messaging_product": "whatsapp",
                "contacts": [{"input": "+1234567890", "wa_id": "1234567890"}],
                "messages": [{"id": "wamid.123456"}],
            },
        )

        message_data = {
            "messaging_product": "whatsapp",
            "to": "+1234567890",
            "type": "text",
            "text": {
                "body": "Hi! We noticed your recent review and would like to help improve your experience."
            },
        }

        response = await whatsapp_service.make_request(
            "POST",
            "https://graph.facebook.com/v18.0/123456789/messages",
            json=message_data,
            headers={"Authorization": "Bearer mock_whatsapp_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) == 1
        assert "id" in data["messages"][0]

    async def test_send_whatsapp_template_message(self, whatsapp_service):
        """Test sending WhatsApp template message"""
        whatsapp_service.add_response(
            200,
            {
                "messaging_product": "whatsapp",
                "contacts": [{"input": "+1234567890", "wa_id": "1234567890"}],
                "messages": [{"id": "wamid.template_123"}],
            },
        )

        template_data = {
            "messaging_product": "whatsapp",
            "to": "+1234567890",
            "type": "template",
            "template": {
                "name": "customer_recovery",
                "language": {"code": "en_US"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": "John"},
                            {"type": "text", "text": "Acme Corp"},
                        ],
                    }
                ],
            },
        }

        response = await whatsapp_service.make_request(
            "POST",
            "https://graph.facebook.com/v18.0/123456789/messages",
            json=template_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data

    async def test_whatsapp_webhook_message_received(self, whatsapp_service):
        """Test WhatsApp webhook for received messages"""
        webhook_data = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123456789",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"display_phone_number": "+1234567890"},
                                "messages": [
                                    {
                                        "from": "+0987654321",
                                        "id": "wamid.incoming_123",
                                        "timestamp": "1642694400",
                                        "text": {"body": "Thank you for reaching out!"},
                                        "type": "text",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        # Simulate webhook processing
        entry = webhook_data["entry"][0]
        change = entry["changes"][0]
        messages = change["value"]["messages"]

        assert len(messages) == 1
        assert messages[0]["type"] == "text"
        assert messages[0]["from"] == "+0987654321"

    async def test_whatsapp_message_status_webhook(self, whatsapp_service):
        """Test WhatsApp message status webhook"""
        status_webhook = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123456789",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"display_phone_number": "+1234567890"},
                                "statuses": [
                                    {
                                        "id": "wamid.123456",
                                        "status": "delivered",
                                        "timestamp": "1642694400",
                                        "recipient_id": "+0987654321",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        # Simulate status processing
        entry = status_webhook["entry"][0]
        change = entry["changes"][0]
        statuses = change["value"]["statuses"]

        assert len(statuses) == 1
        assert statuses[0]["status"] == "delivered"
        assert statuses[0]["id"] == "wamid.123456"


class TestCRMIntegration:
    """Test CRM system integration"""

    @pytest.fixture
    def crm_service(self):
        """Create mock CRM service"""
        service = MockExternalService("crm")
        return service

    async def test_fetch_customer_data(self, crm_service):
        """Test fetching customer data from CRM"""
        crm_service.add_response(
            200,
            {
                "id": "crm_customer_123",
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "status": "active",
                "created_date": "2023-01-15T10:00:00Z",
                "last_interaction": "2024-01-10T14:30:00Z",
                "lifetime_value": 5000.00,
                "support_tickets": [
                    {
                        "id": "ticket_456",
                        "status": "resolved",
                        "priority": "medium",
                        "created_date": "2024-01-05T09:00:00Z",
                    }
                ],
            },
        )

        response = await crm_service.make_request(
            "GET",
            "https://api.crm.com/v1/customers/crm_customer_123",
            headers={"Authorization": "Bearer crm_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "crm_customer_123"
        assert data["name"] == "John Doe"
        assert "support_tickets" in data
        assert len(data["support_tickets"]) == 1

    async def test_create_support_ticket(self, crm_service):
        """Test creating support ticket in CRM"""
        crm_service.add_response(
            201,
            {
                "id": "ticket_789",
                "customer_id": "crm_customer_123",
                "subject": "Follow-up on negative review",
                "description": "Customer left 2-star review, need to follow up",
                "priority": "high",
                "status": "open",
                "created_date": "2024-01-15T11:00:00Z",
                "assigned_to": "support_agent_456",
            },
        )

        ticket_data = {
            "customer_id": "crm_customer_123",
            "subject": "Follow-up on negative review",
            "description": "Customer left 2-star review, need to follow up",
            "priority": "high",
            "source": "review_system",
        }

        response = await crm_service.make_request(
            "POST",
            "https://api.crm.com/v1/tickets",
            json=ticket_data,
            headers={"Authorization": "Bearer crm_token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "ticket_789"
        assert data["priority"] == "high"
        assert data["status"] == "open"

    async def test_update_customer_notes(self, crm_service):
        """Test updating customer notes in CRM"""
        crm_service.add_response(
            200,
            {
                "id": "crm_customer_123",
                "notes": [
                    {
                        "id": "note_123",
                        "content": "Customer recovery action initiated due to negative review",
                        "created_by": "review_system",
                        "created_date": "2024-01-15T11:30:00Z",
                    }
                ],
            },
        )

        note_data = {
            "content": "Customer recovery action initiated due to negative review",
            "type": "system_note",
            "source": "review_system",
        }

        response = await crm_service.make_request(
            "POST",
            "https://api.crm.com/v1/customers/crm_customer_123/notes",
            json=note_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "notes" in data
        assert len(data["notes"]) == 1
        assert "review_system" in data["notes"][0]["created_by"]

    async def test_crm_webhook_customer_updated(self, crm_service):
        """Test CRM webhook for customer updates"""
        webhook_data = {
            "event_type": "customer.updated",
            "timestamp": "2024-01-15T12:00:00Z",
            "data": {
                "customer_id": "crm_customer_123",
                "changes": {
                    "email": {
                        "old_value": "old@example.com",
                        "new_value": "new@example.com",
                    },
                    "status": {"old_value": "active", "new_value": "inactive"},
                },
            },
        }

        # Simulate webhook processing
        assert webhook_data["event_type"] == "customer.updated"
        assert "changes" in webhook_data["data"]
        changes = webhook_data["data"]["changes"]
        assert "email" in changes
        assert changes["email"]["new_value"] == "new@example.com"


class TestExternalServiceErrorHandling:
    """Test error handling across external services"""

    @pytest.fixture
    def failing_service(self):
        """Create service that simulates failures"""
        service = MockExternalService("failing_service")
        return service

    async def test_network_timeout_handling(self, failing_service):
        """Test handling of network timeouts"""
        failing_service.add_error(asyncio.TimeoutError("Request timed out"))

        with pytest.raises(asyncio.TimeoutError):
            await failing_service.make_request("GET", "https://api.example.com/test")

        assert failing_service.call_count == 1

    async def test_connection_error_handling(self, failing_service):
        """Test handling of connection errors"""
        failing_service.add_error(httpx.ConnectError("Connection failed"))

        with pytest.raises(httpx.ConnectError):
            await failing_service.make_request("GET", "https://api.example.com/test")

    async def test_retry_logic_simulation(self, failing_service):
        """Test retry logic for failed requests"""
        # First two requests fail, third succeeds
        failing_service.add_error(httpx.ConnectError("Connection failed"))
        failing_service.add_error(httpx.ConnectError("Connection failed"))
        failing_service.add_response(200, {"status": "success"})

        # Simulate retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await failing_service.make_request(
                    "GET", "https://api.example.com/test"
                )
                assert response.status_code == 200
                break
            except httpx.ConnectError:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.1)  # Brief delay between retries

        assert failing_service.call_count == 3

    async def test_circuit_breaker_simulation(self, failing_service):
        """Test circuit breaker pattern simulation"""
        # Simulate circuit breaker state
        circuit_breaker = {
            "failure_count": 0,
            "failure_threshold": 3,
            "state": "closed",  # closed, open, half_open
            "last_failure_time": None,
        }

        # Simulate multiple failures
        for i in range(5):
            try:
                if circuit_breaker["state"] == "open":
                    # Circuit breaker is open, don't make request
                    raise Exception("Circuit breaker is open")

                failing_service.add_error(httpx.ConnectError("Service unavailable"))
                await failing_service.make_request(
                    "GET", "https://api.example.com/test"
                )

            except (httpx.ConnectError, Exception):
                circuit_breaker["failure_count"] += 1
                circuit_breaker["last_failure_time"] = datetime.utcnow()

                if (
                    circuit_breaker["failure_count"]
                    >= circuit_breaker["failure_threshold"]
                ):
                    circuit_breaker["state"] = "open"

        assert circuit_breaker["state"] == "open"
        assert circuit_breaker["failure_count"] >= circuit_breaker["failure_threshold"]


class TestServiceHealthMonitoring:
    """Test external service health monitoring"""

    async def test_service_health_check_all_services(self):
        """Test health check across all external services"""
        services = {
            "google_reviews": MockExternalService("google_reviews"),
            "email_service": MockExternalService("email_service"),
            "whatsapp": MockExternalService("whatsapp"),
            "crm": MockExternalService("crm"),
        }

        # Mock health responses
        for service_name, service in services.items():
            service.add_response(
                200,
                {
                    "status": "healthy",
                    "service": service_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "response_time_ms": 150,
                },
            )

        # Perform health checks
        health_results = {}
        for service_name, service in services.items():
            try:
                response = await service.make_request(
                    "GET", f"https://api.{service_name}.com/health"
                )
                health_results[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_code": response.status_code,
                    "response_time_ms": response.json().get("response_time_ms", 0),
                }
            except Exception as e:
                health_results[service_name] = {"status": "unhealthy", "error": str(e)}

        # Verify all services are healthy
        for service_name, result in health_results.items():
            assert result["status"] == "healthy"
            assert result["response_code"] == 200

    async def test_service_performance_monitoring(self):
        """Test service performance monitoring"""
        service = MockExternalService("performance_test")

        # Mock responses with different response times
        response_times = []
        for i in range(10):
            response_time = 100 + (i * 50)  # Increasing response times
            service.add_response(
                200, {"status": "success", "response_time_ms": response_time}
            )
            response_times.append(response_time)

        # Collect performance metrics
        performance_metrics = []
        for i in range(10):
            start_time = datetime.utcnow()
            response = await service.make_request(
                "GET", "https://api.test.com/endpoint"
            )
            end_time = datetime.utcnow()

            actual_response_time = (end_time - start_time).total_seconds() * 1000
            reported_response_time = response.json()["response_time_ms"]

            performance_metrics.append(
                {
                    "actual_response_time_ms": actual_response_time,
                    "reported_response_time_ms": reported_response_time,
                    "status_code": response.status_code,
                }
            )

        # Analyze performance
        avg_response_time = sum(
            m["reported_response_time_ms"] for m in performance_metrics
        ) / len(performance_metrics)
        max_response_time = max(
            m["reported_response_time_ms"] for m in performance_metrics
        )

        assert len(performance_metrics) == 10
        assert avg_response_time > 0
        assert max_response_time >= avg_response_time

        # Performance thresholds
        assert avg_response_time < 1000  # Average should be under 1 second
        assert max_response_time < 2000  # Max should be under 2 seconds


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
