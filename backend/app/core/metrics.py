"""
Comprehensive metrics collection and monitoring system
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
import json
import logging

from app.core.redis import get_redis_client
from app.core.config import settings

logger = logging.getLogger("app.metrics")


@dataclass
class MetricPoint:
    """Individual metric data point"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = "count"


@dataclass
class TimeSeries:
    """Time series data for a metric"""
    name: str
    points: deque = field(default_factory=lambda: deque(maxlen=1000))
    tags: Dict[str, str] = field(default_factory=dict)
    
    def add_point(self, value: float, timestamp: Optional[datetime] = None):
        """Add a data point to the time series"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        point = MetricPoint(
            name=self.name,
            value=value,
            timestamp=timestamp,
            tags=self.tags
        )
        self.points.append(point)
    
    def get_recent_points(self, minutes: int = 5) -> List[MetricPoint]:
        """Get points from the last N minutes"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [p for p in self.points if p.timestamp >= cutoff]
    
    def get_average(self, minutes: int = 5) -> float:
        """Get average value over the last N minutes"""
        points = self.get_recent_points(minutes)
        if not points:
            return 0.0
        return sum(p.value for p in points) / len(points)
    
    def get_max(self, minutes: int = 5) -> float:
        """Get maximum value over the last N minutes"""
        points = self.get_recent_points(minutes)
        if not points:
            return 0.0
        return max(p.value for p in points)
    
    def get_min(self, minutes: int = 5) -> float:
        """Get minimum value over the last N minutes"""
        points = self.get_recent_points(minutes)
        if not points:
            return 0.0
        return min(p.value for p in points)


