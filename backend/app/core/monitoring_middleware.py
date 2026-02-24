"""
Comprehensive monitoring middleware for FastAPI
"""
import time
import uuid
from typing import Callable, Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
import logging

from app.core.logging_config import log_api_request, log_security_event, log_performance_event
from app.core.metrics import track_api_request, increment_counter, set_gauge, record_histogram
from app.core.error_tracking import add_breadcrumb, set_user_context, set_tag, capture_exception

logger = logging.getLogger("app.monitoring")


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive monitoring middleware that tracks:
    - Request/response metrics
    - Performance timing
    - Error rates
    - Security events
    - User activity
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.active_requests = 0
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Track active requests
        self.active_requests += 1
        set_gauge("api.active_requests", self.active_requests)
        
        # Extract request information
        method = request.method
        url_path = request.url.path
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Add breadcrumb for request tracking
        add_breadcrumb(
            f"HTTP Request: {method} {url_path}",
            category="http",
            data={
                "method": method,
                "url": str(request.url),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "request_id": request_id
            }
        )
        
        # Set tags for error tracking
        set_tag("request_id", request_id)
        set_tag("endpoint", url_path)
        set_tag("method", method)
        
        # Track request start
        increment_counter("api.requests.started", tags={
            "method": method,
            "endpoint": url_path
        })
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Extract user information if available
            user_id = getattr(request.state, 'user_id', None)
            organization_id = getattr(request.state, 'organization_id', None)
            
            # Set user context for error tracking
            if user_id:
                set_user_context(user_id, organization_id)
            
            # Track successful request
            self._track_request_completion(
                method=method,
                endpoint=url_path,
                status_code=response.status_code,
                response_time=response_time,
                user_id=user_id,
                organization_id=organization_id,
                client_ip=client_ip,
                user_agent=user_agent,
                request_id=request_id
            )
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{response_time:.3f}s"
            
            return response
            
        except Exception as e:
            # Calculate response time for failed requests
            response_time = time.time() - start_time
            
            # Track failed request
            self._track_request_error(
                method=method,
                endpoint=url_path,
                error=e,
                response_time=response_time,
                client_ip=client_ip,
                user_agent=user_agent,
                request_id=request_id
            )
            
            # Capture exception
            capture_exception(
                e,
                context={
                    "request": {
                        "method": method,
                        "url": str(request.url),
                        "headers": dict(request.headers),
                        "client_ip": client_ip,
                        "user_agent": user_agent
                    }
                },
                request_id=request_id,
                tags={
                    "endpoint": url_path,
                    "method": method
                }
            )
            
            raise
        
        finally:
            # Track active requests
            self.active_requests -= 1
            set_gauge("api.active_requests", self.active_requests)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers (from load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"
    
    def _track_request_completion(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        response_time: float,
        user_id: Optional[str],
        organization_id: Optional[str],
        client_ip: str,
        user_agent: str,
        request_id: str
    ):
        """Track completed request metrics and logs"""
        
        # Track API request metrics
        track_api_request(method, endpoint, status_code, response_time)
        
        # Log API request
        log_api_request(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            response_time=response_time,
            user_id=user_id,
            ip_address=client_ip,
            user_agent=user_agent,
            request_id=request_id
        )
        
        # Track performance metrics
        if response_time > 1.0:  # Slow request threshold
            log_performance_event(
                operation="api_request",
                duration=response_time,
                message=f"Slow API request: {method} {endpoint}",
                user_id=user_id,
                additional_data={
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": status_code,
                    "client_ip": client_ip
                }
            )
            
            # Track slow requests
            increment_counter("api.requests.slow", tags={
                "method": method,
                "endpoint": endpoint
            })
        
        # Track security events
        if status_code in [401, 403]:
            log_security_event(
                event_type="access_denied",
                message=f"Access denied: {method} {endpoint}",
                user_id=user_id,
                ip_address=client_ip,
                user_agent=user_agent,
                additional_data={
                    "status_code": status_code,
                    "endpoint": endpoint,
                    "method": method
                }
            )
        
        # Track user activity
        if user_id and organization_id:
            increment_counter("user.activity", tags={
                "user_id": user_id,
                "organization_id": organization_id,
                "endpoint": endpoint,
                "method": method
            })
        
        # Add breadcrumb for successful completion
        add_breadcrumb(
            f"HTTP Response: {status_code} - {response_time:.3f}s",
            category="http",
            data={
                "status_code": status_code,
                "response_time": response_time,
                "request_id": request_id
            }
        )
    
    def _track_request_error(
        self,
        method: str,
        endpoint: str,
        error: Exception,
        response_time: float,
        client_ip: str,
        user_agent: str,
        request_id: str
    ):
        """Track failed request metrics and logs"""
        
        error_type = type(error).__name__
        
        # Track error metrics
        increment_counter("api.requests.errors", tags={
            "method": method,
            "endpoint": endpoint,
            "error_type": error_type
        })
        
        # Track error response time
        record_histogram("api.requests.error_duration", response_time * 1000, tags={
            "method": method,
            "endpoint": endpoint,
            "error_type": error_type
        })
        
        # Log error
        logger.error(
            f"API request failed: {method} {endpoint} - {error_type}: {str(error)}",
            exc_info=error,
            extra={
                "method": method,
                "endpoint": endpoint,
                "error_type": error_type,
                "response_time": response_time,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "request_id": request_id
            }
        )
        
        # Add breadcrumb for error
        add_breadcrumb(
            f"HTTP Error: {error_type} - {response_time:.3f}s",
            category="http",
            level="error",
            data={
                "error_type": error_type,
                "error_message": str(error),
                "response_time": response_time,
                "request_id": request_id
            }
        )


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track application health metrics
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.startup_time = time.time()
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Track uptime
        uptime = time.time() - self.startup_time
        set_gauge("app.uptime_seconds", uptime)
        
        # Process request
        response = await call_next(request)
        
        # Track health check requests separately
        if request.url.path.startswith("/health"):
            increment_counter("health_checks.total", tags={
                "endpoint": request.url.path,
                "status_code": str(response.status_code)
            })
        
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track rate limiting metrics
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.request_counts = {}
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = self._get_client_ip(request)
        
        # Track requests per IP
        current_time = int(time.time() / 60)  # Per minute
        key = f"{client_ip}:{current_time}"
        
        if key not in self.request_counts:
            self.request_counts[key] = 0
        self.request_counts[key] += 1
        
        # Clean old entries
        self._cleanup_old_entries(current_time)
        
        # Track rate limiting metrics
        set_gauge("rate_limiting.requests_per_minute", self.request_counts.get(key, 0), tags={
            "client_ip": client_ip
        })
        
        # Check for potential abuse
        if self.request_counts.get(key, 0) > 100:  # More than 100 requests per minute
            log_security_event(
                event_type="rate_limit_exceeded",
                message=f"High request rate from IP: {client_ip}",
                ip_address=client_ip,
                additional_data={
                    "requests_per_minute": self.request_counts[key],
                    "endpoint": request.url.path
                }
            )
            
            increment_counter("security.rate_limit_exceeded", tags={
                "client_ip": client_ip
            })
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"
    
    def _cleanup_old_entries(self, current_time: int):
        """Clean up old rate limiting entries"""
        cutoff_time = current_time - 5  # Keep last 5 minutes
        keys_to_remove = [key for key in self.request_counts.keys() 
                         if int(key.split(':')[1]) < cutoff_time]
        
        for key in keys_to_remove:
            del self.request_counts[key]


def setup_monitoring_middleware(app: FastAPI):
    """
    Set up all monitoring middleware for the FastAPI application
    """
    # Add middleware in reverse order (last added is executed first)
    app.add_middleware(RateLimitingMiddleware)
    app.add_middleware(HealthCheckMiddleware)
    app.add_middleware(MonitoringMiddleware)
    
    logger.info("Monitoring middleware configured successfully")
