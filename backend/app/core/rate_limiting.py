"""
Advanced rate limiting service with multiple strategies and user tiers
"""
import time
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from app.core.redis import redis_client

logger = logging.getLogger(__name__)


class UserTier(Enum):
    """User tier enumeration for different rate limits"""
    ANONYMOUS = "anonymous"
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"


@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests: int
    window_seconds: int
    burst_requests: Optional[int] = None  # Allow burst above normal rate


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    limit_type: str = "requests"


class RateLimitConfig:
    """Configuration for different rate limits by user tier and endpoint"""
    
    # Global rate limits by user tier (requests per minute)
    GLOBAL_LIMITS = {
        UserTier.ANONYMOUS: RateLimit(requests=30, window_seconds=60),
        UserTier.FREE: RateLimit(requests=100, window_seconds=60),
        UserTier.PREMIUM: RateLimit(requests=500, window_seconds=60),
        UserTier.ENTERPRISE: RateLimit(requests=2000, window_seconds=60),
        UserTier.ADMIN: RateLimit(requests=5000, window_seconds=60),
    }
    
    # Endpoint-specific rate limits (requests per minute)
    ENDPOINT_LIMITS = {
        # Authentication endpoints (stricter limits)
        "/api/v1/auth/login": {
            UserTier.ANONYMOUS: RateLimit(requests=5, window_seconds=60),
            UserTier.FREE: RateLimit(requests=10, window_seconds=60),
            UserTier.PREMIUM: RateLimit(requests=20, window_seconds=60),
            UserTier.ENTERPRISE: RateLimit(requests=50, window_seconds=60),
            UserTier.ADMIN: RateLimit(requests=100, window_seconds=60),
        },
        "/api/v1/auth/register": {
            UserTier.ANONYMOUS: RateLimit(requests=3, window_seconds=300),  # 5 minutes
            UserTier.FREE: RateLimit(requests=5, window_seconds=300),
            UserTier.PREMIUM: RateLimit(requests=10, window_seconds=300),
            UserTier.ENTERPRISE: RateLimit(requests=20, window_seconds=300),
            UserTier.ADMIN: RateLimit(requests=50, window_seconds=300),
        },
        
        # Review processing endpoints
        "/api/v1/reviews/ingest": {
            UserTier.FREE: RateLimit(requests=50, window_seconds=60),
            UserTier.PREMIUM: RateLimit(requests=200, window_seconds=60),
            UserTier.ENTERPRISE: RateLimit(requests=1000, window_seconds=60),
            UserTier.ADMIN: RateLimit(requests=2000, window_seconds=60),
        },
        "/api/v1/reviews/analyze": {
            UserTier.FREE: RateLimit(requests=30, window_seconds=60),
            UserTier.PREMIUM: RateLimit(requests=150, window_seconds=60),
            UserTier.ENTERPRISE: RateLimit(requests=500, window_seconds=60),
            UserTier.ADMIN: RateLimit(requests=1000, window_seconds=60),
        },
        
        # Customer recovery endpoints
        "/api/v1/customers/recover": {
            UserTier.FREE: RateLimit(requests=20, window_seconds=60),
            UserTier.PREMIUM: RateLimit(requests=100, window_seconds=60),
            UserTier.ENTERPRISE: RateLimit(requests=300, window_seconds=60),
            UserTier.ADMIN: RateLimit(requests=500, window_seconds=60),
        },
        
        # Agent decision endpoints
        "/api/v1/agents/decide-action": {
            UserTier.FREE: RateLimit(requests=40, window_seconds=60),
            UserTier.PREMIUM: RateLimit(requests=200, window_seconds=60),
            UserTier.ENTERPRISE: RateLimit(requests=800, window_seconds=60),
            UserTier.ADMIN: RateLimit(requests=1500, window_seconds=60),
        },
        
        # Dashboard and metrics (more lenient)
        "/api/v1/dashboard/metrics": {
            UserTier.FREE: RateLimit(requests=60, window_seconds=60),
            UserTier.PREMIUM: RateLimit(requests=300, window_seconds=60),
            UserTier.ENTERPRISE: RateLimit(requests=600, window_seconds=60),
            UserTier.ADMIN: RateLimit(requests=1000, window_seconds=60),
        },
    }
    
    # Burst limits (short-term higher rates)
    BURST_LIMITS = {
        UserTier.FREE: RateLimit(requests=20, window_seconds=10),
        UserTier.PREMIUM: RateLimit(requests=50, window_seconds=10),
        UserTier.ENTERPRISE: RateLimit(requests=200, window_seconds=10),
        UserTier.ADMIN: RateLimit(requests=500, window_seconds=10),
    }


