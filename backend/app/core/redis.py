"""
Redis configuration and utilities
"""
import redis.asyncio as redis
from typing import Optional, Any
import json
import pickle
import time
from app.core.config import settings


class RedisClient:
    """Redis client wrapper with common operations"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        self.redis = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self.redis:
            await self.connect()
        return await self.redis.get(key)
    
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set key-value pair with optional expiration"""
        if not self.redis:
            await self.connect()
        return await self.redis.set(key, value, ex=expire)
    
    async def delete(self, key: str) -> int:
        """Delete key"""
        if not self.redis:
            await self.connect()
        return await self.redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis:
            await self.connect()
        return await self.redis.exists(key)
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key"""
        if not self.redis:
            await self.connect()
        return await self.redis.expire(key, seconds)
    
    async def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value by key"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    async def set_json(self, key: str, value: dict, expire: Optional[int] = None) -> bool:
        """Set JSON value with optional expiration"""
        json_value = json.dumps(value)
        return await self.set(key, json_value, expire)
    
    async def get_object(self, key: str) -> Optional[Any]:
        """Get pickled object by key"""
        if not self.redis:
            await self.connect()
        value = await self.redis.get(key)
        if value:
            try:
                return pickle.loads(value)
            except (pickle.PickleError, TypeError):
                return None
        return None
    
    async def set_object(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set pickled object with optional expiration"""
        if not self.redis:
            await self.connect()
        pickled_value = pickle.dumps(value)
        return await self.redis.set(key, pickled_value, ex=expire)
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        if not self.redis:
            await self.connect()
        return await self.redis.incr(key, amount)
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement counter"""
        if not self.redis:
            await self.connect()
        return await self.redis.decr(key, amount)


# Global Redis client instance
redis_client = RedisClient()


# Cache decorators and utilities
class CacheManager:
    """Cache management utilities"""
    
    @staticmethod
    def make_key(*args, prefix: str = "revive_ai") -> str:
        """Create cache key from arguments"""
        key_parts = [str(arg) for arg in args]
        return f"{prefix}:{':'.join(key_parts)}"
    
    @staticmethod
    async def get_or_set(
        key: str, 
        fetch_func, 
        expire: int = 3600,
        use_json: bool = True
    ) -> Any:
        """Get from cache or fetch and set"""
        # Try to get from cache
        if use_json:
            cached_value = await redis_client.get_json(key)
        else:
            cached_value = await redis_client.get_object(key)
        
        if cached_value is not None:
            return cached_value
        
        # Fetch fresh data
        fresh_value = await fetch_func()
        
        # Cache the result
        if use_json:
            await redis_client.set_json(key, fresh_value, expire)
        else:
            await redis_client.set_object(key, fresh_value, expire)
        
        return fresh_value


# Session management
class SessionManager:
    """Session management using Redis"""
    
    SESSION_PREFIX = "session"
    DEFAULT_EXPIRE = 60 * 60 * 24 * 7  # 7 days
    
    @classmethod
    async def create_session(cls, user_id: str, session_data: dict) -> str:
        """Create new session"""
        import uuid
        session_id = str(uuid.uuid4())
        session_key = cls.make_session_key(session_id)
        
        session_data.update({
            "user_id": user_id,
            "created_at": int(time.time())
        })
        
        await redis_client.set_json(session_key, session_data, cls.DEFAULT_EXPIRE)
        return session_id
    
    @classmethod
    async def get_session(cls, session_id: str) -> Optional[dict]:
        """Get session data"""
        session_key = cls.make_session_key(session_id)
        return await redis_client.get_json(session_key)
    
    @classmethod
    async def update_session(cls, session_id: str, session_data: dict) -> bool:
        """Update session data"""
        session_key = cls.make_session_key(session_id)
        existing_session = await cls.get_session(session_id)
        
        if existing_session:
            existing_session.update(session_data)
            return await redis_client.set_json(session_key, existing_session, cls.DEFAULT_EXPIRE)
        return False
    
    @classmethod
    async def delete_session(cls, session_id: str) -> bool:
        """Delete session"""
        session_key = cls.make_session_key(session_id)
        return await redis_client.delete(session_key) > 0
    
    @classmethod
    async def extend_session(cls, session_id: str) -> bool:
        """Extend session expiration"""
        session_key = cls.make_session_key(session_id)
        return await redis_client.expire(session_key, cls.DEFAULT_EXPIRE)
    
    @classmethod
    def make_session_key(cls, session_id: str) -> str:
        """Create session key"""
        return f"{cls.SESSION_PREFIX}:{session_id}"


# Rate limiting
class RateLimiter:
    """Advanced rate limiting using Redis with multiple strategies"""
    
    @staticmethod
    async def is_rate_limited(
        key: str, 
        limit: int, 
        window: int = 60
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded using sliding window
        Returns (is_limited, remaining_requests)
        """
        current_count = await redis_client.get(key)
        
        if current_count is None:
            # First request in window
            await redis_client.set(key, "1", window)
            return False, limit - 1
        
        current_count = int(current_count)
        
        if current_count >= limit:
            return True, 0
        
        # Increment counter
        new_count = await redis_client.increment(key)
        remaining = max(0, limit - new_count)
        
        return False, remaining
    
    @staticmethod
    async def sliding_window_rate_limit(
        key: str,
        limit: int,
        window: int = 60
    ) -> tuple[bool, int, int]:
        """
        Sliding window rate limiting with more accurate counting
        Returns (is_limited, remaining_requests, reset_time)
        """
        if not redis_client.redis:
            await redis_client.connect()
        
        now = int(time.time())
        pipeline = redis_client.redis.pipeline()
        
        # Remove expired entries
        pipeline.zremrangebyscore(key, 0, now - window)
        
        # Count current requests in window
        pipeline.zcard(key)
        
        # Add current request
        pipeline.zadd(key, {str(now): now})
        
        # Set expiration
        pipeline.expire(key, window)
        
        results = await pipeline.execute()
        current_count = results[1]
        
        if current_count >= limit:
            # Remove the request we just added since it's over limit
            await redis_client.redis.zrem(key, str(now))
            return True, 0, now + window
        
        remaining = limit - current_count - 1  # -1 for the request we just added
        reset_time = now + window
        
        return False, remaining, reset_time
    
    @staticmethod
    async def token_bucket_rate_limit(
        key: str,
        capacity: int,
        refill_rate: float,
        tokens_requested: int = 1
    ) -> tuple[bool, int]:
        """
        Token bucket rate limiting
        Returns (is_allowed, tokens_remaining)
        """
        if not redis_client.redis:
            await redis_client.connect()
        
        now = time.time()
        bucket_key = f"bucket:{key}"
        
        # Get current bucket state
        bucket_data = await redis_client.get_json(bucket_key)
        
        if bucket_data is None:
            # Initialize bucket
            bucket_data = {
                "tokens": capacity,
                "last_refill": now
            }
        else:
            # Refill tokens based on time elapsed
            time_elapsed = now - bucket_data["last_refill"]
            tokens_to_add = int(time_elapsed * refill_rate)
            
            if tokens_to_add > 0:
                bucket_data["tokens"] = min(capacity, bucket_data["tokens"] + tokens_to_add)
                bucket_data["last_refill"] = now
        
        # Check if we have enough tokens
        if bucket_data["tokens"] >= tokens_requested:
            bucket_data["tokens"] -= tokens_requested
            await redis_client.set_json(bucket_key, bucket_data, 3600)  # 1 hour expiry
            return True, bucket_data["tokens"]
        else:
            await redis_client.set_json(bucket_key, bucket_data, 3600)
            return False, bucket_data["tokens"]
    
    @staticmethod
    async def get_rate_limit_info(key: str) -> dict:
        """Get current rate limit information"""
        if not redis_client.redis:
            await redis_client.connect()
        
        # Try to get sliding window data
        count = await redis_client.redis.zcard(key)
        ttl = await redis_client.redis.ttl(key)
        
        return {
            "current_requests": count,
            "window_remaining": ttl if ttl > 0 else 0,
            "key": key
        }
    
    @staticmethod
    async def reset_rate_limit(key: str) -> bool:
        """Reset rate limit for a key"""
        return await redis_client.delete(key) > 0


