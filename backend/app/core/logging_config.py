"""
Comprehensive logging configuration for production monitoring
"""
import logging
import logging.config
import json
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import traceback
import os

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'organization_id'):
            log_entry['organization_id'] = record.organization_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
        if hasattr(record, 'user_agent'):
            log_entry['user_agent'] = record.user_agent
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'response_time'):
            log_entry['response_time'] = record.response_time
        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type
        if hasattr(record, 'error_details'):
            log_entry['error_details'] = record.error_details
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add stack trace for errors
        if record.levelno >= logging.ERROR and not record.exc_info:
            log_entry['stack_trace'] = traceback.format_stack()
        
        return json.dumps(log_entry, default=str)


class SecurityLogFilter(logging.Filter):
    """
    Filter for security-related log events
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter security events"""
        security_keywords = [
            'authentication', 'authorization', 'login', 'logout',
            'permission', 'access_denied', 'security', 'breach',
            'attack', 'suspicious', 'blocked', 'rate_limit'
        ]
        
        message = record.getMessage().lower()
        return any(keyword in message for keyword in security_keywords)


class PerformanceLogFilter(logging.Filter):
    """
    Filter for performance-related log events
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter performance events"""
        return (
            hasattr(record, 'response_time') or
            'slow' in record.getMessage().lower() or
            'performance' in record.getMessage().lower() or
            'timeout' in record.getMessage().lower()
        )


class ErrorLogFilter(logging.Filter):
    """
    Filter for error and exception events
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter error events"""
        return record.levelno >= logging.ERROR


def setup_logging():
    """
    Set up comprehensive logging configuration
    """
    
    # Create logs directory if it doesn't exist
    log_dir = "/app/logs" if settings.ENVIRONMENT == "production" else "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "%(levelname)s - %(message)s"
            }
        },
        "filters": {
            "security": {
                "()": SecurityLogFilter,
            },
            "performance": {
                "()": PerformanceLogFilter,
            },
            "error": {
                "()": ErrorLogFilter,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "json" if settings.ENVIRONMENT == "production" else "detailed",
                "stream": sys.stdout
            },
            "file_all": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "json",
                "filename": f"{log_dir}/application.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "file_error": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filename": f"{log_dir}/error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf8",
                "filters": ["error"]
            },
            "file_security": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": f"{log_dir}/security.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf8",
                "filters": ["security"]
            },
            "file_performance": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": f"{log_dir}/performance.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
                "filters": ["performance"]
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": settings.LOG_LEVEL,
                "handlers": ["console", "file_all"],
                "propagate": False
            },
            "app": {
                "level": "DEBUG",
                "handlers": ["console", "file_all", "file_error", "file_security", "file_performance"],
                "propagate": False
            },
            "app.security": {
                "level": "INFO",
                "handlers": ["console", "file_security"],
                "propagate": False
            },
            "app.performance": {
                "level": "INFO",
                "handlers": ["console", "file_performance"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file_all"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file_all"],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["console", "file_all"],
                "propagate": False
            },
            "celery": {
                "level": "INFO",
                "handlers": ["console", "file_all"],
                "propagate": False
            }
        }
    }
    
    # Apply logging configuration
    logging.config.dictConfig(config)
    
    # Set up structured logging for FastAPI
    setup_fastapi_logging()


def setup_fastapi_logging():
    """
    Set up FastAPI-specific logging
    """
    import uvicorn.logging
    
    # Configure uvicorn logging
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    
    # Use JSON formatter for production
    if settings.ENVIRONMENT == "production":
        for handler in uvicorn_logger.handlers:
            handler.setFormatter(JSONFormatter())
        for handler in uvicorn_access_logger.handlers:
            handler.setFormatter(JSONFormatter())


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name
    """
    return logging.getLogger(name)


def log_security_event(
    event_type: str,
    message: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
):
    """
    Log a security event with structured data
    """
    logger = get_logger("app.security")
    
    extra = {
        "event_type": event_type,
        "user_id": user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }
    
    if additional_data:
        extra.update(additional_data)
    
    logger.info(message, extra=extra)


def log_performance_event(
    operation: str,
    duration: float,
    message: str,
    user_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
):
    """
    Log a performance event with timing data
    """
    logger = get_logger("app.performance")
    
    extra = {
        "operation": operation,
        "duration": duration,
        "user_id": user_id,
    }
    
    if additional_data:
        extra.update(additional_data)
    
    logger.info(message, extra=extra)


def log_api_request(
    method: str,
    endpoint: str,
    status_code: int,
    response_time: float,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None
):
    """
    Log an API request with structured data
    """
    logger = get_logger("app")
    
    extra = {
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "response_time": response_time,
        "user_id": user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "request_id": request_id,
    }
    
    level = logging.ERROR if status_code >= 500 else logging.WARNING if status_code >= 400 else logging.INFO
    logger.log(level, f"{method} {endpoint} - {status_code} - {response_time:.3f}s", extra=extra)


def log_database_operation(
    operation: str,
    table: str,
    duration: float,
    rows_affected: Optional[int] = None,
    user_id: Optional[str] = None
):
    """
    Log a database operation with performance data
    """
    logger = get_logger("app.performance")
    
    extra = {
        "operation": operation,
        "table": table,
        "duration": duration,
        "rows_affected": rows_affected,
        "user_id": user_id,
    }
    
    message = f"Database {operation} on {table} - {duration:.3f}s"
    if rows_affected is not None:
        message += f" - {rows_affected} rows"
    
    logger.info(message, extra=extra)


def log_external_api_call(
    service: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time: float,
    user_id: Optional[str] = None
):
    """
    Log an external API call
    """
    logger = get_logger("app.performance")
    
    extra = {
        "service": service,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "response_time": response_time,
        "user_id": user_id,
    }
    
    level = logging.ERROR if status_code >= 500 else logging.WARNING if status_code >= 400 else logging.INFO
    logger.log(level, f"External API call to {service} - {method} {endpoint} - {status_code} - {response_time:.3f}s", extra=extra)


# Initialize logging when module is imported
if not logging.getLogger().handlers:
    setup_logging()
