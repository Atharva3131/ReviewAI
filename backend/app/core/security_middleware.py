"""
Enhanced security middleware for comprehensive protection
"""

import hashlib
import hmac
import ipaddress
import logging
import secrets
import time
from typing import Callable, Dict, List, Optional, Set

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.redis import redis_client
from app.core.security import SecurityService
from app.core.validation import InputSanitizer, ValidationError

logger = logging.getLogger(__name__)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF (Cross-Site Request Forgery) protection middleware
    """

    # Methods that require CSRF protection
    CSRF_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Paths exempt from CSRF protection
    CSRF_EXEMPT_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/webhooks/google",
        "/api/v1/webhooks/crm",
        "/api/v1/reviews",
        "/api/v1/support-tickets",
        "/api/v1/customers",
        "/health",
        "/metrics",
    }

    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply CSRF protection to state-changing requests"""

        # Skip CSRF protection for safe methods
        if request.method not in self.CSRF_PROTECTED_METHODS:
            return await call_next(request)

        # Skip CSRF for all API routes (they use JWT Bearer tokens, not cookies)
        if request.url.path.startswith("/api/"):
            return await call_next(request)

        # Check if path is exempt (exact match or starts with exempt path)
        request_path = request.url.path
        is_exempt = any(
            request_path == exempt_path or request_path.startswith(exempt_path + "/")
            for exempt_path in self.CSRF_EXEMPT_PATHS
        )

        if is_exempt:
            return await call_next(request)

        # Skip for API key authentication (stateless)
        if request.headers.get("X-API-Key"):
            return await call_next(request)

        # Get CSRF token from header or form data
        csrf_token = request.headers.get("X-CSRF-Token") or request.headers.get(
            "X-CSRFToken"
        )

        if not csrf_token:
            logger.warning(
                f"CSRF token missing for {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                },
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": {
                        "type": "csrf_token_missing",
                        "message": "CSRF token required for this request",
                        "status_code": 403,
                    }
                },
            )

        # Validate CSRF token
        if not self._validate_csrf_token(csrf_token, request):
            logger.warning(
                f"Invalid CSRF token for {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "csrf_token_sample": (
                        csrf_token[:10] + "..." if len(csrf_token) > 10 else csrf_token
                    ),
                },
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": {
                        "type": "csrf_token_invalid",
                        "message": "Invalid CSRF token",
                        "status_code": 403,
                    }
                },
            )

        # Process request
        response = await call_next(request)

        # Add new CSRF token to response for SPA applications
        new_csrf_token = self._generate_csrf_token()
        response.headers["X-CSRF-Token"] = new_csrf_token

        return response

    def _validate_csrf_token(self, token: str, request: Request) -> bool:
        """Validate CSRF token using HMAC"""
        try:
            # Extract timestamp and signature from token
            parts = token.split(".")
            if len(parts) != 2:
                return False

            timestamp_str, signature = parts
            timestamp = int(timestamp_str)

            # Check if token is not too old (1 hour)
            if time.time() - timestamp > 3600:
                return False

            # Generate expected signature
            user_id = getattr(request.state, "user_id", "")
            session_data = (
                f"{timestamp}.{user_id}.{request.client.host if request.client else ''}"
            )
            expected_signature = hmac.new(
                self.secret_key.encode(), session_data.encode(), hashlib.sha256
            ).hexdigest()

            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)

        except (ValueError, AttributeError):
            return False

    def _generate_csrf_token(self) -> str:
        """Generate new CSRF token"""
        timestamp = int(time.time())
        random_data = secrets.token_hex(16)
        token_data = f"{timestamp}.{random_data}"

        signature = hmac.new(
            self.secret_key.encode(), token_data.encode(), hashlib.sha256
        ).hexdigest()

        return f"{timestamp}.{signature}"


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic input sanitization
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Sanitize request inputs automatically"""

        # Skip sanitization for certain content types
        content_type = request.headers.get("content-type", "")
        if any(
            ct in content_type.lower()
            for ct in ["multipart/form-data", "application/octet-stream"]
        ):
            return await call_next(request)

        # Sanitize query parameters
        if request.query_params:
            sanitized_params = {}
            for key, value in request.query_params.items():
                try:
                    sanitized_key = InputSanitizer.sanitize_string(key, max_length=100)
                    sanitized_value = InputSanitizer.sanitize_string(
                        value, max_length=1000
                    )
                    sanitized_params[sanitized_key] = sanitized_value
                except ValidationError as e:
                    logger.warning(
                        f"Invalid query parameter: {key}={value}, error: {e.message}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "error": {
                                "type": "invalid_query_parameter",
                                "message": f"Invalid query parameter '{key}': {e.message}",
                                "status_code": 400,
                            }
                        },
                    )

            # Store sanitized params for use in endpoints
            request.state.sanitized_query_params = sanitized_params

        # Sanitize headers (specific ones)
        sanitized_headers = {}
        headers_to_sanitize = ["user-agent", "referer", "x-forwarded-for"]

        for header_name in headers_to_sanitize:
            header_value = request.headers.get(header_name)
            if header_value:
                try:
                    sanitized_headers[header_name] = InputSanitizer.sanitize_string(
                        header_value, max_length=500
                    )
                except ValidationError:
                    # Log but don't block request for header sanitization failures
                    logger.warning(
                        f"Failed to sanitize header {header_name}: {header_value}"
                    )

        request.state.sanitized_headers = sanitized_headers

        return await call_next(request)


class AdvancedSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Advanced security headers middleware with configurable policies
    """

    def __init__(self, app, config: Dict[str, any] = None):
        super().__init__(app)
        self.config = config or {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add comprehensive security headers"""

        response = await call_next(request)

        # Content Security Policy
        csp_policy = self.config.get("csp_policy", self._get_default_csp())
        response.headers["Content-Security-Policy"] = csp_policy

        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature Policy)
        permissions_policy = self.config.get(
            "permissions_policy", self._get_default_permissions()
        )
        response.headers["Permissions-Policy"] = permissions_policy

        # Cross-Origin Embedder Policy
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

        # Cross-Origin Opener Policy
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Cross-Origin Resource Policy
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Strict Transport Security (HTTPS only)
        if request.url.scheme == "https":
            hsts_header = self.config.get(
                "hsts_header", "max-age=31536000; includeSubDomains; preload"
            )
            response.headers["Strict-Transport-Security"] = hsts_header

        # Cache Control for sensitive endpoints
        if self._is_sensitive_endpoint(request.url.path):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        # Server header removal/modification
        response.headers["Server"] = "Revive-AI"

        return response

    def _get_default_csp(self) -> str:
        """Get default Content Security Policy"""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "object-src 'none'; "
            "child-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "manifest-src 'self';"
        )

    def _get_default_permissions(self) -> str:
        """Get default Permissions Policy"""
        return (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "interest-cohort=(), "
            "payment=(), "
            "usb=(), "
            "bluetooth=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Check if endpoint contains sensitive data"""
        sensitive_patterns = [
            "/api/v1/auth/",
            "/api/v1/users/",
            "/api/v1/dashboard/",
            "/api/v1/customers/",
        ]
        return any(pattern in path for pattern in sensitive_patterns)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    IP whitelist/blacklist middleware for additional access control
    """

    def __init__(self, app, whitelist: List[str] = None, blacklist: List[str] = None):
        super().__init__(app)
        self.whitelist = self._parse_ip_list(whitelist or [])
        self.blacklist = self._parse_ip_list(blacklist or [])

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check IP against whitelist/blacklist"""

        client_ip = self._get_client_ip(request)

        # Check blacklist first
        if self._is_ip_in_list(client_ip, self.blacklist):
            logger.warning(f"Blocked request from blacklisted IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": {
                        "type": "ip_blocked",
                        "message": "Access denied",
                        "status_code": 403,
                    }
                },
            )

        # Check whitelist if configured
        if self.whitelist and not self._is_ip_in_list(client_ip, self.whitelist):
            logger.warning(f"Blocked request from non-whitelisted IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": {
                        "type": "ip_not_whitelisted",
                        "message": "Access denied",
                        "status_code": 403,
                    }
                },
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP considering proxy headers"""
        # Check X-Forwarded-For header (from load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct connection IP
        return request.client.host if request.client else "127.0.0.1"

    def _parse_ip_list(self, ip_list: List[str]) -> List[ipaddress.IPv4Network]:
        """Parse IP list into network objects"""
        networks = []
        for ip_str in ip_list:
            try:
                # Handle both single IPs and CIDR notation
                if "/" not in ip_str:
                    ip_str += "/32"  # Single IP
                networks.append(ipaddress.IPv4Network(ip_str, strict=False))
            except ValueError as e:
                logger.error(f"Invalid IP address in list: {ip_str}, error: {e}")
        return networks

    def _is_ip_in_list(self, ip: str, ip_list: List[ipaddress.IPv4Network]) -> bool:
        """Check if IP is in the given list"""
        try:
            client_ip = ipaddress.IPv4Address(ip)
            return any(client_ip in network for network in ip_list)
        except ValueError:
            logger.warning(f"Invalid client IP address: {ip}")
            return False


class DDoSProtectionMiddleware(BaseHTTPMiddleware):
    """
    Basic DDoS protection middleware with rate limiting and request analysis
    """

    def __init__(
        self, app, max_requests_per_minute: int = 100, max_requests_per_second: int = 10
    ):
        super().__init__(app)
        self.max_requests_per_minute = max_requests_per_minute
        self.max_requests_per_second = max_requests_per_second

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply DDoS protection measures"""

        client_ip = self._get_client_ip(request)
        current_time = int(time.time())

        # Check requests per second
        second_key = f"ddos:second:{client_ip}:{current_time}"
        second_count = await redis_client.increment(second_key)
        await redis_client.expire(second_key, 1)

        if second_count > self.max_requests_per_second:
            logger.warning(
                f"DDoS protection: Too many requests per second from {client_ip}"
            )
            return self._create_rate_limit_response("Too many requests per second")

        # Check requests per minute
        minute_key = f"ddos:minute:{client_ip}:{current_time // 60}"
        minute_count = await redis_client.increment(minute_key)
        await redis_client.expire(minute_key, 60)

        if minute_count > self.max_requests_per_minute:
            logger.warning(
                f"DDoS protection: Too many requests per minute from {client_ip}"
            )
            return self._create_rate_limit_response("Too many requests per minute")

        # Analyze request patterns for suspicious behavior
        if await self._is_suspicious_request(request, client_ip):
            logger.warning(
                f"DDoS protection: Suspicious request pattern from {client_ip}"
            )
            return self._create_rate_limit_response(
                "Suspicious request pattern detected"
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP (same as IPWhitelistMiddleware)"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "127.0.0.1"

    async def _is_suspicious_request(self, request: Request, client_ip: str) -> bool:
        """Analyze request for suspicious patterns"""

        # Check for missing or suspicious User-Agent
        user_agent = request.headers.get("User-Agent", "")
        if not user_agent or len(user_agent) < 10:
            return True

        # Check for suspicious User-Agent patterns
        suspicious_agents = [
            "bot",
            "crawler",
            "scanner",
            "curl",
            "wget",
            "python-requests",
        ]
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            # Allow legitimate bots but rate limit them more strictly
            bot_key = f"ddos:bot:{client_ip}:{int(time.time()) // 60}"
            bot_count = await redis_client.increment(bot_key)
            await redis_client.expire(bot_key, 60)
            return bot_count > 10  # Lower limit for bots

        # Check for rapid requests to different endpoints (scanning behavior)
        endpoint_key = f"ddos:endpoints:{client_ip}"
        if redis_client.redis:
            await redis_client.redis.sadd(endpoint_key, request.url.path)
            await redis_client.expire(endpoint_key, 300)  # 5 minutes
            endpoint_count = await redis_client.redis.scard(endpoint_key)

            # If accessing too many different endpoints quickly, it's suspicious
            if endpoint_count > 20:
                return True

        return False

    def _create_rate_limit_response(self, message: str) -> JSONResponse:
        """Create rate limit response"""
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "type": "rate_limit_exceeded",
                    "message": message,
                    "status_code": 429,
                }
            },
            headers={"Retry-After": "60"},
        )


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive audit logging middleware for security events
    """

    # Sensitive endpoints that require detailed logging
    SENSITIVE_ENDPOINTS = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/users/",
        "/api/v1/customers/",
        "/api/v1/reviews/",
        "/api/v1/agents/",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log security-relevant events"""

        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")

        # Collect request information
        audit_data = {
            "request_id": request_id,
            "timestamp": start_time,
            "method": request.method,
            "path": request.url.path,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", ""),
            "user_id": getattr(request.state, "user_id", None),
            "organization_id": getattr(request.state, "organization_id", None),
            "referer": request.headers.get("Referer", ""),
        }

        # Process request
        response = await call_next(request)

        # Add response information
        audit_data.update(
            {
                "status_code": response.status_code,
                "response_time": time.time() - start_time,
            }
        )

        # Log based on sensitivity and status
        if self._should_audit_log(request.url.path, response.status_code):
            await self._write_audit_log(audit_data)

        # Log security events
        if response.status_code in [401, 403, 429]:
            await self._log_security_event(audit_data, response.status_code)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "127.0.0.1"

    def _should_audit_log(self, path: str, status_code: int) -> bool:
        """Determine if request should be audit logged"""
        # Always log sensitive endpoints
        if any(sensitive in path for sensitive in self.SENSITIVE_ENDPOINTS):
            return True

        # Always log errors
        if status_code >= 400:
            return True

        # Log state-changing operations
        return False

    async def _write_audit_log(self, audit_data: dict):
        """Write audit log entry"""
        try:
            # Store in Redis for real-time monitoring
            log_key = f"audit_log:{audit_data['request_id']}"
            await redis_client.set_json(
                log_key, audit_data, expire=30 * 24 * 60 * 60
            )  # 30 days

            # Also log to application logger
            logger.info(
                f"Audit: {audit_data['method']} {audit_data['path']} - {audit_data['status_code']}",
                extra=audit_data,
            )

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    async def _log_security_event(self, audit_data: dict, status_code: int):
        """Log security-specific events"""
        event_type = {
            401: "authentication_failure",
            403: "authorization_failure",
            429: "rate_limit_exceeded",
        }.get(status_code, "security_event")

        security_event = {
            **audit_data,
            "event_type": event_type,
            "severity": "high" if status_code in [401, 403] else "medium",
        }

        try:
            # Store security events separately for monitoring
            event_key = f"security_event:{int(time.time())}:{secrets.token_hex(4)}"
            await redis_client.set_json(
                event_key, security_event, expire=90 * 24 * 60 * 60
            )  # 90 days

            logger.warning(
                f"Security Event: {event_type} - {audit_data['path']}",
                extra=security_event,
            )

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
