"""
Automated security tests for penetration testing and vulnerability assessment
"""

import asyncio
import hashlib
import hmac
from datetime import datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.rate_limiting import AdvancedRateLimiter, UserTier
from app.core.security import SecurityAuditLog, SecurityService
from app.core.sql_protection import SQLInjectionError, SQLSecurityValidator
from app.core.validation import InputSanitizer, ValidationError
from app.main import app

client = TestClient(app)


class TestAuthenticationSecurity:
    """Test authentication security controls"""

    def test_jwt_token_manipulation(self):
        """Test that manipulated JWT tokens are rejected"""
        # Create a valid token
        token_data = {
            "sub": "user123",
            "org_id": "org123",
            "email": "test@example.com",
            "role": "user",
        }
        token = SecurityService.create_access_token(token_data)

        # Try to manipulate the token
        parts = token.split(".")

        # Manipulate payload
        manipulated_token = parts[0] + ".eyJzdWIiOiJhZG1pbiJ9." + parts[2]

        with pytest.raises(Exception):
            SecurityService.verify_token(manipulated_token)

    def test_expired_token_rejection(self):
        """Test that expired tokens are rejected"""
        token_data = {"sub": "user123", "org_id": "org123"}

        # Create token with immediate expiration
        token = SecurityService.create_access_token(
            token_data, expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(Exception):
            SecurityService.verify_token(token)

    def test_password_timing_attack_protection(self):
        """Test that password verification is protected against timing attacks"""
        import time

        password = "SecurePassword123!"
        hashed = SecurityService.get_password_hash(password)

        # Measure time for correct password
        start = time.perf_counter()
        SecurityService.verify_password(password, hashed)
        correct_time = time.perf_counter() - start

        # Measure time for incorrect password
        start = time.perf_counter()
        SecurityService.verify_password("WrongPassword", hashed)
        incorrect_time = time.perf_counter() - start

        # Times should be similar (within 10ms)
        time_diff = abs(correct_time - incorrect_time)
        assert time_diff < 0.01, "Timing attack vulnerability detected"

    def test_weak_password_rejection(self):
        """Test that weak passwords are rejected"""
        weak_passwords = ["password", "123456", "password123", "admin", "qwerty"]

        for weak_pwd in weak_passwords:
            result = SecurityService.validate_password_strength(weak_pwd)
            assert not result["is_valid"], f"Weak password accepted: {weak_pwd}"

    def test_password_strength_requirements(self):
        """Test password strength validation"""
        # Too short
        result = SecurityService.validate_password_strength("Short1!")
        assert not result["is_valid"]

        # No uppercase
        result = SecurityService.validate_password_strength("lowercase123!")
        assert not result["is_valid"]

        # No lowercase
        result = SecurityService.validate_password_strength("UPPERCASE123!")
        assert not result["is_valid"]

        # No digit
        result = SecurityService.validate_password_strength("NoDigits!")
        assert not result["is_valid"]

        # Valid strong password
        result = SecurityService.validate_password_strength("SecurePass123!")
        assert result["is_valid"]
        assert result["strength"] in ["Strong", "Very Strong"]


class TestSQLInjectionProtection:
    """Test SQL injection protection"""

    def test_union_based_injection(self):
        """Test protection against UNION-based SQL injection"""
        malicious_inputs = [
            "' UNION SELECT * FROM users--",
            "1' UNION SELECT password FROM users--",
            "admin' UNION ALL SELECT NULL,NULL,NULL--",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(SQLInjectionError):
                SQLSecurityValidator.validate_user_input(malicious_input)

    def test_boolean_based_injection(self):
        """Test protection against boolean-based SQL injection"""
        malicious_inputs = [
            "' OR '1'='1",
            "' OR 1=1--",
            "admin' OR '1'='1'--",
            "' AND 1=1--",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(SQLInjectionError):
                SQLSecurityValidator.validate_user_input(malicious_input)

    def test_time_based_injection(self):
        """Test protection against time-based SQL injection"""
        malicious_inputs = [
            "'; WAITFOR DELAY '00:00:05'--",
            "' AND SLEEP(5)--",
            "1' AND BENCHMARK(5000000,MD5('test'))--",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(SQLInjectionError):
                SQLSecurityValidator.validate_user_input(malicious_input)

    def test_stacked_queries(self):
        """Test protection against stacked queries"""
        malicious_inputs = [
            "'; DROP TABLE users--",
            "1'; DELETE FROM users WHERE '1'='1",
            "admin'; UPDATE users SET role='admin'--",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(SQLInjectionError):
                SQLSecurityValidator.validate_user_input(malicious_input)

    def test_information_schema_access(self):
        """Test protection against information schema access"""
        malicious_inputs = [
            "' UNION SELECT table_name FROM information_schema.tables--",
            "' AND 1=0 UNION SELECT NULL,table_name FROM information_schema.tables--",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(SQLInjectionError):
                SQLSecurityValidator.validate_user_input(malicious_input)


class TestXSSProtection:
    """Test XSS protection"""

    def test_script_tag_injection(self):
        """Test protection against script tag injection"""
        malicious_inputs = [
            "<script>alert('XSS')</script>",
            "<script src='http://evil.com/xss.js'></script>",
            "<SCRIPT>alert('XSS')</SCRIPT>",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_string(malicious_input)

    def test_event_handler_injection(self):
        """Test protection against event handler injection"""
        malicious_inputs = [
            "<img src=x onerror=alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<div onclick=alert('XSS')>Click me</div>",
            "<input onfocus=alert('XSS') autofocus>",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_string(malicious_input)

    def test_javascript_protocol(self):
        """Test protection against javascript: protocol"""
        malicious_inputs = [
            "<a href='javascript:alert(\"XSS\")'>Click</a>",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_string(malicious_input)

    def test_html_sanitization(self):
        """Test HTML sanitization with allowed tags"""
        # Safe HTML should be allowed
        safe_html = "<p>This is <strong>safe</strong> content</p>"
        sanitized = InputSanitizer.sanitize_string(safe_html, allow_html=True)
        assert "<p>" in sanitized
        assert "<strong>" in sanitized

        # Dangerous HTML should be stripped
        dangerous_html = "<p>Safe</p><script>alert('XSS')</script>"
        sanitized = InputSanitizer.sanitize_string(dangerous_html, allow_html=True)
        assert "<script>" not in sanitized
        assert "alert" not in sanitized


class TestPathTraversalProtection:
    """Test path traversal protection"""

    def test_directory_traversal(self):
        """Test protection against directory traversal"""
        malicious_inputs = [
            "../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "....//....//etc/passwd",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_filename(malicious_input)

    def test_url_encoded_traversal(self):
        """Test protection against URL-encoded traversal"""
        malicious_inputs = ["%2e%2e%2f%2e%2e%2fetc%2fpasswd", "..%2f..%2fetc%2fpasswd"]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_string(malicious_input)

    def test_reserved_filenames(self):
        """Test protection against Windows reserved filenames"""
        reserved_names = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]

        for reserved_name in reserved_names:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_filename(reserved_name)


class TestCSRFProtection:
    """Test CSRF protection"""

    def test_csrf_token_required_for_post(self):
        """Test that POST requests require CSRF token"""
        response = client.post(
            "/api/v1/reviews/ingest",
            json={"platform": "google", "rating": 5},
            headers={"Authorization": "Bearer valid_token"},
        )

        # Should fail without CSRF token
        assert response.status_code in [403, 401]

    def test_csrf_token_validation(self):
        """Test CSRF token validation"""
        # Invalid token should be rejected
        response = client.post(
            "/api/v1/reviews/ingest",
            json={"platform": "google", "rating": 5},
            headers={
                "Authorization": "Bearer valid_token",
                "X-CSRF-Token": "invalid_token",
            },
        )

        assert response.status_code in [403, 401]

    def test_safe_methods_no_csrf(self):
        """Test that safe methods don't require CSRF token"""
        response = client.get("/health")

        # GET requests should not require CSRF token
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting"""

    @pytest.mark.asyncio
    async def test_global_rate_limit(self):
        """Test global rate limiting"""
        identifier = "test_user_123"
        tier = UserTier.FREE.value

        # Make requests up to the limit
        for i in range(100):
            result = await AdvancedRateLimiter.check_rate_limit(
                identifier=identifier, user_tier=tier, endpoint=None
            )

            if i < 99:
                assert not result["overall_limited"]
            else:
                # 100th request should be limited
                assert result["overall_limited"]

    @pytest.mark.asyncio
    async def test_endpoint_specific_rate_limit(self):
        """Test endpoint-specific rate limiting"""
        identifier = "test_user_456"
        tier = UserTier.FREE.value
        endpoint = "/api/v1/auth/login"

        # Login endpoint has stricter limits (5 req/min for free tier)
        for i in range(6):
            result = await AdvancedRateLimiter.check_rate_limit(
                identifier=identifier, user_tier=tier, endpoint=endpoint
            )

            if i < 5:
                assert not result["overall_limited"]
            else:
                # 6th request should be limited
                assert result["overall_limited"]

    @pytest.mark.asyncio
    async def test_burst_protection(self):
        """Test burst protection"""
        identifier = "test_user_789"
        tier = UserTier.FREE.value

        # Make rapid requests (burst)
        for i in range(21):
            result = await AdvancedRateLimiter.check_rate_limit(
                identifier=identifier, user_tier=tier, endpoint=None
            )

            if i < 20:
                assert not result["burst"]["limited"]
            else:
                # 21st burst request should be limited
                assert result["burst"]["limited"]


class TestAuthorizationBypass:
    """Test authorization bypass attempts"""

    def test_horizontal_privilege_escalation(self):
        """Test protection against horizontal privilege escalation"""
        # User A tries to access User B's data
        # This would require actual API testing with real tokens
        pass  # Placeholder for integration test

    def test_vertical_privilege_escalation(self):
        """Test protection against vertical privilege escalation"""
        # Regular user tries to access admin endpoints
        # This would require actual API testing with real tokens
        pass  # Placeholder for integration test

    def test_idor_protection(self):
        """Test protection against Insecure Direct Object References"""
        # User tries to access resources by manipulating IDs
        # This would require actual API testing with real tokens
        pass  # Placeholder for integration test


class TestInputValidation:
    """Test input validation"""

    def test_email_validation(self):
        """Test email validation"""
        # Valid emails
        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
            "user+tag@example.com",
        ]

        for email in valid_emails:
            sanitized = InputSanitizer.sanitize_email(email)
            assert "@" in sanitized

        # Invalid emails
        invalid_emails = [
            "not_an_email",
            "@example.com",
            "user@",
            "user..double@example.com",
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_email(email)

    def test_url_validation(self):
        """Test URL validation"""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com/path",
            "https://sub.example.com:8080/path?query=value",
        ]

        for url in valid_urls:
            sanitized = InputSanitizer.sanitize_url(url)
            assert sanitized.startswith(("http://", "https://"))

        # Invalid URLs
        invalid_urls = [
            "javascript:alert('XSS')",
            "file:///etc/passwd",
            "ftp://example.com",
        ]

        for url in invalid_urls:
            with pytest.raises(ValidationError):
                InputSanitizer.sanitize_url(url)

    def test_length_limits(self):
        """Test length limit enforcement"""
        # String too long
        long_string = "a" * 1001

        with pytest.raises(ValidationError):
            InputSanitizer.sanitize_string(long_string, max_length=1000)

        # String within limit
        short_string = "a" * 100
        sanitized = InputSanitizer.sanitize_string(short_string, max_length=1000)
        assert len(sanitized) == 100


class TestSecurityHeaders:
    """Test security headers"""

    def test_security_headers_present(self):
        """Test that security headers are present"""
        response = client.get("/health")

        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "X-XSS-Protection" in response.headers
        assert "Content-Security-Policy" in response.headers

    def test_hsts_header(self):
        """Test HSTS header on HTTPS"""
        # This would require HTTPS testing
        pass  # Placeholder for HTTPS-specific test

    def test_cache_control_sensitive_endpoints(self):
        """Test cache control on sensitive endpoints"""
        # Sensitive endpoints should have no-cache headers
        response = client.get(
            "/api/v1/dashboard/metrics", headers={"Authorization": "Bearer valid_token"}
        )

        # Should have cache control headers (if authenticated)
        # This is a placeholder - actual test would need valid auth
        pass


class TestDataProtection:
    """Test data protection measures"""

    def test_password_hashing(self):
        """Test that passwords are properly hashed"""
        password = "SecurePassword123!"
        hashed = SecurityService.get_password_hash(password)

        # Hash should be different from password
        assert hashed != password

        # Hash should be bcrypt format
        assert hashed.startswith("$2b$")

        # Verification should work
        assert SecurityService.verify_password(password, hashed)

    def test_api_key_hashing(self):
        """Test that API keys are hashed"""
        api_key = SecurityService.generate_api_key()
        hashed = SecurityService.hash_api_key(api_key)

        # Hash should be different from key
        assert hashed != api_key

        # Hash should be consistent
        hashed2 = SecurityService.hash_api_key(api_key)
        assert hashed == hashed2

    def test_constant_time_comparison(self):
        """Test constant-time string comparison"""
        string1 = "secret_value_123"
        string2 = "secret_value_123"
        string3 = "different_value"

        # Same strings should match
        assert SecurityService.constant_time_compare(string1, string2)

        # Different strings should not match
        assert not SecurityService.constant_time_compare(string1, string3)


class TestAuditLogging:
    """Test audit logging"""

    @pytest.mark.asyncio
    async def test_login_attempt_logging(self):
        """Test that login attempts are logged"""
        await SecurityAuditLog.log_login_attempt(
            email="test@example.com",
            success=True,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Log should be created (would need to check Redis)
        # This is a placeholder for actual log verification
        pass

    @pytest.mark.asyncio
    async def test_password_change_logging(self):
        """Test that password changes are logged"""
        await SecurityAuditLog.log_password_change(
            user_id="user123", ip_address="192.168.1.1"
        )

        # Log should be created (would need to check Redis)
        # This is a placeholder for actual log verification
        pass


class TestMultiTenantIsolation:
    """Test multi-tenant data isolation"""

    def test_organization_id_in_token(self):
        """Test that organization ID is included in JWT token"""
        token_data = {
            "sub": "user123",
            "org_id": "org123",
            "email": "test@example.com",
            "role": "user",
        }

        token = SecurityService.create_access_token(token_data)
        decoded = SecurityService.verify_token(token)

        assert "org_id" in decoded
        assert decoded["org_id"] == "org123"

    def test_organization_id_extraction(self):
        """Test organization ID extraction from token"""
        token_data = {
            "sub": "user123",
            "org_id": "org456",
            "email": "test@example.com",
            "role": "user",
        }

        token = SecurityService.create_access_token(token_data)
        org_id = SecurityService.get_organization_id_from_token(token)

        assert org_id == "org456"


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
