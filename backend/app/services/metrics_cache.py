"""
Advanced metrics caching service for performance optimization
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from functools import wraps

from app.core.redis import redis_client, CacheManager

logger = logging.getLogger(__name__)


class MetricsCacheService:
    """Advanced caching service for dashboard metrics"""
    
    # Cache TTL configurations (in seconds)
    CACHE_TTLS = {
        "kpis": 300,           # 5 minutes
        "trends": 600,         # 10 minutes
        "activity_feed": 60,   # 1 minute
        "charts": 900,         # 15 minutes
        "alerts": 120,         # 2 minutes
        "realtime": 30,        # 30 seconds
        "aggregated": 1800,    # 30 minutes
    }
    
    # Cache warming intervals
    WARM_INTERVALS = {
        "kpis": 240,           # Warm 1 minute before expiry
        "trends": 540,         # Warm 1 minute before expiry
        "charts": 840,         # Warm 1 minute before expiry
    }
    
    def __init__(self):
        self.warming_tasks: Dict[str, asyncio.Task] = {}
    
    async def get_cached_metrics(
        self, 
        cache_key: str, 
        fetch_func: Callable,
        ttl: int = 300,
        warm_cache: bool = True
    ) -> Any:
        """
        Get metrics from cache or fetch and cache
        
        Args:
            cache_key: Redis cache key
            fetch_func: Function to fetch fresh data
            ttl: Cache TTL in seconds
            warm_cache: Whether to warm cache before expiry
        """
        try:
            # Try to get from cache
            cached_data = await redis_client.get_json(cache_key)
            
            if cached_data is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                
                # Schedule cache warming if enabled
                if warm_cache and cache_key not in self.warming_tasks:
                    warm_time = ttl - 60  # Warm 1 minute before expiry
                    if warm_time > 0:
                        self.warming_tasks[cache_key] = asyncio.create_task(
                            self._schedule_cache_warming(cache_key, fetch_func, warm_time)
                        )
                
                return cached_data
            
            # Cache miss - fetch fresh data
            logger.debug(f"Cache miss for key: {cache_key}")
            fresh_data = await fetch_func()
            
            # Cache the fresh data
            await redis_client.set_json(cache_key, fresh_data, ttl)
            
            return fresh_data
            
        except Exception as e:
            logger.error(f"Cache operation failed for key {cache_key}: {e}")
            # Fallback to direct fetch
            return await fetch_func()
    
    async def invalidate_cache(self, pattern: str):
        """Invalidate cache keys matching pattern"""
        try:
            if redis_client.redis:
                keys = await redis_client.redis.keys(pattern)
                if keys:
                    await redis_client.redis.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache keys matching pattern: {pattern}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache pattern {pattern}: {e}")
    
    async def invalidate_organization_cache(self, organization_id: str):
        """Invalidate all cache for an organization"""
        patterns = [
            f"revive_ai:dashboard_metrics:{organization_id}:*",
            f"revive_ai:kpis:{organization_id}:*",
            f"revive_ai:trends:{organization_id}:*",
            f"revive_ai:activity:{organization_id}:*",
            f"revive_ai:alerts:{organization_id}:*",
            f"revive_ai:realtime_metrics:{organization_id}",
        ]
        
        for pattern in patterns:
            await self.invalidate_cache(pattern)
    
    async def warm_cache(self, cache_key: str, fetch_func: Callable, ttl: int):
        """Warm cache with fresh data"""
        try:
            fresh_data = await fetch_func()
            await redis_client.set_json(cache_key, fresh_data, ttl)
            logger.debug(f"Cache warmed for key: {cache_key}")
        except Exception as e:
            logger.error(f"Failed to warm cache for key {cache_key}: {e}")
    
    async def _schedule_cache_warming(self, cache_key: str, fetch_func: Callable, delay: int):
        """Schedule cache warming task"""
        try:
            await asyncio.sleep(delay)
            await self.warm_cache(cache_key, fetch_func, self.CACHE_TTLS.get("kpis", 300))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Cache warming failed for key {cache_key}: {e}")
        finally:
            # Clean up task reference
            if cache_key in self.warming_tasks:
                del self.warming_tasks[cache_key]
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if not redis_client.redis:
                return {"error": "Redis not connected"}
            
            # Get Redis info
            redis_info = await redis_client.redis.info()
            
            # Count keys by pattern
            key_counts = {}
            patterns = [
                "revive_ai:dashboard_metrics:*",
                "revive_ai:kpis:*",
                "revive_ai:trends:*",
                "revive_ai:activity:*",
                "revive_ai:alerts:*",
                "revive_ai:realtime_metrics:*",
            ]
            
            for pattern in patterns:
                keys = await redis_client.redis.keys(pattern)
                key_counts[pattern] = len(keys)
            
            return {
                "redis_info": {
                    "used_memory": redis_info.get("used_memory_human"),
                    "connected_clients": redis_info.get("connected_clients"),
                    "total_commands_processed": redis_info.get("total_commands_processed"),
                    "keyspace_hits": redis_info.get("keyspace_hits"),
                    "keyspace_misses": redis_info.get("keyspace_misses"),
                },
                "key_counts": key_counts,
                "warming_tasks": len(self.warming_tasks),
                "cache_ttls": self.CACHE_TTLS,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}


# Global cache service instance
metrics_cache = MetricsCacheService()


def cached_metrics(
    cache_type: str = "kpis",
    key_suffix: str = "",
    warm_cache: bool = True
):
    """
    Decorator for caching metrics functions
    
    Args:
        cache_type: Type of cache (determines TTL)
        key_suffix: Additional suffix for cache key
        warm_cache: Whether to enable cache warming
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            func_name = func.__name__
            
            # Extract organization_id from args/kwargs
            organization_id = None
            if args and hasattr(args[0], '__dict__') and 'organization_id' in str(args):
                # Try to find organization_id in arguments
                for arg in args:
                    if isinstance(arg, str) and len(arg) == 36:  # UUID length
                        organization_id = arg
                        break
            
            if not organization_id and 'organization_id' in kwargs:
                organization_id = kwargs['organization_id']
            
            if not organization_id:
                # If no organization_id found, execute function directly
                return await func(*args, **kwargs)
            
            # Create cache key
            cache_key = CacheManager.make_key(
                cache_type,
                func_name,
                organization_id,
                key_suffix,
                prefix="revive_ai"
            )
            
            # Get TTL for cache type
            ttl = metrics_cache.CACHE_TTLS.get(cache_type, 300)
            
            # Create fetch function
            async def fetch_func():
                return await func(*args, **kwargs)
            
            # Get cached or fresh data
            return await metrics_cache.get_cached_metrics(
                cache_key=cache_key,
                fetch_func=fetch_func,
                ttl=ttl,
                warm_cache=warm_cache
            )
        
        return wrapper
    return decorator


