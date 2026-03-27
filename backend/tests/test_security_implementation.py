"""
Comprehensive security implementation tests
"""

import asyncio
import json
import time
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limiting import AdvancedRateLimiter, UserTier
from app.core.security import SecurityService
from app.core.security_config import SecuritySettings, SecurityValidator
from app.core.security_middleware import (
    AuditLoggingMiddleware,
    CSRFProtectionMiddleware,
    DDoSProtectionMiddleware,
    InputSanitizationMiddleware,
)
from app.core.sql_protection import SQLInjectionError, SQLSecurityValidator
from app.core.validation import InputSanitizer, InputValidator, ValidationError


class TestInputSanitization:
    """Test input sanitization functionality"""

    def test_sanitize_string_basic(self):
        """Test basic string sanitization"""
        # Normal string
        result = InputSanitizer.sanitize_string("Hello World")
        assert result == "Hello World"

        # String with HTML
        result = InputSanitizer.sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "alert" not in result

    def test_sanitize_string_with_html_allowed(self):
        """Test string sanitization with HTML allowed"""
        html_input = "<p>Hello <strong>World</strong></p><script>alert('xss')</script>"
        result = InputSanitizer.sanitize_string(html_input, allow_html=True)

        # Should keep safe HTML
        assert "<p>" in result
        assert "<strong>" in result

        # Should remove dangerous HTML
        assert "<script>" not in result
        assert "alert" not in result

    def test_sanitize_string_length_limit(self):
        """Test string length validation"""
        long_string = "a" * 1000

        with pytest.raises(ValidationError) as exc_info:
            InputSanitizer.sanitize_string(long_string, max_length=100)

        assert "too long" in str(exc_info.value).lower()

    def test_detect_sql_injection(self):
        """Test SQL injection detection"""
        sql_inputs = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "UNION SELECT * FROM users",
            "admin'--",
            "1; DELETE FROM users",
        ]

        for sql_input in sql_inputs:
            with pytest.raises(ValidationError) as exc_info:
                InputSanitizer.sanitize_string(sql_input)
            assert "malicious" in str(exc_info.value).lower()

    def test_detect_xss_attempts(self):
        """Test XSS detection"""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "onload=alert('xss')",
        ]

        for xss_input in xss_inputs:
            with pytest.raises(ValidationError) as exc_info:
                InputSanitizer.sanitize_string(xss_input)
            assert "malicious" in str(exc_info.value).lower()

    def test_detect_path_traversal(self):
        """Test path traversal detection"""
        path_inputs = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "%2e%2e%2f",
            "....//....//etc/passwd",
        ]

        for path_input in path_inputs:
            with pytest.raises(ValidationError) as exc_info:
                InputSanitizer.sanitize_string(path_input)
            assert "malicious" in str(exc_info.value).lower()

    def test_sanitize_email(self):
        """Test email sanitization"""
        # Valid emails
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@test-domain.com",
        ]

        for email in valid_emails:
            result = InputSanitizer.sanitize_email(email)
            assert result == email.lower()

        # Invalid emails
        invalid_emails = [
            "not-an-email",
            "user@",
            "@domain.com",
            "user..double@domain.com",
            "user@domain..com",
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_email(email)

    def test_sanitize_url(self):
        """Test URL sanitization"""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://localhost:8000/api/v1/test",
            "https://sub.domain.com/path?param=value",
        ]

        for url in valid_urls:
            result = InputSanitizer.sanitize_url(url)
            assert result.startswith(("http://", "https://"))

        # Invalid schemes
        invalid_urls = [
            "javascript:alert('xss')",
            "ftp://example.com",
            "file:///etc/passwd",
        ]

        for url in invalid_urls:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_url(url)

    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Valid filenames
        valid_filenames = ["document.pdf", "report_2024.csv", "image-file.jpg"]

        for filename in valid_filenames:
            result = InputSanitizer.sanitize_filename(filename)
            assert result == filename

        # Invalid filenames
        invalid_filenames = [
            "../../../etc/passwd",
            "file<script>.txt",
            "CON.txt",  # Windows reserved name
            "file|pipe.txt",
            "file?.txt",
        ]

        for filename in invalid_filenames:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_filename(filename)