class AdvancedRateLimiter:
    """Advanced rate limiter with multiple algorithms and strategies"""
    
    @staticmethod
    async def check_rate_limit(
        identifier: str,
        user_tier: str,
        endpoint: str = None,
        use_sliding_window: bool = True
    ) -> Dict[str, any]:
        """
        Check rate limits using multiple strategies
        
        Args:
            identifier: Unique identifier (user_id, ip, etc.)
            user_tier: User tier string
            endpoint: Specific endpoint being accessed
            use_sliding_window: Whether to use sliding window algorithm
            
        Returns:
            Dictionary with rate limit information
        """
        try:
            tier = UserTier(user_tier)
        except ValueError:
            tier = UserTier.ANONYMOUS
        
        current_time = int(time.time())
        
        # Check global rate limit
        global_result = await AdvancedRateLimiter._check_global_limit(
            identifier, tier, current_time, use_sliding_window
        )
        
        # Check endpoint-specific rate limit
        endpoint_result = await AdvancedRateLimiter._check_endpoint_limit(
            identifier, tier, endpoint, current_time, use_sliding_window
        )
        
        # Check burst limit
        burst_result = await AdvancedRateLimiter._check_burst_limit(
            identifier, tier, current_time
        )
        
        # Determine overall result
        overall_limited = (
            global_result["limited"] or 
            endpoint_result["limited"] or 
            burst_result["limited"]
        )
        
        return {
            "overall_limited": overall_limited,
            "global": global_result,
            "endpoint": endpoint_result,
            "burst": burst_result,
            "user_tier": user_tier,
            "timestamp": current_time
        }
    
    @staticmethod
    async def _check_global_limit(
        identifier: str, 
        tier: UserTier, 
        current_time: int,
        use_sliding_window: bool
    ) -> Dict[str, any]:
        """Check global rate limit"""
        
        limit_config = RateLimitConfig.GLOBAL_LIMITS.get(tier)
        if not limit_config:
            return {"limited": False, "remaining": 999999, "reset_time": current_time + 60}
        
        key = f"rate_limit:global:{identifier}"
        
        if use_sliding_window:
            return await AdvancedRateLimiter._sliding_window_check(
                key, limit_config, current_time
            )
        else:
            return await AdvancedRateLimiter._fixed_window_check(
                key, limit_config, current_time
            )
    
    @staticmethod
    async def _check_endpoint_limit(
        identifier: str,
        tier: UserTier,
        endpoint: str,
        current_time: int,
        use_sliding_window: bool
    ) -> Dict[str, any]:
        """Check endpoint-specific rate limit"""
        
        if not endpoint:
            return {"limited": False, "remaining": 999999, "reset_time": current_time + 60}
        
        # Get endpoint-specific limit
        endpoint_limits = RateLimitConfig.ENDPOINT_LIMITS.get(endpoint, {})
        limit_config = endpoint_limits.get(tier)
        
        if not limit_config:
            return {"limited": False, "remaining": 999999, "reset_time": current_time + 60}
        
        key = f"rate_limit:endpoint:{endpoint}:{identifier}"
        
        if use_sliding_window:
            return await AdvancedRateLimiter._sliding_window_check(
                key, limit_config, current_time
            )
        else:
            return await AdvancedRateLimiter._fixed_window_check(
                key, limit_config, current_time
            )
    
    @staticmethod
    async def _check_burst_limit(
        identifier: str,
        tier: UserTier,
        current_time: int
    ) -> Dict[str, any]:
        """Check burst rate limit (always uses sliding window)"""
        
        limit_config = RateLimitConfig.BURST_LIMITS.get(tier)
        if not limit_config:
            return {"limited": False, "remaining": 999999, "reset_time": current_time + 10}
        
        key = f"rate_limit:burst:{identifier}"
        
        return await AdvancedRateLimiter._sliding_window_check(
            key, limit_config, current_time
        )
    
    @staticmethod
    async def _sliding_window_check(
        key: str,
        limit_config: RateLimit,
        current_time: int
    ) -> Dict[str, any]:
        """
        Sliding window rate limiting algorithm
        More accurate but slightly more expensive
        """
        
        window_start = current_time - limit_config.window_seconds
        
        try:
            if redis_client.redis:
                # Use Redis sorted set for sliding window
                pipe = redis_client.redis.pipeline()
                
                # Remove old entries
                pipe.zremrangebyscore(key, 0, window_start)
                
                # Count current requests in window
                pipe.zcard(key)
                
                # Add current request
                pipe.zadd(key, {str(current_time): current_time})
                
                # Set expiration
                pipe.expire(key, limit_config.window_seconds + 1)
                
                results = await pipe.execute()
                current_count = results[1] + 1  # +1 for the request we just added
                
            else:
                # Fallback to memory-based tracking (not recommended for production)
                current_count = 1
            
            # Check if limit exceeded
            limited = current_count > limit_config.requests
            remaining = max(0, limit_config.requests - current_count)
            reset_time = current_time + limit_config.window_seconds
            
            return {
                "limited": limited,
                "remaining": remaining,
                "reset_time": reset_time,
                "current_count": current_count,
                "limit": limit_config.requests,
                "window_seconds": limit_config.window_seconds
            }
            
        except Exception as e:
            logger.error(f"Error in sliding window rate limit check: {e}")
            # Fail open - allow request if Redis is down
            return {
                "limited": False,
                "remaining": limit_config.requests,
                "reset_time": current_time + limit_config.window_seconds,
                "error": str(e)
            }
    
    @staticmethod
    async def _fixed_window_check(
        key: str,
        limit_config: RateLimit,
        current_time: int
    ) -> Dict[str, any]:
        """
        Fixed window rate limiting algorithm
        Simpler and more efficient but less accurate
        """
        
        # Calculate window start (aligned to window boundaries)
        window_start = (current_time // limit_config.window_seconds) * limit_config.window_seconds
        window_key = f"{key}:{window_start}"
        
        try:
            if redis_client.redis:
                # Increment counter for this window
                current_count = await redis_client.increment(window_key)
                
                # Set expiration on first request in window
                if current_count == 1:
                    await redis_client.expire(window_key, limit_config.window_seconds + 1)
            else:
                current_count = 1
            
            # Check if limit exceeded
            limited = current_count > limit_config.requests
            remaining = max(0, limit_config.requests - current_count)
            reset_time = window_start + limit_config.window_seconds
            
            return {
                "limited": limited,
                "remaining": remaining,
                "reset_time": reset_time,
                "current_count": current_count,
                "limit": limit_config.requests,
                "window_seconds": limit_config.window_seconds
            }
            
        except Exception as e:
            logger.error(f"Error in fixed window rate limit check: {e}")
            # Fail open - allow request if Redis is down
            return {
                "limited": False,
                "remaining": limit_config.requests,
                "reset_time": current_time + limit_config.window_seconds,
                "error": str(e)
            }
    
    @staticmethod
    async def get_user_tier(user_id: str, organization_id: str) -> str:
        """
        Get user tier from database or cache
        This would typically query the database to get the user's subscription tier
        """
        try:
            # Try to get from cache first
            cache_key = f"user_tier:{user_id}"
            cached_tier = await redis_client.get(cache_key)
            
            if cached_tier:
                return cached_tier
            
            # In a real implementation, this would query the database
            # For now, we'll use a simple heuristic or default
            
            # TODO: Implement actual database query
            # from app.services.user_service import UserService
            # user = await UserService.get_user_with_organization(user_id, organization_id)
            # tier = user.organization.subscription_tier
            
            # Default to free tier for now
            tier = UserTier.FREE.value
            
            # Cache the result
            await redis_client.set(cache_key, tier, expire=300)  # 5 minutes
            
            return tier
            
        except Exception as e:
            logger.error(f"Error getting user tier for {user_id}: {e}")
            return UserTier.FREE.value  # Default to free tier on error
    
    @staticmethod
    def get_rate_limit_headers(rate_limit_info: Dict[str, any]) -> Dict[str, str]:
        """
        Generate standard rate limit headers
        Following the draft RFC for rate limit headers
        """
        headers = {}
        
        # Use the most restrictive limit for headers
        if rate_limit_info["global"]["limited"]:
            limit_info = rate_limit_info["global"]
        elif rate_limit_info["endpoint"]["limited"]:
            limit_info = rate_limit_info["endpoint"]
        elif rate_limit_info["burst"]["limited"]:
            limit_info = rate_limit_info["burst"]
        else:
            # Use global limit info if no limits exceeded
            limit_info = rate_limit_info["global"]
        
        # Standard rate limit headers
        headers["X-RateLimit-Limit"] = str(limit_info.get("limit", 0))
        headers["X-RateLimit-Remaining"] = str(limit_info.get("remaining", 0))
        headers["X-RateLimit-Reset"] = str(limit_info.get("reset_time", 0))
        
        # Additional headers
        headers["X-RateLimit-Window"] = str(limit_info.get("window_seconds", 60))
        headers["X-RateLimit-Policy"] = f"{limit_info.get('limit', 0)};w={limit_info.get('window_seconds', 60)}"
        
        # If limited, add retry-after
        if rate_limit_info["overall_limited"]:
            retry_after = limit_info.get("reset_time", 0) - int(time.time())
            headers["Retry-After"] = str(max(1, retry_after))
        
        return headers
    
    @staticmethod
    async def reset_rate_limits(identifier: str):
        """Reset all rate limits for an identifier (useful for testing or admin override)"""
        try:
            if redis_client.redis:
                # Find all keys for this identifier
                patterns = [
                    f"rate_limit:global:{identifier}*",
                    f"rate_limit:endpoint:*:{identifier}*",
                    f"rate_limit:burst:{identifier}*"
                ]
                
                for pattern in patterns:
                    keys = await redis_client.redis.keys(pattern)
                    if keys:
                        await redis_client.redis.delete(*keys)
                
                logger.info(f"Reset rate limits for identifier: {identifier}")
                
        except Exception as e:
            logger.error(f"Error resetting rate limits for {identifier}: {e}")
    
    @staticmethod
    async def get_rate_limit_stats(identifier: str) -> Dict[str, any]:
        """Get current rate limit statistics for an identifier"""
        try:
            stats = {}
            current_time = int(time.time())
            
            if redis_client.redis:
                # Global stats
                global_key = f"rate_limit:global:{identifier}"
                if await redis_client.redis.exists(global_key):
                    global_count = await redis_client.redis.zcard(global_key)
                    stats["global"] = {"current_count": global_count}
                
                # Endpoint stats
                endpoint_pattern = f"rate_limit:endpoint:*:{identifier}*"
                endpoint_keys = await redis_client.redis.keys(endpoint_pattern)
                
                endpoint_stats = {}
                for key in endpoint_keys:
                    endpoint = key.split(":")[2]  # Extract endpoint from key
                    count = await redis_client.redis.zcard(key)
                    endpoint_stats[endpoint] = {"current_count": count}
                
                stats["endpoints"] = endpoint_stats
                
                # Burst stats
                burst_key = f"rate_limit:burst:{identifier}"
                if await redis_client.redis.exists(burst_key):
                    burst_count = await redis_client.redis.zcard(burst_key)
                    stats["burst"] = {"current_count": burst_count}
            
            stats["timestamp"] = current_time
            return stats
            
        except Exception as e:
            logger.error(f"Error getting rate limit stats for {identifier}: {e}")
            return {"error": str(e), "timestamp": int(time.time())}


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    
    def __init__(self, message: str, retry_after: int, limit_type: str = "requests"):
        self.message = message
        self.retry_after = retry_after
        self.limit_type = limit_type
        super().__init__(self.message)