class MetricsAggregationCache:
    """Cache for pre-aggregated metrics to improve performance"""
    
    @staticmethod
    async def get_daily_aggregates(organization_id: str, date: datetime) -> Optional[Dict[str, Any]]:
        """Get daily aggregated metrics"""
        date_str = date.strftime("%Y-%m-%d")
        cache_key = CacheManager.make_key(
            "daily_aggregates",
            organization_id,
            date_str,
            prefix="revive_ai"
        )
        
        return await redis_client.get_json(cache_key)
    
    @staticmethod
    async def set_daily_aggregates(
        organization_id: str, 
        date: datetime, 
        aggregates: Dict[str, Any]
    ):
        """Set daily aggregated metrics"""
        date_str = date.strftime("%Y-%m-%d")
        cache_key = CacheManager.make_key(
            "daily_aggregates",
            organization_id,
            date_str,
            prefix="revive_ai"
        )
        
        # Cache for 7 days
        await redis_client.set_json(cache_key, aggregates, 7 * 24 * 3600)
    
    @staticmethod
    async def get_hourly_aggregates(organization_id: str, hour: datetime) -> Optional[Dict[str, Any]]:
        """Get hourly aggregated metrics"""
        hour_str = hour.strftime("%Y-%m-%d-%H")
        cache_key = CacheManager.make_key(
            "hourly_aggregates",
            organization_id,
            hour_str,
            prefix="revive_ai"
        )
        
        return await redis_client.get_json(cache_key)
    
    @staticmethod
    async def set_hourly_aggregates(
        organization_id: str, 
        hour: datetime, 
        aggregates: Dict[str, Any]
    ):
        """Set hourly aggregated metrics"""
        hour_str = hour.strftime("%Y-%m-%d-%H")
        cache_key = CacheManager.make_key(
            "hourly_aggregates",
            organization_id,
            hour_str,
            prefix="revive_ai"
        )
        
        # Cache for 24 hours
        await redis_client.set_json(cache_key, aggregates, 24 * 3600)


class CacheWarmingService:
    """Service for proactive cache warming"""
    
    def __init__(self):
        self.warming_schedule: Dict[str, asyncio.Task] = {}
    
    async def start_warming_schedule(self, organization_ids: List[str]):
        """Start cache warming schedule for organizations"""
        for org_id in organization_ids:
            if org_id not in self.warming_schedule:
                self.warming_schedule[org_id] = asyncio.create_task(
                    self._warm_organization_cache(org_id)
                )
    
    async def stop_warming_schedule(self, organization_id: str):
        """Stop cache warming for an organization"""
        if organization_id in self.warming_schedule:
            self.warming_schedule[organization_id].cancel()
            del self.warming_schedule[organization_id]
    
    async def _warm_organization_cache(self, organization_id: str):
        """Warm cache for an organization on schedule"""
        try:
            while True:
                # Warm KPIs cache
                await self._warm_kpis_cache(organization_id)
                
                # Warm trends cache
                await self._warm_trends_cache(organization_id)
                
                # Wait for next warming cycle (5 minutes)
                await asyncio.sleep(300)
                
        except asyncio.CancelledError:
            logger.info(f"Cache warming cancelled for organization {organization_id}")
        except Exception as e:
            logger.error(f"Cache warming error for organization {organization_id}: {e}")
    
    async def _warm_kpis_cache(self, organization_id: str):
        """Warm KPIs cache"""
        try:
            from app.services.dashboard_service import DashboardMetricsService
            from app.core.database import get_async_db
            
            async for db in get_async_db():
                service = DashboardMetricsService(db)
                
                # Warm cache for different time ranges
                for time_range in ["7d", "30d", "90d"]:
                    cache_key = CacheManager.make_key(
                        "dashboard_metrics",
                        organization_id,
                        time_range,
                        prefix="revive_ai"
                    )
                    
                    # Check if cache needs warming (expires in next 60 seconds)
                    if redis_client.redis:
                        ttl = await redis_client.redis.ttl(cache_key)
                        if ttl < 60:  # Less than 60 seconds remaining
                            await service.get_comprehensive_metrics(organization_id, time_range)
                
                break  # Exit the async generator
                
        except Exception as e:
            logger.error(f"Failed to warm KPIs cache for {organization_id}: {e}")
    
    async def _warm_trends_cache(self, organization_id: str):
        """Warm trends cache"""
        # Similar implementation for trends
        pass


# Global cache warming service
cache_warming_service = CacheWarmingService()