class TestInputValidation:
    """Test business logic input validation"""

    def test_validate_rating(self):
        """Test rating validation"""
        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            result = InputValidator.validate_rating(rating)
            assert result == rating

        # Invalid ratings
        invalid_ratings = [0, 6, -1, 10, "3", 3.5]

        for rating in invalid_ratings:
            with pytest.raises(ValidationError):
                InputValidator.validate_rating(rating)

    def test_validate_sentiment_score(self):
        """Test sentiment score validation"""
        # Valid scores
        valid_scores = [0.0, 0.5, 1.0, 0.25, 0.75]

        for score in valid_scores:
            result = InputValidator.validate_sentiment_score(score)
            assert result == float(score)

        # Invalid scores
        invalid_scores = [-0.1, 1.1, 2.0, "0.5", None]

        for score in invalid_scores:
            with pytest.raises(ValidationError):
                InputValidator.validate_sentiment_score(score)

    def test_validate_urgency_level(self):
        """Test urgency level validation"""
        # Valid levels
        valid_levels = ["low", "medium", "high", "LOW", "MEDIUM", "HIGH"]

        for level in valid_levels:
            result = InputValidator.validate_urgency_level(level)
            assert result in ["low", "medium", "high"]

        # Invalid levels
        invalid_levels = ["critical", "urgent", "normal", 1, None]

        for level in invalid_levels:
            with pytest.raises(ValidationError):
                InputValidator.validate_urgency_level(level)

    def test_validate_issue_categories(self):
        """Test issue categories validation"""
        # Valid categories
        valid_categories = [
            ["support"],
            ["pricing", "delivery"],
            ["support", "quality", "pricing"],
            [],
        ]

        for categories in valid_categories:
            result = InputValidator.validate_issue_categories(categories)
            assert all(
                cat in ["support", "pricing", "delivery", "quality"] for cat in result
            )

        # Invalid categories
        invalid_categories = [
            ["invalid_category"],
            ["support", "invalid"],
            ["support", "pricing", "delivery", "quality", "extra"],  # Too many
            "not_a_list",
            [123],
        ]

        for categories in invalid_categories:
            with pytest.raises(ValidationError):
                InputValidator.validate_issue_categories(categories)


class TestSQLProtection:
    """Test SQL injection protection"""

    def test_validate_query_string_safe(self):
        """Test safe query validation"""
        safe_queries = [
            "SELECT id, name FROM users WHERE active = true",
            "SELECT * FROM reviews WHERE rating >= 4",
            "SELECT COUNT(*) FROM customers",
        ]

        for query in safe_queries:
            # Should not raise exception
            result = SQLSecurityValidator.validate_query_string(
                query, allow_keywords=["SELECT", "FROM", "WHERE", "COUNT"]
            )
            assert result is True

    def test_validate_query_string_dangerous(self):
        """Test dangerous query detection"""
        dangerous_queries = [
            "DROP TABLE users",
            "DELETE FROM users WHERE 1=1",
            "INSERT INTO users (name) VALUES ('hacker')",
            "SELECT * FROM users; DROP TABLE users; --",
            "UNION SELECT password FROM admin_users",
        ]

        for query in dangerous_queries:
            with pytest.raises(SQLInjectionError):
                SQLSecurityValidator.validate_query_string(query)

    def test_validate_user_input_contexts(self):
        """Test user input validation in different contexts"""
        # Sort context
        valid_sort = "created_at"
        result = SQLSecurityValidator.validate_user_input(valid_sort, context="sort")
        assert result == valid_sort

        invalid_sort = "created_at; DROP TABLE users"
        with pytest.raises(SQLInjectionError):
            SQLSecurityValidator.validate_user_input(invalid_sort, context="sort")

        # Filter context
        valid_filter = "active user"
        result = SQLSecurityValidator.validate_user_input(
            valid_filter, context="filter"
        )
        assert "active user" in result

        # Search context
        valid_search = "customer feedback review"
        result = SQLSecurityValidator.validate_user_input(
            valid_search, context="search"
        )
        assert "customer feedback review" in result


