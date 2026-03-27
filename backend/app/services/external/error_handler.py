"""
Enhanced error handling and retry mechanisms for external services
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from app.core.config import settings
from app.core.redis import redis_client

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for better handling"""

    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors"""

    service_name: str
    operation: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceError:
    """Detailed error information"""

    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    context: ErrorContext
    original_exception: Optional[Exception] = None
    status_code: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None
    resolved: bool = False
    resolution_notes: Optional[str] = None


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""

    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    success_threshold: int = 3  # successes needed to close circuit
    timeout: int = 30  # request timeout


class CircuitBreaker:
    """Circuit breaker for external services"""

    def __init__(self, service_name: str, config: CircuitBreakerConfig):
        self.service_name = service_name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.next_attempt_time: Optional[datetime] = None

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception(f"Circuit breaker OPEN for {self.service_name}")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result

        except Exception as e:
            await self._on_failure(e)
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker"""
        if not self.last_failure_time:
            return True

        return (
            datetime.utcnow() - self.last_failure_time
        ).total_seconds() >= self.config.recovery_timeout

    async def _on_success(self):
        """Handle successful operation"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker CLOSED for {self.service_name}")
        else:
            self.failure_count = 0

    async def _on_failure(self, exception: Exception):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = datetime.utcnow() + timedelta(
                seconds=self.config.recovery_timeout
            )
            logger.warning(f"Circuit breaker OPEN for {self.service_name}")


class ExternalServiceErrorHandler:
    """Centralized error handling for external services"""

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_history: List[ServiceError] = []
        self.error_callbacks: Dict[ErrorCategory, List[Callable]] = {}

    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service"""
        if service_name not in self.circuit_breakers:
            config = CircuitBreakerConfig()
            self.circuit_breakers[service_name] = CircuitBreaker(service_name, config)

        return self.circuit_breakers[service_name]

    def register_error_callback(self, category: ErrorCategory, callback: Callable):
        """Register callback for specific error categories"""
        if category not in self.error_callbacks:
            self.error_callbacks[category] = []
        self.error_callbacks[category].append(callback)

    async def handle_error(
        self, error: Exception, context: ErrorContext, status_code: Optional[int] = None
    ) -> ServiceError:
        """Handle and categorize errors"""

        # Generate unique error ID
        error_id = f"{context.service_name}_{int(datetime.utcnow().timestamp())}"

        # Categorize error
        category = self._categorize_error(error, status_code)
        severity = self._determine_severity(category, status_code)

        # Create service error
        service_error = ServiceError(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(error),
            context=context,
            original_exception=error,
            status_code=status_code,
        )

        # Store error
        await self._store_error(service_error)

        # Execute callbacks
        await self._execute_callbacks(service_error)

        # Log error
        await self._log_error(service_error)

        return service_error

    def _categorize_error(
        self, error: Exception, status_code: Optional[int]
    ) -> ErrorCategory:
        """Categorize error based on type and status code"""
        if status_code:
            if status_code == 401 or status_code == 403:
                return ErrorCategory.AUTHENTICATION
            elif status_code == 429:
                return ErrorCategory.RATE_LIMIT
            elif 400 <= status_code < 500:
                return ErrorCategory.VALIDATION
            elif status_code >= 500:
                return ErrorCategory.SERVER_ERROR

        error_type = type(error).__name__.lower()

        if "timeout" in error_type or "timeout" in str(error).lower():
            return ErrorCategory.TIMEOUT
        elif "network" in error_type or "connection" in error_type:
            return ErrorCategory.NETWORK

        return ErrorCategory.UNKNOWN

    def _determine_severity(
        self, category: ErrorCategory, status_code: Optional[int]
    ) -> ErrorSeverity:
        """Determine error severity"""
        if category == ErrorCategory.AUTHENTICATION:
            return ErrorSeverity.HIGH
        elif category == ErrorCategory.RATE_LIMIT:
            return ErrorSeverity.MEDIUM
        elif category == ErrorCategory.SERVER_ERROR:
            return ErrorSeverity.HIGH
        elif category == ErrorCategory.TIMEOUT:
            return ErrorSeverity.MEDIUM
        elif category == ErrorCategory.NETWORK:
            return ErrorSeverity.HIGH

        return ErrorSeverity.LOW

    async def _store_error(self, error: ServiceError):
        """Store error in Redis for analysis"""
        error_key = f"service_error:{error.error_id}"
        error_data = {
            "error_id": error.error_id,
            "service_name": error.context.service_name,
            "category": error.category.value,
            "severity": error.severity.value,
            "message": error.message,
            "status_code": error.status_code,
            "timestamp": error.context.timestamp.isoformat(),
            "operation": error.context.operation,
            "retry_count": error.retry_count,
            "resolved": error.resolved,
        }

        # Store individual error (expires in 7 days)
        await redis_client.set_json(error_key, error_data, 604800)

        # Add to service error list
        service_errors_key = f"service_errors:{error.context.service_name}"
        await redis_client.lpush(service_errors_key, error.error_id)
        await redis_client.ltrim(service_errors_key, 0, 99)  # Keep last 100 errors
        await redis_client.expire(service_errors_key, 604800)

        # Update error statistics
        await self._update_error_stats(error)

    async def _update_error_stats(self, error: ServiceError):
        """Update error statistics"""
        stats_key = f"error_stats:{error.context.service_name}"
        stats = await redis_client.get_json(stats_key) or {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "last_error": None,
        }

        stats["total_errors"] += 1
        stats["errors_by_category"][error.category.value] = (
            stats["errors_by_category"].get(error.category.value, 0) + 1
        )
        stats["errors_by_severity"][error.severity.value] = (
            stats["errors_by_severity"].get(error.severity.value, 0) + 1
        )
        stats["last_error"] = error.context.timestamp.isoformat()

        await redis_client.set_json(stats_key, stats, 86400)  # 24 hours

    async def _execute_callbacks(self, error: ServiceError):
        """Execute registered callbacks for error category"""
        callbacks = self.error_callbacks.get(error.category, [])

        for callback in callbacks:
            try:
                await callback(error)
            except Exception as e:
                logger.error(f"Error executing callback for {error.category}: {e}")

    async def _log_error(self, error: ServiceError):
        """Log error with appropriate level"""
        log_data = {
            "error_id": error.error_id,
            "service": error.context.service_name,
            "category": error.category.value,
            "severity": error.severity.value,
            "operation": error.context.operation,
            "status_code": error.status_code,
        }

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(
                f"Critical error in {error.context.service_name}: {error.message}",
                extra=log_data,
            )
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(
                f"High severity error in {error.context.service_name}: {error.message}",
                extra=log_data,
            )
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(
                f"Medium severity error in {error.context.service_name}: {error.message}",
                extra=log_data,
            )
        else:
            logger.info(
                f"Low severity error in {error.context.service_name}: {error.message}",
                extra=log_data,
            )

    async def get_service_errors(
        self, service_name: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent errors for a service"""
        service_errors_key = f"service_errors:{service_name}"
        error_ids = await redis_client.lrange(service_errors_key, 0, limit - 1)

        errors = []
        for error_id in error_ids:
            error_key = f"service_error:{error_id}"
            error_data = await redis_client.get_json(error_key)
            if error_data:
                errors.append(error_data)

        return errors

    async def get_error_stats(self, service_name: str) -> Dict[str, Any]:
        """Get error statistics for a service"""
        stats_key = f"error_stats:{service_name}"
        return await redis_client.get_json(stats_key) or {}

    async def mark_error_resolved(self, error_id: str, resolution_notes: str = None):
        """Mark an error as resolved"""
        error_key = f"service_error:{error_id}"
        error_data = await redis_client.get_json(error_key)

        if error_data:
            error_data["resolved"] = True
            error_data["resolution_notes"] = resolution_notes
            error_data["resolved_at"] = datetime.utcnow().isoformat()
            await redis_client.set_json(error_key, error_data, 604800)

    @asynccontextmanager
    async def with_error_handling(self, context: ErrorContext):
        """Context manager for automatic error handling"""
        try:
            yield
        except Exception as e:
            await self.handle_error(e, context)
            raise


# Global error handler instance
error_handler = ExternalServiceErrorHandler()


# Error callback functions


async def handle_authentication_error(error: ServiceError):
    """Handle authentication errors"""
    logger.warning(
        f"Authentication error in {error.context.service_name}, may need to refresh tokens"
    )

    # Store authentication failure
    auth_failure_key = f"auth_failure:{error.context.service_name}"
    await redis_client.set(auth_failure_key, "failed", 300)  # 5 minutes


async def handle_rate_limit_error(error: ServiceError):
    """Handle rate limit errors"""
    logger.info(
        f"Rate limit hit for {error.context.service_name}, implementing backoff"
    )

    # Store rate limit status
    rate_limit_key = f"rate_limit:{error.context.service_name}"
    await redis_client.set_json(
        rate_limit_key,
        {
            "status": "rate_limited",
            "timestamp": datetime.utcnow().isoformat(),
            "service": error.context.service_name,
        },
        1800,  # 30 minutes
    )


async def handle_server_error(error: ServiceError):
    """Handle server errors"""
    logger.error(f"Server error in {error.context.service_name}, service may be down")

    # Check if we should trigger circuit breaker
    circuit_breaker = error_handler.get_circuit_breaker(error.context.service_name)
    # Circuit breaker logic is handled in the CircuitBreaker class


# Register default error callbacks
error_handler.register_error_callback(
    ErrorCategory.AUTHENTICATION, handle_authentication_error
)
error_handler.register_error_callback(ErrorCategory.RATE_LIMIT, handle_rate_limit_error)
error_handler.register_error_callback(ErrorCategory.SERVER_ERROR, handle_server_error)


# Utility functions for external services


async def with_retry_and_circuit_breaker(
    service_name: str,
    operation: str,
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    *args,
    **kwargs,
) -> Any:
    """Execute function with retry logic and circuit breaker"""
    circuit_breaker = error_handler.get_circuit_breaker(service_name)

    context = ErrorContext(service_name=service_name, operation=operation)

    for attempt in range(max_retries + 1):
        try:
            return await circuit_breaker.call(func, *args, **kwargs)

        except Exception as e:
            if attempt < max_retries:
                # Calculate delay with exponential backoff
                delay = base_delay * (2**attempt)

                # Handle the error but don't raise yet
                service_error = await error_handler.handle_error(e, context)
                service_error.retry_count = attempt + 1

                logger.info(
                    f"Retrying {operation} for {service_name} in {delay}s (attempt {attempt + 1})"
                )
                await asyncio.sleep(delay)
                continue

            # Final attempt failed
            await error_handler.handle_error(e, context)
            raise


async def get_service_health_summary() -> Dict[str, Any]:
    """Get health summary for all external services"""
    from .base_service import external_service_manager

    service_status = await external_service_manager.get_all_service_status()
    health_checks = await external_service_manager.health_check_all()

    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
        "overall_health": "healthy",
    }

    unhealthy_count = 0

    for service_name in service_status.keys():
        error_stats = await error_handler.get_error_stats(service_name)
        recent_errors = await error_handler.get_service_errors(service_name, 10)

        is_healthy = health_checks.get(service_name, False)
        if not is_healthy:
            unhealthy_count += 1

        summary["services"][service_name] = {
            "status": service_status[service_name],
            "healthy": is_healthy,
            "error_stats": error_stats,
            "recent_errors_count": len(recent_errors),
            "circuit_breaker_state": error_handler.circuit_breakers.get(
                service_name, CircuitBreaker(service_name, CircuitBreakerConfig())
            ).state.value,
        }

    # Determine overall health
    total_services = len(service_status)
    if unhealthy_count == 0:
        summary["overall_health"] = "healthy"
    elif unhealthy_count < total_services / 2:
        summary["overall_health"] = "degraded"
    else:
        summary["overall_health"] = "unhealthy"

    return summary
