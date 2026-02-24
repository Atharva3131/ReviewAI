"""
Comprehensive error tracking and monitoring with Sentry integration
"""
import logging
import traceback
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from functools import wraps
import asyncio

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("app.error_tracking")


class ErrorTracker:
    """
    Comprehensive error tracking and monitoring system
    """
    
    def __init__(self):
        self.initialized = False
        self.error_counts = {}
        self.recent_errors = []
        
        if SENTRY_AVAILABLE and settings.SENTRY_DSN:
            self._initialize_sentry()
        else:
            logger.warning("Sentry not available or DSN not configured, using fallback error tracking")
    
    def _initialize_sentry(self):
        """Initialize Sentry SDK with comprehensive configuration"""
        try:
            # Configure logging integration
            logging_integration = LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            )
            
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.ENVIRONMENT,
                release=settings.APP_VERSION,
                integrations=[
                    FastApiIntegration(auto_enabling_integrations=False),
                    SqlalchemyIntegration(),
                    RedisIntegration(),
                    CeleryIntegration(),
                    logging_integration,
                ],
                # Performance monitoring
                traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
                profiles_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
                
                # Error sampling
                sample_rate=1.0,
                
                # Additional configuration
                attach_stacktrace=True,
                send_default_pii=False,  # Don't send PII by default
                max_breadcrumbs=50,
                
                # Custom error filtering
                before_send=self._before_send_filter,
                before_send_transaction=self._before_send_transaction_filter,
            )
            
            # Set global tags
            sentry_sdk.set_tag("service", "revive-ai-backend")
            sentry_sdk.set_tag("version", settings.APP_VERSION)
            
            self.initialized = True
            logger.info("Sentry error tracking initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
            self.initialized = False
    
    def _before_send_filter(self, event, hint):
        """Filter events before sending to Sentry"""
        # Don't send certain types of errors
        if 'exc_info' in hint:
            exc_type, exc_value, tb = hint['exc_info']
            
            # Filter out common non-critical errors
            if exc_type.__name__ in ['KeyboardInterrupt', 'SystemExit']:
                return None
            
            # Filter out specific HTTP errors that are expected
            if hasattr(exc_value, 'status_code'):
                if exc_value.status_code in [400, 401, 403, 404]:
                    return None
        
        # Add custom context
        event['extra']['server_name'] = settings.SERVER_NAME
        event['extra']['environment'] = settings.ENVIRONMENT
        
        return event
    
    def _before_send_transaction_filter(self, event, hint):
        """Filter transaction events before sending to Sentry"""
        # Don't track health check endpoints
        if event.get('transaction') in ['/health', '/health/ready', '/health/live']:
            return None
        
        return event
    
    def capture_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        request_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        level: str = "error"
    ):
        """
        Capture an exception with additional context
        """
        # Track error locally
        self._track_error_locally(exception, context)
        
        if self.initialized and SENTRY_AVAILABLE:
            # Set Sentry context
            with sentry_sdk.push_scope() as scope:
                # Set user context
                if user_id or organization_id:
                    scope.set_user({
                        "id": user_id,
                        "organization_id": organization_id
                    })
                
                # Set tags
                if tags:
                    for key, value in tags.items():
                        scope.set_tag(key, value)
                
                # Set additional context
                if context:
                    scope.set_context("additional_info", context)
                
                if request_id:
                    scope.set_tag("request_id", request_id)
                
                # Set level
                scope.level = level
                
                # Capture the exception
                sentry_sdk.capture_exception(exception)
        
        # Log the error
        logger.error(
            f"Exception captured: {type(exception).__name__}: {str(exception)}",
            exc_info=exception,
            extra={
                "user_id": user_id,
                "organization_id": organization_id,
                "request_id": request_id,
                "context": context,
                "tags": tags
            }
        )
    
    def capture_message(
        self,
        message: str,
        level: str = "info",
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Capture a custom message
        """
        if self.initialized and SENTRY_AVAILABLE:
            with sentry_sdk.push_scope() as scope:
                # Set user context
                if user_id or organization_id:
                    scope.set_user({
                        "id": user_id,
                        "organization_id": organization_id
                    })
                
                # Set tags
                if tags:
                    for key, value in tags.items():
                        scope.set_tag(key, value)
                
                # Set additional context
                if context:
                    scope.set_context("additional_info", context)
                
                # Set level
                scope.level = level
                
                # Capture the message
                sentry_sdk.capture_message(message, level)
        
        # Log the message
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(
            log_level,
            message,
            extra={
                "user_id": user_id,
                "organization_id": organization_id,
                "context": context,
                "tags": tags
            }
        )
    
    def add_breadcrumb(
        self,
        message: str,
        category: str = "custom",
        level: str = "info",
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Add a breadcrumb for debugging context
        """
        if self.initialized and SENTRY_AVAILABLE:
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                level=level,
                data=data or {}
            )
    
    def set_user_context(self, user_id: str, organization_id: Optional[str] = None, email: Optional[str] = None):
        """
        Set user context for error tracking
        """
        if self.initialized and SENTRY_AVAILABLE:
            sentry_sdk.set_user({
                "id": user_id,
                "organization_id": organization_id,
                "email": email
            })
    
    def set_tag(self, key: str, value: str):
        """
        Set a tag for error tracking
        """
        if self.initialized and SENTRY_AVAILABLE:
            sentry_sdk.set_tag(key, value)
    
    def _track_error_locally(self, exception: Exception, context: Optional[Dict[str, Any]] = None):
        """
        Track error locally for fallback monitoring
        """
        error_type = type(exception).__name__
        error_message = str(exception)
        
        # Count errors by type
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Store recent errors (keep last 100)
        error_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": error_type,
            "message": error_message,
            "traceback": traceback.format_exc(),
            "context": context
        }
        
        self.recent_errors.append(error_info)
        if len(self.recent_errors) > 100:
            self.recent_errors = self.recent_errors[-100:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get a summary of recent errors
        """
        return {
            "error_counts": self.error_counts,
            "recent_errors": self.recent_errors[-10:],  # Last 10 errors
            "total_errors": sum(self.error_counts.values()),
            "unique_error_types": len(self.error_counts)
        }


# Global error tracker instance
error_tracker = ErrorTracker()


# Convenience functions
def capture_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    request_id: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    level: str = "error"
):
    """Capture an exception with additional context"""
    error_tracker.capture_exception(exception, context, user_id, organization_id, request_id, tags, level)


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
):
    """Capture a custom message"""
    error_tracker.capture_message(message, level, context, user_id, organization_id, tags)


def add_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
):
    """Add a breadcrumb for debugging context"""
    error_tracker.add_breadcrumb(message, category, level, data)


def set_user_context(user_id: str, organization_id: Optional[str] = None, email: Optional[str] = None):
    """Set user context for error tracking"""
    error_tracker.set_user_context(user_id, organization_id, email)


def set_tag(key: str, value: str):
    """Set a tag for error tracking"""
    error_tracker.set_tag(key, value)


# Decorators for automatic error tracking
def track_errors(
    operation_name: Optional[str] = None,
    capture_args: bool = False,
    capture_result: bool = False
):
    """
    Decorator to automatically track errors in functions
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                add_breadcrumb(f"Starting operation: {op_name}", category="operation")
                
                if capture_args:
                    add_breadcrumb(
                        f"Operation arguments",
                        category="operation",
                        data={"args": str(args), "kwargs": str(kwargs)}
                    )
                
                result = await func(*args, **kwargs)
                
                if capture_result:
                    add_breadcrumb(
                        f"Operation completed successfully",
                        category="operation",
                        data={"result": str(result)[:1000]}  # Limit result size
                    )
                
                return result
                
            except Exception as e:
                capture_exception(
                    e,
                    context={
                        "operation": op_name,
                        "args": str(args) if capture_args else None,
                        "kwargs": str(kwargs) if capture_args else None
                    },
                    tags={"operation": op_name}
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                add_breadcrumb(f"Starting operation: {op_name}", category="operation")
                
                if capture_args:
                    add_breadcrumb(
                        f"Operation arguments",
                        category="operation",
                        data={"args": str(args), "kwargs": str(kwargs)}
                    )
                
                result = func(*args, **kwargs)
                
                if capture_result:
                    add_breadcrumb(
                        f"Operation completed successfully",
                        category="operation",
                        data={"result": str(result)[:1000]}  # Limit result size
                    )
                
                return result
                
            except Exception as e:
                capture_exception(
                    e,
                    context={
                        "operation": op_name,
                        "args": str(args) if capture_args else None,
                        "kwargs": str(kwargs) if capture_args else None
                    },
                    tags={"operation": op_name}
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Context manager for error tracking
class ErrorTrackingContext:
    """Context manager for tracking errors in code blocks"""
    
    def __init__(
        self,
        operation_name: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        self.operation_name = operation_name
        self.user_id = user_id
        self.organization_id = organization_id
        self.tags = tags or {}
    
    def __enter__(self):
        add_breadcrumb(f"Starting operation: {self.operation_name}", category="operation")
        if self.user_id:
            set_user_context(self.user_id, self.organization_id)
        for key, value in self.tags.items():
            set_tag(key, value)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            capture_exception(
                exc_val,
                context={"operation": self.operation_name},
                user_id=self.user_id,
                organization_id=self.organization_id,
                tags=self.tags
            )
        else:
            add_breadcrumb(f"Operation completed successfully: {self.operation_name}", category="operation")


def track_operation(
    operation_name: str,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
):
    """Context manager for tracking operations"""
    return ErrorTrackingContext(operation_name, user_id, organization_id, tags)