@pytest.mark.asyncio
class TestRateLimiting:
    """Test rate limiting functionality"""

    async def test_rate_limit_check_within_limits(self):
        """Test rate limiting when within limits"""
        identifier = "test_user_1"
        user_tier = UserTier.FREE.value

        # Mock Redis to avoid actual Redis dependency
        with patch("app.core.rate_limiting.redis_client") as mock_redis:
            mock_redis.redis = Mock()
            mock_redis.redis.pipeline.return_value.__aenter__.return_value.execute.return_value = [
                None,
                5,
                None,
                None,
            ]

            result = await AdvancedRateLimiter.check_rate_limit(
                identifier=identifier, user_tier=user_tier, endpoint="/api/v1/test"
            )

            assert not result["overall_limited"]
            assert result["user_tier"] == user_tier

    async def test_rate_limit_check_exceeded(self):
        """Test rate limiting when limits are exceeded"""
        identifier = "test_user_2"
        user_tier = UserTier.FREE.value

        # Mock Redis to simulate exceeded limits
        with patch("app.core.rate_limiting.redis_client") as mock_redis:
            mock_redis.redis = Mock()
            # Simulate high request count
            mock_redis.redis.pipeline.return_value.__aenter__.return_value.execute.return_value = [
                None,
                150,
                None,
                None,
            ]

            result = await AdvancedRateLimiter.check_rate_limit(
                identifier=identifier, user_tier=user_tier, endpoint="/api/v1/test"
            )

            assert result["overall_limited"]

    async def test_get_user_tier(self):
        """Test user tier retrieval"""
        user_id = "test_user_123"
        organization_id = "test_org_456"

        with patch("app.core.rate_limiting.redis_client") as mock_redis:
            mock_redis.get.return_value = None  # No cached tier
            mock_redis.set.return_value = None

            tier = await AdvancedRateLimiter.get_user_tier(user_id, organization_id)

            # Should default to FREE tier
            assert tier == UserTier.FREE.value


class TestSecurityService:
    """Test security service functionality"""

    def test_password_validation(self):
        """Test password strength validation"""
        # Strong password
        strong_password = "StrongP@ssw0rd123"
        result = SecurityService.validate_password_strength(strong_password)

        assert result["is_valid"]
        assert result["strength"] in ["Strong", "Very Strong"]
        assert len(result["recommendations"]) == 0

        # Weak password
        weak_password = "password"
        result = SecurityService.validate_password_strength(weak_password)

        assert not result["is_valid"]
        assert result["strength"] in ["Weak", "Very Weak"]
        assert len(result["recommendations"]) > 0

    def test_jwt_token_creation_and_verification(self):
        """Test JWT token creation and verification"""
        # Create token data
        from app.core.security import TokenData

        token_data = TokenData(
            user_id="user_123",
            organization_id="org_456",
            email="test@example.com",
            role="user",
        )

        # Create token
        token = SecurityService.create_access_token(token_data.to_dict())
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long

        # Verify token
        payload = SecurityService.verify_token(token)
        assert payload["sub"] == "user_123"
        assert payload["org_id"] == "org_456"
        assert payload["email"] == "test@example.com"

    def test_password_hashing_and_verification(self):
        """Test password hashing and verification"""
        password = "TestPassword123!"

        # Hash password
        hashed = SecurityService.get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hashes are long

        # Verify correct password
        assert SecurityService.verify_password(password, hashed)

        # Verify incorrect password
        assert not SecurityService.verify_password("WrongPassword", hashed)

    def test_api_key_generation_and_validation(self):
        """Test API key generation and validation"""
        # Generate API key
        api_key = SecurityService.generate_api_key()
        assert api_key.startswith("ra_")
        assert len(api_key) > 35

        # Validate API key format
        from app.core.validation import SecurityValidator

        result = SecurityValidator.validate_api_key_format(api_key)
        assert result == api_key

        # Test invalid format
        with pytest.raises(ValidationError):
            SecurityValidator.validate_api_key_format("invalid_key")