class AdvancedRateLimiter:
    """Advanced rate limiting with multiple tiers and strategies"""
    
    # Rate limit tiers
    RATE_LIMITS = {
        "anonymous": {"requests": 100, "window": 3600},  # 100 per hour
        "authenticated": {"requests": 1000, "window": 3600},  # 1000 per hour
        "premium": {"requests": 5000, "window": 3600},  # 5000 per hour
        "admin": {"requests": 10000, "window": 3600},  # 10000 per hour
    }
    
    # Endpoint-specific limits
    ENDPOINT_LIMITS = {
        "/api/v1/reviews/ingest": {"requests": 100, "window": 60},  # 100 per minute
        "/api/v1/reviews/analyze": {"requests": 200, "window": 60},  # 200 per minute
        "/api/v1/customers/recover": {"requests": 50, "window": 60},  # 50 per minute
        "/api/v1/agents/decide-action": {"requests": 500, "window": 60},  # 500 per minute
    }
    
    @classmethod
    async def check_rate_limit(
        cls,
        identifier: str,
        user_tier: str = "anonymous",
        endpoint: str = None,
        use_sliding_window: bool = True
    ) -> dict:
        """
        Comprehensive rate limit check
        Returns detailed rate limit information
        """
        results = {}
        
        # Check global user rate limit
        global_limit = cls.RATE_LIMITS.get(user_tier, cls.RATE_LIMITS["anonymous"])
        global_key = f"rate_limit:global:{identifier}"
        
        if use_sliding_window:
            is_limited, remaining, reset_time = await RateLimiter.sliding_window_rate_limit(
                global_key,
                global_limit["requests"],
                global_limit["window"]
            )
        else:
            is_limited, remaining = await RateLimiter.is_rate_limited(
                global_key,
                global_limit["requests"],
                global_limit["window"]
            )
            reset_time = int(time.time()) + global_limit["window"]
        
        results["global"] = {
            "limited": is_limited,
            "remaining": remaining,
            "reset_time": reset_time,
            "limit": global_limit["requests"],
            "window": global_limit["window"]
        }
        
        # Check endpoint-specific rate limit
        if endpoint and endpoint in cls.ENDPOINT_LIMITS:
            endpoint_limit = cls.ENDPOINT_LIMITS[endpoint]
            endpoint_key = f"rate_limit:endpoint:{endpoint}:{identifier}"
            
            if use_sliding_window:
                ep_limited, ep_remaining, ep_reset = await RateLimiter.sliding_window_rate_limit(
                    endpoint_key,
                    endpoint_limit["requests"],
                    endpoint_limit["window"]
                )
            else:
                ep_limited, ep_remaining = await RateLimiter.is_rate_limited(
                    endpoint_key,
                    endpoint_limit["requests"],
                    endpoint_limit["window"]
                )
                ep_reset = int(time.time()) + endpoint_limit["window"]
            
            results["endpoint"] = {
                "limited": ep_limited,
                "remaining": ep_remaining,
                "reset_time": ep_reset,
                "limit": endpoint_limit["requests"],
                "window": endpoint_limit["window"]
            }
            
            # Overall result is limited if either global or endpoint is limited
            results["overall_limited"] = is_limited or ep_limited
        else:
            results["overall_limited"] = is_limited
        
        return results
    
    @classmethod
    async def get_user_tier(cls, user_id: str = None, organization_id: str = None) -> str:
        """Determine user tier for rate limiting"""
        if not user_id:
            return "anonymous"
        
        # TODO: Implement actual tier determination based on user/organization data
        # For now, return authenticated for any logged-in user
        return "authenticated"
    
    @classmethod
    def get_rate_limit_headers(cls, rate_limit_info: dict) -> dict:
        """Generate rate limit headers for response"""
        headers = {}
        
        if "global" in rate_limit_info:
            global_info = rate_limit_info["global"]
            headers.update({
                "X-RateLimit-Limit": str(global_info["limit"]),
                "X-RateLimit-Remaining": str(global_info["remaining"]),
                "X-RateLimit-Reset": str(global_info["reset_time"]),
                "X-RateLimit-Window": str(global_info["window"])
            })
        
        if "endpoint" in rate_limit_info:
            endpoint_info = rate_limit_info["endpoint"]
            headers.update({
                "X-RateLimit-Endpoint-Limit": str(endpoint_info["limit"]),
                "X-RateLimit-Endpoint-Remaining": str(endpoint_info["remaining"]),
                "X-RateLimit-Endpoint-Reset": str(endpoint_info["reset_time"])
            })
        
        return headers


# Function to get redis client instance
def get_redis_client() -> RedisClient:
    """Get Redis client instance"""
    return RedisClient()
