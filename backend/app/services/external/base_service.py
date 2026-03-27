"""
Base service for external API integrations
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import httpx

from app.core.redis import redis_client

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """External service status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"


@dataclass
class ServiceResponse:
    """Standardized response from external services"""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None
    response_time_ms: Optional[float] = None


@dataclass
class RetryConfig:
    """Configuration for retry logic"""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class BaseExternalService(ABC):
    """Base class for external service integrations"""

    def __init__(
        self,
        service_name: str,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.service_name = service_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.status = ServiceStatus.ACTIVE

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout), headers=self._get_default_headers()
        )

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests"""
        headers = {
            "User-Agent": f"ReviveAI/{self.service_name}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.api_key:
            headers.update(self._get_auth_headers())

        return headers

    @abstractmethod
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers (implemented by subclasses)"""
        pass

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ServiceResponse:
        """Make HTTP request with retry logic and error handling"""

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = self._get_default_headers()
        if headers:
            request_headers.update(headers)

        start_time = datetime.utcnow()

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # Make the request
                response = await self.client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers,
                )

                # Calculate response time
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                # Parse rate limit headers
                rate_limit_remaining = self._parse_rate_limit_remaining(
                    response.headers
                )
                rate_limit_reset = self._parse_rate_limit_reset(response.headers)

                # Handle successful responses
                if response.status_code < 400:
                    try:
                        response_data = response.json() if response.content else {}
                    except json.JSONDecodeError:
                        response_data = {"raw_response": response.text}

                    await self._log_request(
                        method, url, response.status_code, response_time, True
                    )

                    return ServiceResponse(
                        success=True,
                        data=response_data,
                        status_code=response.status_code,
                        rate_limit_remaining=rate_limit_remaining,
                        rate_limit_reset=rate_limit_reset,
                        response_time_ms=response_time,
                    )

                # Handle client errors (4xx) - don't retry
                elif 400 <= response.status_code < 500:
                    error_msg = await self._parse_error_response(response)

                    # Handle rate limiting
                    if response.status_code == 429:
                        self.status = ServiceStatus.RATE_LIMITED
                        await self._handle_rate_limit(response.headers)

                    await self._log_request(
                        method, url, response.status_code, response_time, False
                    )

                    return ServiceResponse(
                        success=False,
                        error=error_msg,
                        status_code=response.status_code,
                        rate_limit_remaining=rate_limit_remaining,
                        rate_limit_reset=rate_limit_reset,
                        response_time_ms=response_time,
                    )

                # Handle server errors (5xx) - retry
                else:
                    error_msg = await self._parse_error_response(response)

                    if attempt < self.retry_config.max_retries:
                        delay = self._calculate_retry_delay(attempt)
                        logger.warning(
                            f"Server error from {self.service_name}, retrying in {delay}s",
                            extra={
                                "service": self.service_name,
                                "status_code": response.status_code,
                                "attempt": attempt + 1,
                                "max_retries": self.retry_config.max_retries,
                            },
                        )
                        await asyncio.sleep(delay)
                        continue

                    await self._log_request(
                        method, url, response.status_code, response_time, False
                    )

                    return ServiceResponse(
                        success=False,
                        error=error_msg,
                        status_code=response.status_code,
                        response_time_ms=response_time,
                    )

            except httpx.TimeoutException:
                if attempt < self.retry_config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"Timeout from {self.service_name}, retrying in {delay}s"
                    )
                    await asyncio.sleep(delay)
                    continue

                return ServiceResponse(
                    success=False,
                    error="Request timeout",
                    response_time_ms=(datetime.utcnow() - start_time).total_seconds()
                    * 1000,
                )

            except Exception as e:
                if attempt < self.retry_config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    logger.error(
                        f"Error from {self.service_name}: {e}, retrying in {delay}s"
                    )
                    await asyncio.sleep(delay)
                    continue

                return ServiceResponse(
                    success=False,
                    error=str(e),
                    response_time_ms=(datetime.utcnow() - start_time).total_seconds()
                    * 1000,
                )

        return ServiceResponse(success=False, error="Max retries exceeded")

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay for retry with exponential backoff"""
        delay = self.retry_config.base_delay * (
            self.retry_config.exponential_base**attempt
        )
        delay = min(delay, self.retry_config.max_delay)

        # Add jitter to prevent thundering herd
        if self.retry_config.jitter:
            import random

            delay *= 0.5 + random.random() * 0.5

        return delay

    def _parse_rate_limit_remaining(self, headers: Dict[str, str]) -> Optional[int]:
        """Parse rate limit remaining from headers"""
        # Common rate limit header names
        for header in [
            "X-RateLimit-Remaining",
            "X-Rate-Limit-Remaining",
            "RateLimit-Remaining",
        ]:
            if header in headers:
                try:
                    return int(headers[header])
                except ValueError:
                    pass
        return None

    def _parse_rate_limit_reset(self, headers: Dict[str, str]) -> Optional[datetime]:
        """Parse rate limit reset time from headers"""
        for header in ["X-RateLimit-Reset", "X-Rate-Limit-Reset", "RateLimit-Reset"]:
            if header in headers:
                try:
                    timestamp = int(headers[header])
                    return datetime.fromtimestamp(timestamp)
                except ValueError:
                    pass
        return None

    async def _parse_error_response(self, response: httpx.Response) -> str:
        """Parse error message from response"""
        try:
            error_data = response.json()

            # Common error message fields
            for field in ["error", "message", "detail", "error_description"]:
                if field in error_data:
                    return str(error_data[field])

            return f"HTTP {response.status_code}: {response.text[:200]}"

        except json.JSONDecodeError:
            return f"HTTP {response.status_code}: {response.text[:200]}"

    async def _handle_rate_limit(self, headers: Dict[str, str]):
        """Handle rate limiting"""
        reset_time = self._parse_rate_limit_reset(headers)

        if reset_time:
            # Cache rate limit status
            cache_key = f"rate_limit:{self.service_name}"
            await redis_client.set_json(
                cache_key,
                {
                    "status": "rate_limited",
                    "reset_time": reset_time.isoformat(),
                    "service": self.service_name,
                },
                int((reset_time - datetime.utcnow()).total_seconds()),
            )

    async def _log_request(
        self,
        method: str,
        url: str,
        status_code: int,
        response_time_ms: float,
        success: bool,
    ):
        """Log request details"""
        logger.info(
            f"{self.service_name} API request",
            extra={
                "service": self.service_name,
                "method": method,
                "url": url,
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "success": success,
            },
        )

        # Store metrics in Redis
        metrics_key = f"external_service_metrics:{self.service_name}"
        metrics = await redis_client.get_json(metrics_key) or {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0,
            "last_request": None,
        }

        metrics["total_requests"] += 1
        if success:
            metrics["successful_requests"] += 1
        else:
            metrics["failed_requests"] += 1

        # Update average response time
        metrics["avg_response_time"] = (
            metrics["avg_response_time"] * (metrics["total_requests"] - 1)
            + response_time_ms
        ) / metrics["total_requests"]
        metrics["last_request"] = datetime.utcnow().isoformat()

        await redis_client.set_json(metrics_key, metrics, 86400)  # 24 hours

    async def get_service_status(self) -> Dict[str, Any]:
        """Get current service status and metrics"""
        metrics_key = f"external_service_metrics:{self.service_name}"
        metrics = await redis_client.get_json(metrics_key) or {}

        rate_limit_key = f"rate_limit:{self.service_name}"
        rate_limit_info = await redis_client.get_json(rate_limit_key)

        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "base_url": self.base_url,
            "metrics": metrics,
            "rate_limit_info": rate_limit_info,
            "last_check": datetime.utcnow().isoformat(),
        }

    async def health_check(self) -> bool:
        """Perform health check on the service"""
        try:
            response = await self._make_request("GET", "/health")
            return response.success
        except Exception:
            return False

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    async def test_connection(self) -> ServiceResponse:
        """Test connection to the service"""
        pass


class ExternalServiceManager:
    """Manager for all external services"""

    def __init__(self):
        self.services: Dict[str, BaseExternalService] = {}

    def register_service(self, service: BaseExternalService):
        """Register an external service"""
        self.services[service.service_name] = service
        logger.info(f"Registered external service: {service.service_name}")

    def get_service(self, service_name: str) -> Optional[BaseExternalService]:
        """Get a registered service"""
        return self.services.get(service_name)

    async def get_all_service_status(self) -> Dict[str, Any]:
        """Get status of all registered services"""
        status = {}

        for name, service in self.services.items():
            try:
                status[name] = await service.get_service_status()
            except Exception as e:
                status[name] = {
                    "service_name": name,
                    "status": "error",
                    "error": str(e),
                }

        return status

    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health check on all services"""
        results = {}

        for name, service in self.services.items():
            try:
                results[name] = await service.health_check()
            except Exception:
                results[name] = False

        return results

    async def close_all(self):
        """Close all service connections"""
        for service in self.services.values():
            try:
                await service.close()
            except Exception as e:
                logger.error(f"Error closing service {service.service_name}: {e}")


# Global service manager
external_service_manager = ExternalServiceManager()