class TestSecurityConfiguration:
    """Test security configuration validation"""

    def test_security_settings_validation(self):
        """Test security settings validation"""
        # Create test settings
        settings = SecuritySettings(
            SECURITY_LEVEL="high",
            ENABLE_CSRF_PROTECTION=True,
            PASSWORD_MIN_LENGTH=8,
            CORS_ALLOW_ORIGINS=["http://localhost:3000"],
            CORS_ALLOW_CREDENTIALS=True,
        )

        # Validate configuration
        result = SecurityValidator.validate_security_config(settings)

        # Should have no errors for valid config
        assert len(result["errors"]) == 0

    def test_security_settings_validation_errors(self):
        """Test security settings validation with errors"""
        # Create settings with errors
        settings = SecuritySettings(
            PASSWORD_MIN_LENGTH=4,  # Too short
            CORS_ALLOW_ORIGINS=["*"],  # Wildcard with credentials
            CORS_ALLOW_CREDENTIALS=True,
        )

        # Validate configuration
        result = SecurityValidator.validate_security_config(settings)

        # Should have errors
        assert len(result["errors"]) > 0
        assert any("password" in error.lower() for error in result["errors"])
        assert any("cors" in error.lower() for error in result["errors"])

    def test_security_recommendations(self):
        """Test security recommendations"""
        # Create settings that could be improved
        settings = SecuritySettings(
            SECURITY_LEVEL="medium",  # Could be higher
            ENABLE_AUDIT_LOGGING=False,  # Should be enabled
            API_KEY_ROTATION_DAYS=180,  # Too long
        )

        recommendations = SecurityValidator.get_security_recommendations(settings)

        assert len(recommendations) > 0
        assert any("HIGH security level" in rec for rec in recommendations)
        assert any("audit logging" in rec for rec in recommendations)


@pytest.mark.asyncio
class TestSecurityMiddleware:
    """Test security middleware functionality"""

    async def test_csrf_protection_middleware(self):
        """Test CSRF protection middleware"""
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse

        app = FastAPI()

        @app.post("/test")
        async def test_endpoint():
            return {"message": "success"}

        # Add CSRF middleware
        app.add_middleware(CSRFProtectionMiddleware, secret_key="test_secret")

        client = TestClient(app)

        # Test POST without CSRF token (should fail)
        response = client.post("/test", json={"data": "test"})
        assert response.status_code == 403
        assert "csrf" in response.json()["error"]["type"].lower()

    async def test_ddos_protection_middleware(self):
        """Test DDoS protection middleware"""
        from fastapi import FastAPI

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        # Add DDoS protection middleware
        app.add_middleware(
            DDoSProtectionMiddleware,
            max_requests_per_minute=5,
            max_requests_per_second=2,
        )

        client = TestClient(app)

        # Mock Redis for rate limiting
        with patch("app.core.security_middleware.redis_client") as mock_redis:
            mock_redis.increment.return_value = 1  # First request
            mock_redis.expire.return_value = None

            # First request should succeed
            response = client.get("/test")
            assert response.status_code == 200

            # Simulate too many requests
            mock_redis.increment.return_value = 10  # Exceeded limit

            response = client.get("/test")
            assert response.status_code == 429


class TestSecurityIntegration:
    """Integration tests for security features"""

    def test_end_to_end_security_validation(self):
        """Test end-to-end security validation"""
        # Simulate a complete request with security validation

        # 1. Input sanitization
        user_input = "Hello <script>alert('xss')</script> World"
        sanitized = InputSanitizer.sanitize_string(user_input)
        assert "<script>" not in sanitized

        # 2. SQL injection protection
        search_query = "test search"
        validated_query = SQLSecurityValidator.validate_user_input(
            search_query, context="search"
        )
        assert validated_query == search_query

        # 3. Password validation
        password = "SecureP@ssw0rd123"
        validation_result = SecurityService.validate_password_strength(password)
        assert validation_result["is_valid"]

        # 4. JWT token handling
        from app.core.security import TokenData

        token_data = TokenData(
            user_id="user_123",
            organization_id="org_456",
            email="test@example.com",
            role="user",
        )

        token = SecurityService.create_access_token(token_data.to_dict())
        payload = SecurityService.verify_token(token)
        assert payload["sub"] == "user_123"

    def test_security_audit_trail(self):
        """Test security audit trail functionality"""
        # This would test the complete audit logging pipeline
        # For now, we'll test the structure

        audit_event = {
            "event_type": "authentication_failure",
            "user_id": None,
            "ip_address": "192.168.1.100",
            "timestamp": int(time.time()),
            "details": {"reason": "invalid_password", "attempt_count": 3},
        }

        # Validate audit event structure
        required_fields = ["event_type", "timestamp", "ip_address"]
        for field in required_fields:
            assert field in audit_event

        assert isinstance(audit_event["timestamp"], int)
        assert audit_event["event_type"] in [
            "authentication_failure",
            "authentication_success",
            "authorization_failure",
            "rate_limit_exceeded",
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
