"""
Custom middleware for authentication, authorization, and request processing
"""

import logging
import time
import traceback
import uuid
from typing import Any, Callable, Dict

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import (
    BusinessLogicError,
    DatabaseError,
    ReviveAIException,
    convert_exception_to_http,
)
from app.core.redis import redis_client
from app.core.security import SecurityService

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive error handling middleware that catches and formats all exceptions
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle all exceptions and return properly formatted error responses"""

        try:
            response = await call_next(request)
            return response

        except ReviveAIException as e:
            # Custom Revive AI exceptions
            return await self._handle_revive_ai_exception(request, e)

        except HTTPException as e:
            # FastAPI HTTPException - already properly formatted
            return await self._handle_http_exception(request, e)

        except StarletteHTTPException as e:
            # Starlette HTTPException
            return await self._handle_starlette_exception(request, e)

        except ValidationError as e:
            # Pydantic validation errors
            return await self._handle_validation_error(request, e)

        except ValueError as e:
            # Value errors (usually from business logic)
            return await self._handle_value_error(request, e)

        except PermissionError as e:
            # Permission/authorization errors
            return await self._handle_permission_error(request, e)

        except ConnectionError as e:
            # Database/external service connection errors
            return await self._handle_connection_error(request, e)

        except TimeoutError as e:
            # Timeout errors
            return await self._handle_timeout_error(request, e)

        except Exception as e:
            # Catch-all for unexpected errors
            return await self._handle_unexpected_error(request, e)

    async def _handle_revive_ai_exception(
        self, request: Request, exc: ReviveAIException
    ) -> JSONResponse:
        """Handle custom Revive AI exceptions"""
        request_id = getattr(request.state, "request_id", "unknown")

        # Convert to HTTP exception to get proper status code
        http_exc = convert_exception_to_http(exc)

        logger.warning(
            f"Revive AI Exception {request_id}: {type(exc).__name__} - {exc.message}",
            extra={
                "request_id": request_id,
                "exception_type": type(exc).__name__,
                "message": exc.message,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=http_exc.status_code,
            content={
                "error": {
                    "type": type(exc).__name__.lower().replace("error", "_error"),
                    "message": exc.message,
                    "status_code": http_exc.status_code,
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "path": request.url.path,
                    "details": exc.details if exc.details else None,
                }
            },
        )

    async def _handle_http_exception(
        self, request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle FastAPI HTTPException"""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            f"HTTP Exception {request_id}: {exc.status_code} - {exc.detail}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_exception",
                    "message": exc.detail,
                    "status_code": exc.status_code,
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "path": request.url.path,
                }
            },
            headers=exc.headers or {},
        )

    async def _handle_starlette_exception(
        self, request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle Starlette HTTPException"""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            f"Starlette Exception {request_id}: {exc.status_code} - {exc.detail}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_exception",
                    "message": exc.detail,
                    "status_code": exc.status_code,
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "path": request.url.path,
                }
            },
        )

    async def _handle_validation_error(
        self, request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors"""
        request_id = getattr(request.state, "request_id", "unknown")

        # Format validation errors
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(x) for x in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                    "input": error.get("input"),
                }
            )

        logger.warning(
            f"Validation Error {request_id}: {len(errors)} validation errors",
            extra={
                "request_id": request_id,
                "validation_errors": errors,
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "validation_error",
                    "message": "Request validation failed",
                    "status_code": 422,
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "path": request.url.path,
                    "details": errors,
                }
            },
        )

    async def _handle_value_error(
        self, request: Request, exc: ValueError
    ) -> JSONResponse:
        """Handle ValueError (business logic errors)"""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            f"Value Error {request_id}: {str(exc)}",
            extra={
                "request_id": request_id,
                "error": str(exc),
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "type": "value_error",
                    "message": str(exc),
                    "status_code": 400,
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "path": request.url.path,
                }
            },
        )

    async def _handle_permission_error(
        self, request: Request, exc: PermissionError
    ) -> JSONResponse:
        """Handle PermissionError (authorization errors)"""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            f"Permission Error {request_id}: {str(exc)}",
            extra={
                "request_id": request_id,
                "error": str(exc),
                "path": request.url.path,
                "method": request.method,
                "user_id": getattr(request.state, "user_id", None),
                "organization_id": getattr(request.state, "organization_id", None),
            },
        )

        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": {
                    "type": "permission_error",
                    "message": "Insufficient permissions to access this resource",
                    "status_code": 403,
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "path": request.url.path,
                }
            },
        )

    async def _handle_connection_error(
        self, request: Request, exc: ConnectionError
    ) -> JSONResponse:
        """Handle ConnectionError (database/external service errors)"""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            f"Connection Error {request_id}: {str(exc)}",
            extra={
                "request_id": request_id,
                "error": str(exc),
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "type": "service_unavailable",
                    "message": "Service temporarily unavailable. Please try again later.",
                    "status_code": 503,
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "path": request.url.path,
                }
            },
        )

    async def _handle_timeout_error(
        self, request: Request, exc: TimeoutError
    ) -> JSONResponse:
        """Handle TimeoutError"""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            f"Timeout Error {request_id}: {str(exc)}",
            extra={
                "request_id": request_id,
                "error": str(exc),
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            content={
                "error": {
                    "type": "timeout_error",
                    "message": "Request timed out. Please try again.",
                    "status_code": 408,
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "path": request.url.path,
                }
            },
        )

    async def _handle_unexpected_error(
        self, request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected errors"""
        request_id = getattr(request.state, "request_id", "unknown")

        # Log full traceback for debugging
        logger.error(
            f"Unexpected Error {request_id}: {type(exc).__name__}: {str(exc)}",
            extra={
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc(),
            },
            exc_info=True,
        )

        # Don't expose internal error details in production
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "internal_server_error",
                    "message": "An unexpected error occurred. Please try again later.",
                    "status_code": 500,
                    "request_id": request_id,
                    "timestamp": time.time(),
                    "path": request.url.path,
                }
            },
        )


class DatabaseErrorHandlingMixin:
    """
    Mixin for handling database-specific errors
    """

    @staticmethod
    def handle_database_error(exc: Exception) -> Dict[str, Any]:
        """Convert database errors to standardized format"""

        # SQLAlchemy errors
        if "sqlalchemy" in str(type(exc)).lower():
            if "integrity" in str(exc).lower():
                return {
                    "type": "integrity_error",
                    "message": "Data integrity constraint violation",
                    "status_code": 409,
                }
            elif "connection" in str(exc).lower():
                return {
                    "type": "database_connection_error",
                    "message": "Database connection failed",
                    "status_code": 503,
                }
            elif "timeout" in str(exc).lower():
                return {
                    "type": "database_timeout",
                    "message": "Database operation timed out",
                    "status_code": 408,
                }

        # PostgreSQL specific errors
        if "psycopg" in str(type(exc)).lower():
            if "unique" in str(exc).lower():
                return {
                    "type": "duplicate_entry",
                    "message": "Resource already exists",
                    "status_code": 409,
                }
            elif "foreign key" in str(exc).lower():
                return {
                    "type": "foreign_key_violation",
                    "message": "Referenced resource does not exist",
                    "status_code": 400,
                }

        # Default database error
        return {
            "type": "database_error",
            "message": "Database operation failed",
            "status_code": 500,
        }


class BusinessLogicErrorHandlingMixin:
    """
    Mixin for handling business logic errors
    """

    @staticmethod
    def handle_business_logic_error(exc: Exception) -> Dict[str, Any]:
        """Convert business logic errors to standardized format"""

        error_message = str(exc).lower()

        # Common business logic error patterns
        if "not found" in error_message:
            return {
                "type": "resource_not_found",
                "message": "Requested resource not found",
                "status_code": 404,
            }
        elif "already exists" in error_message:
            return {
                "type": "resource_exists",
                "message": "Resource already exists",
                "status_code": 409,
            }
        elif "invalid" in error_message:
            return {
                "type": "invalid_input",
                "message": "Invalid input provided",
                "status_code": 400,
            }
        elif "unauthorized" in error_message or "permission" in error_message:
            return {
                "type": "unauthorized",
                "message": "Insufficient permissions",
                "status_code": 403,
            }
        elif "limit exceeded" in error_message or "quota" in error_message:
            return {
                "type": "limit_exceeded",
                "message": "Rate limit or quota exceeded",
                "status_code": 429,
            }

        # Default business logic error
        return {"type": "business_logic_error", "message": str(exc), "status_code": 400}


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling authentication and adding user context to requests
    """

    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/reset-password/confirm",
        "/api/v1/auth/verify-email",
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/health/detailed",
        "/versions",
        "/metrics",
        # Temporarily added for testing
        "/api/v1/reviews",
        "/api/v1/support-tickets",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add authentication context"""

        # Skip authentication for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Skip authentication for static files and docs
        if (
            request.url.path.startswith("/static/")
            or request.url.path.startswith("/docs")
            or request.url.path.startswith("/redoc")
        ):
            return await call_next(request)

        # Extract authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authorization header missing"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate Bearer token format
        try:
            scheme, token = authorization.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("Invalid scheme")
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authorization header format"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify JWT token
        try:
            payload = SecurityService.verify_token(token)

            # Add user context to request state
            request.state.user_id = payload.get("sub")
            request.state.organization_id = payload.get("org_id")
            request.state.user_email = payload.get("email")
            request.state.user_role = payload.get("role")
            request.state.token_type = payload.get("type", "access")

        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
                headers=e.headers or {},
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Process request
        response = await call_next(request)
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware for comprehensive request logging and monitoring
    """

    def __init__(self, app, log_body: bool = False, log_headers: bool = False):
        super().__init__(app)
        self.log_body = log_body
        self.log_headers = log_headers

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log comprehensive request and response information with metrics"""

        # Generate request ID if not exists
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Collect request information
        request_info = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host if request.client else None,
            "user_id": getattr(request.state, "user_id", None),
            "organization_id": getattr(request.state, "organization_id", None),
            "api_version": getattr(request.state, "api_version", None),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
            "timestamp": start_time,
        }

        # Log headers if enabled (excluding sensitive ones)
        if self.log_headers:
            sensitive_headers = {"authorization", "cookie", "x-api-key", "x-auth-token"}
            request_info["headers"] = {
                k: v
                for k, v in request.headers.items()
                if k.lower() not in sensitive_headers
            }

        # Log request body if enabled and appropriate
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    # Read body (this consumes the stream, so we need to replace it)
                    body = await request.body()
                    if body:
                        request_info["body_size"] = len(body)
                        # Only log body for small requests to avoid log spam
                        if len(body) < 1024:  # 1KB limit
                            request_info["body"] = body.decode("utf-8")[
                                :500
                            ]  # Truncate at 500 chars
                except Exception as e:
                    request_info["body_read_error"] = str(e)

        # Log request
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path}",
            extra=request_info,
        )

        # Process request and handle errors
        response = None
        error_info = None

        try:
            response = await call_next(request)

        except Exception as e:
            error_info = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc(),
            }
            # Re-raise to let error handling middleware deal with it
            raise

        finally:
            # Calculate processing time
            process_time = time.time() - start_time

            # Collect response information
            response_info = {
                "request_id": request_id,
                "status_code": response.status_code if response else 500,
                "process_time": process_time,
                "response_size": (
                    response.headers.get("content-length") if response else None
                ),
            }

            # Add error information if applicable
            if error_info:
                response_info.update(error_info)

            # Add response headers if enabled
            if self.log_headers and response:
                response_info["response_headers"] = dict(response.headers)

            # Determine log level based on status code and processing time
            if response and response.status_code < 400 and process_time < 1.0:
                log_level = logging.INFO
            elif response and response.status_code < 500:
                log_level = logging.WARNING
            else:
                log_level = logging.ERROR

            # Log response
            status_code = response.status_code if response else 500
            logger.log(
                log_level,
                f"Response {request_id}: {status_code} ({process_time:.3f}s)",
                extra=response_info,
            )

            # Add monitoring headers to response
            if response:
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Process-Time"] = f"{process_time:.3f}"
                response.headers["X-Timestamp"] = str(int(start_time))

            # Record metrics (if metrics system is available)
            await self._record_metrics(request_info, response_info)

        return response

    async def _record_metrics(self, request_info: dict, response_info: dict):
        """Record metrics for monitoring (placeholder for metrics system)"""
        try:
            # This would integrate with a metrics system like Prometheus, DataDog, etc.
            # For now, we'll use Redis to store basic metrics

            from app.core.redis import redis_client

            # Record request count by endpoint
            endpoint_key = f"metrics:requests:{request_info['path']}"
            await redis_client.increment(endpoint_key)
            await redis_client.expire(endpoint_key, 86400)  # 24 hours

            # Record response time
            response_time_key = f"metrics:response_time:{request_info['path']}"
            await redis_client.redis.lpush(
                response_time_key, response_info["process_time"]
            )
            await redis_client.redis.ltrim(
                response_time_key, 0, 99
            )  # Keep last 100 measurements
            await redis_client.expire(response_time_key, 86400)

            # Record status codes
            status_key = f"metrics:status:{response_info['status_code']}"
            await redis_client.increment(status_key)
            await redis_client.expire(status_key, 86400)

            # Record errors
            if response_info["status_code"] >= 400:
                error_key = f"metrics:errors:{request_info['path']}"
                await redis_client.increment(error_key)
                await redis_client.expire(error_key, 86400)

        except Exception as e:
            # Don't let metrics recording break the request
            logger.error(f"Failed to record metrics: {e}")


class MetricsCollector:
    """Utility class for collecting and retrieving application metrics"""

    @staticmethod
    async def get_endpoint_metrics(endpoint: str = None, hours: int = 24) -> dict:
        """Get metrics for specific endpoint or all endpoints"""
        from app.core.redis import redis_client

        if endpoint:
            endpoints = [endpoint]
        else:
            # Get all endpoint keys
            pattern = "metrics:requests:*"
            if redis_client.redis:
                keys = await redis_client.redis.keys(pattern)
                endpoints = [key.split(":", 2)[2] for key in keys]
            else:
                endpoints = []

        metrics = {}

        for ep in endpoints:
            # Request count
            request_count = await redis_client.get(f"metrics:requests:{ep}")

            # Average response time
            response_times = []
            if redis_client.redis:
                times = await redis_client.redis.lrange(
                    f"metrics:response_time:{ep}", 0, -1
                )
                response_times = [float(t) for t in times if t]

            avg_response_time = (
                sum(response_times) / len(response_times) if response_times else 0
            )

            # Error count
            error_count = await redis_client.get(f"metrics:errors:{ep}")

            metrics[ep] = {
                "request_count": int(request_count) if request_count else 0,
                "avg_response_time": round(avg_response_time, 3),
                "error_count": int(error_count) if error_count else 0,
                "error_rate": (
                    round((int(error_count) / int(request_count)) * 100, 2)
                    if request_count and int(request_count) > 0
                    else 0
                ),
            }

        return metrics

    @staticmethod
    async def get_system_metrics() -> dict:
        """Get overall system metrics"""
        from app.core.redis import redis_client

        # Status code distribution
        status_codes = {}
        for code in [200, 201, 400, 401, 403, 404, 422, 429, 500, 503]:
            count = await redis_client.get(f"metrics:status:{code}")
            if count:
                status_codes[str(code)] = int(count)

        # Total requests
        total_requests = sum(status_codes.values())

        # Error rate
        error_requests = sum(
            count for code, count in status_codes.items() if int(code) >= 400
        )
        error_rate = (
            (error_requests / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "total_requests": total_requests,
            "status_code_distribution": status_codes,
            "error_rate": round(error_rate, 2),
            "timestamp": int(time.time()),
        }

    @staticmethod
    async def reset_metrics():
        """Reset all metrics (useful for testing)"""
        from app.core.redis import redis_client

        if redis_client.redis:
            # Delete all metrics keys
            patterns = ["metrics:*"]
            for pattern in patterns:
                keys = await redis_client.redis.keys(pattern)
                if keys:
                    await redis_client.redis.delete(*keys)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware with multiple strategies and tiers
    """

    def __init__(self, app, use_sliding_window: bool = True):
        super().__init__(app)
        self.use_sliding_window = use_sliding_window

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply advanced rate limiting based on user tier and endpoint"""

        # Skip rate limiting for health checks and static files
        if request.url.path in [
            "/",
            "/health",
            "/metrics",
        ] or request.url.path.startswith("/static/"):
            return await call_next(request)

        # Get user context
        user_id = getattr(request.state, "user_id", None)
        organization_id = getattr(request.state, "organization_id", None)
        client_ip = request.client.host if request.client else "unknown"

        # Determine identifier and user tier
        from app.core.redis import AdvancedRateLimiter

        if user_id:
            identifier = f"user:{user_id}"
            user_tier = await AdvancedRateLimiter.get_user_tier(
                user_id, organization_id
            )
        else:
            identifier = f"ip:{client_ip}"
            user_tier = "anonymous"

        # Check rate limits
        rate_limit_info = await AdvancedRateLimiter.check_rate_limit(
            identifier=identifier,
            user_tier=user_tier,
            endpoint=request.url.path,
            use_sliding_window=self.use_sliding_window,
        )

        # Check if rate limited
        if rate_limit_info["overall_limited"]:
            # Determine which limit was exceeded
            if rate_limit_info["global"]["limited"]:
                retry_after = rate_limit_info["global"]["reset_time"] - int(time.time())
                limit_type = "global"
            else:
                retry_after = rate_limit_info["endpoint"]["reset_time"] - int(
                    time.time()
                )
                limit_type = "endpoint"

            # Log rate limit violation
            logger.warning(
                f"Rate limit exceeded for {identifier}",
                extra={
                    "identifier": identifier,
                    "user_tier": user_tier,
                    "endpoint": request.url.path,
                    "limit_type": limit_type,
                    "rate_limit_info": rate_limit_info,
                },
            )

            # Generate rate limit headers
            headers = AdvancedRateLimiter.get_rate_limit_headers(rate_limit_info)
            headers.update(
                {
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit-Type": limit_type,
                }
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "type": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded for {limit_type} requests",
                        "status_code": 429,
                        "request_id": getattr(request.state, "request_id", "unknown"),
                        "timestamp": time.time(),
                        "path": request.url.path,
                        "details": {
                            "limit_type": limit_type,
                            "retry_after": retry_after,
                            "user_tier": user_tier,
                        },
                    }
                },
                headers=headers,
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        rate_limit_headers = AdvancedRateLimiter.get_rate_limit_headers(rate_limit_info)
        for header_name, header_value in rate_limit_headers.items():
            response.headers[header_name] = header_value

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""

        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # Add HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


class OrganizationIsolationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for ensuring organization data isolation
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Ensure organization data isolation"""

        # Skip for public paths
        if request.url.path in AuthenticationMiddleware.PUBLIC_PATHS:
            return await call_next(request)

        # Add organization context validation
        organization_id = getattr(request.state, "organization_id", None)
        if organization_id:
            # Store organization context for use in database queries
            request.state.organization_filter = organization_id

        return await call_next(request)