class MetricsCollector:
    """
    Comprehensive metrics collection system
    """
    
    def __init__(self):
        self.metrics: Dict[str, TimeSeries] = {}
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()
        self.redis_client = None
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks for metrics collection"""
        # Start metrics aggregation task
        threading.Thread(target=self._aggregate_metrics_loop, daemon=True).start()
        
        # Start Redis publishing task
        threading.Thread(target=self._publish_metrics_loop, daemon=True).start()
    
    def _get_redis_client(self):
        """Get Redis client for metrics publishing"""
        if self.redis_client is None:
            try:
                self.redis_client = get_redis_client()
            except Exception as e:
                logger.error(f"Failed to connect to Redis for metrics: {e}")
        return self.redis_client
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        with self.lock:
            key = self._get_metric_key(name, tags)
            self.counters[key] += value
            
            # Also add to time series
            if key not in self.metrics:
                self.metrics[key] = TimeSeries(name=name, tags=tags or {})
            self.metrics[key].add_point(self.counters[key])
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric value"""
        with self.lock:
            key = self._get_metric_key(name, tags)
            self.gauges[key] = value
            
            # Also add to time series
            if key not in self.metrics:
                self.metrics[key] = TimeSeries(name=name, tags=tags or {})
            self.metrics[key].add_point(value)
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a value in a histogram"""
        with self.lock:
            key = self._get_metric_key(name, tags)
            self.histograms[key].append(value)
            
            # Keep only last 1000 values
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
            
            # Also add to time series
            if key not in self.metrics:
                self.metrics[key] = TimeSeries(name=name, tags=tags or {})
            self.metrics[key].add_point(value)
    
    def time_operation(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations"""
        return TimingContext(self, name, tags)
    
    def _get_metric_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Generate a unique key for a metric with tags"""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics"""
        with self.lock:
            summary = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {}
            }
            
            # Calculate histogram statistics
            for key, values in self.histograms.items():
                if values:
                    summary["histograms"][key] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "p50": self._percentile(values, 50),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99)
                    }
            
            return summary
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _aggregate_metrics_loop(self):
        """Background loop for metrics aggregation"""
        while True:
            try:
                time.sleep(60)  # Aggregate every minute
                self._aggregate_metrics()
            except Exception as e:
                logger.error(f"Error in metrics aggregation: {e}")
    
    def _aggregate_metrics(self):
        """Aggregate metrics for storage and analysis"""
        summary = self.get_metrics_summary()
        
        # Log metrics summary
        logger.info("Metrics summary", extra={
            "metrics_summary": summary,
            "metric_count": len(self.counters) + len(self.gauges) + len(self.histograms)
        })
        
        # Store in Redis for external monitoring systems
        redis_client = self._get_redis_client()
        if redis_client:
            try:
                redis_client.setex(
                    "metrics:summary",
                    300,  # 5 minutes TTL
                    json.dumps(summary, default=str)
                )
            except Exception as e:
                logger.error(f"Failed to store metrics in Redis: {e}")
    
    def _publish_metrics_loop(self):
        """Background loop for publishing metrics to external systems"""
        while True:
            try:
                time.sleep(30)  # Publish every 30 seconds
                self._publish_metrics()
            except Exception as e:
                logger.error(f"Error in metrics publishing: {e}")
    
    def _publish_metrics(self):
        """Publish metrics to external monitoring systems"""
        redis_client = self._get_redis_client()
        if not redis_client:
            return
        
        try:
            # Publish individual metrics
            for key, value in self.counters.items():
                redis_client.publish("metrics:counter", json.dumps({
                    "key": key,
                    "value": value,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
            
            for key, value in self.gauges.items():
                redis_client.publish("metrics:gauge", json.dumps({
                    "key": key,
                    "value": value,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
            
        except Exception as e:
            logger.error(f"Failed to publish metrics: {e}")


class TimingContext:
    """Context manager for timing operations"""
    
    def __init__(self, collector: MetricsCollector, name: str, tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.record_histogram(
                f"{self.name}.duration",
                duration * 1000,  # Convert to milliseconds
                self.tags
            )
            
            # Also increment operation counter
            self.collector.increment_counter(
                f"{self.name}.count",
                tags=self.tags
            )
            
            # Track errors if exception occurred
            if exc_type:
                error_tags = (self.tags or {}).copy()
                error_tags["error_type"] = exc_type.__name__
                self.collector.increment_counter(
                    f"{self.name}.errors",
                    tags=error_tags
                )


# Global metrics collector instance
metrics = MetricsCollector()


# Convenience functions
def increment_counter(name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
    """Increment a counter metric"""
    metrics.increment_counter(name, value, tags)


def set_gauge(name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """Set a gauge metric value"""
    metrics.set_gauge(name, value, tags)


def record_histogram(name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """Record a value in a histogram"""
    metrics.record_histogram(name, value, tags)


def time_operation(name: str, tags: Optional[Dict[str, str]] = None):
    """Context manager for timing operations"""
    return metrics.time_operation(name, tags)


# Application-specific metrics functions
def track_api_request(method: str, endpoint: str, status_code: int, response_time: float):
    """Track API request metrics"""
    tags = {
        "method": method,
        "endpoint": endpoint,
        "status_code": str(status_code),
        "status_class": f"{status_code // 100}xx"
    }
    
    increment_counter("api.requests.total", tags=tags)
    record_histogram("api.requests.duration", response_time * 1000, tags=tags)
    
    if status_code >= 400:
        increment_counter("api.requests.errors", tags=tags)


def track_database_operation(operation: str, table: str, duration: float, rows_affected: Optional[int] = None):
    """Track database operation metrics"""
    tags = {
        "operation": operation,
        "table": table
    }
    
    increment_counter("database.operations.total", tags=tags)
    record_histogram("database.operations.duration", duration * 1000, tags=tags)
    
    if rows_affected is not None:
        record_histogram("database.operations.rows_affected", rows_affected, tags=tags)


def track_external_api_call(service: str, endpoint: str, status_code: int, response_time: float):
    """Track external API call metrics"""
    tags = {
        "service": service,
        "endpoint": endpoint,
        "status_code": str(status_code),
        "status_class": f"{status_code // 100}xx"
    }
    
    increment_counter("external_api.requests.total", tags=tags)
    record_histogram("external_api.requests.duration", response_time * 1000, tags=tags)
    
    if status_code >= 400:
        increment_counter("external_api.requests.errors", tags=tags)


def track_background_task(task_name: str, duration: float, success: bool):
    """Track background task metrics"""
    tags = {
        "task_name": task_name,
        "status": "success" if success else "failure"
    }
    
    increment_counter("background_tasks.total", tags=tags)
    record_histogram("background_tasks.duration", duration * 1000, tags=tags)
    
    if not success:
        increment_counter("background_tasks.failures", tags={"task_name": task_name})


def track_user_action(action: str, user_id: str, organization_id: str):
    """Track user action metrics"""
    tags = {
        "action": action,
        "organization_id": organization_id
    }
    
    increment_counter("user_actions.total", tags=tags)
    
    # Track unique users (using Redis HyperLogLog for efficiency)
    redis_client = metrics._get_redis_client()
    if redis_client:
        try:
            redis_client.pfadd("unique_users:daily", user_id)
            redis_client.pfadd(f"unique_users:org:{organization_id}:daily", user_id)
        except Exception as e:
            logger.error(f"Failed to track unique users: {e}")


def track_business_metric(metric_name: str, value: float, organization_id: str):
    """Track business-specific metrics"""
    tags = {
        "organization_id": organization_id
    }
    
    set_gauge(f"business.{metric_name}", value, tags=tags)


# System metrics collection
def collect_system_metrics():
    """Collect system-level metrics"""
    try:
        import psutil
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        set_gauge("system.cpu.usage_percent", cpu_percent)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        set_gauge("system.memory.usage_percent", memory.percent)
        set_gauge("system.memory.available_bytes", memory.available)
        set_gauge("system.memory.used_bytes", memory.used)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        set_gauge("system.disk.usage_percent", (disk.used / disk.total) * 100)
        set_gauge("system.disk.free_bytes", disk.free)
        set_gauge("system.disk.used_bytes", disk.used)
        
        # Network metrics
        network = psutil.net_io_counters()
        increment_counter("system.network.bytes_sent", network.bytes_sent)
        increment_counter("system.network.bytes_recv", network.bytes_recv)
        
    except ImportError:
        logger.warning("psutil not available, skipping system metrics collection")
    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}")


# Start system metrics collection
if settings.ENVIRONMENT == "production":
    import threading
    
    def system_metrics_loop():
        while True:
            try:
                collect_system_metrics()
                time.sleep(60)  # Collect every minute
            except Exception as e:
                logger.error(f"Error in system metrics collection: {e}")
    
    threading.Thread(target=system_metrics_loop, daemon=True).start()
