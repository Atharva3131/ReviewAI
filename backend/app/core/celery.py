"""
Celery Configuration and Setup

This module configures Celery for background task processing in the Revive AI system.
It handles review ingestion, recovery action execution, metrics aggregation, and other
asynchronous tasks.
"""
from celery import Celery
from celery.signals import worker_init, worker_shutdown
from kombu import Queue
import os
import logging
from typing import Dict, Any

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery instance
celery_app = Celery(
    "revive_ai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.review_tasks",
        "app.tasks.recovery_tasks", 
        "app.tasks.metrics_tasks",
        "app.tasks.monitoring_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "app.tasks.review_tasks.*": {"queue": "reviews"},
        "app.tasks.recovery_tasks.*": {"queue": "recovery"},
        "app.tasks.metrics_tasks.*": {"queue": "metrics"},
        "app.tasks.monitoring_tasks.*": {"queue": "monitoring"},
    },
    
    # Queue definitions
    task_queues=(
        Queue("reviews", routing_key="reviews"),
        Queue("recovery", routing_key="recovery"),
        Queue("metrics", routing_key="metrics"),
        Queue("monitoring", routing_key="monitoring"),
        Queue("dead_letter", routing_key="dead_letter"),
    ),
    
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task result settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # 10 minutes
    task_retry_jitter=True,
    
    # Rate limiting
    task_annotations={
        "app.tasks.review_tasks.process_review": {"rate_limit": "10/m"},
        "app.tasks.recovery_tasks.execute_recovery_action": {"rate_limit": "5/m"},
        "app.tasks.metrics_tasks.aggregate_metrics": {"rate_limit": "1/m"},
    },
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Dead letter queue settings
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
)

# Task failure handling
@celery_app.task(bind=True)
def handle_task_failure(self, task_id: str, error: str, traceback: str):
    """Handle failed tasks by moving them to dead letter queue"""
    logger.error(f"Task {task_id} failed: {error}")
    
    # Send to dead letter queue for manual inspection
    celery_app.send_task(
        "app.tasks.monitoring_tasks.log_failed_task",
        args=[task_id, error, traceback],
        queue="dead_letter"
    )

# Worker lifecycle events
@worker_init.connect
def worker_init_handler(sender=None, conf=None, **kwargs):
    """Initialize worker resources"""
    logger.info(f"Worker {sender} initializing...")
    
    # Initialize database connections, caches, etc.
    # This runs once per worker process

@worker_shutdown.connect  
def worker_shutdown_handler(sender=None, **kwargs):
    """Cleanup worker resources"""
    logger.info(f"Worker {sender} shutting down...")
    
    # Cleanup database connections, caches, etc.

# Task monitoring and health checks
@celery_app.task(bind=True)
def health_check(self):
    """Health check task for monitoring worker status"""
    return {
        "status": "healthy",
        "worker_id": self.request.id,
        "timestamp": self.request.eta or "now"
    }

# Utility functions
def get_task_info(task_id: str) -> Dict[str, Any]:
    """Get information about a specific task"""
    result = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "traceback": result.traceback,
        "date_done": result.date_done,
        "successful": result.successful() if result.ready() else None,
        "failed": result.failed() if result.ready() else None,
    }

def get_queue_length(queue_name: str) -> int:
    """Get the number of tasks in a specific queue"""
    with celery_app.connection() as conn:
        return conn.default_channel.queue_declare(
            queue=queue_name, passive=True
        ).message_count

def get_active_tasks() -> Dict[str, Any]:
    """Get information about currently active tasks"""
    inspect = celery_app.control.inspect()
    
    return {
        "active": inspect.active(),
        "scheduled": inspect.scheduled(),
        "reserved": inspect.reserved(),
        "stats": inspect.stats(),
    }

def purge_queue(queue_name: str) -> int:
    """Purge all tasks from a specific queue"""
    with celery_app.connection() as conn:
        return conn.default_channel.queue_purge(queue_name)

def revoke_task(task_id: str, terminate: bool = False) -> None:
    """Revoke a specific task"""
    celery_app.control.revoke(task_id, terminate=terminate)

# Task scheduling utilities
def schedule_periodic_tasks():
    """Schedule periodic tasks using Celery Beat"""
    from celery.schedules import crontab
    
    celery_app.conf.beat_schedule = {
        # Aggregate metrics every 5 minutes
        "aggregate-metrics": {
            "task": "app.tasks.metrics_tasks.aggregate_metrics",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "metrics"}
        },
        
        # Process pending recovery actions every minute
        "process-recovery-actions": {
            "task": "app.tasks.recovery_tasks.process_pending_actions",
            "schedule": crontab(minute="*"),
            "options": {"queue": "recovery"}
        },
        
        # Clean up old task results every hour
        "cleanup-task-results": {
            "task": "app.tasks.monitoring_tasks.cleanup_old_results",
            "schedule": crontab(minute=0),
            "options": {"queue": "monitoring"}
        },
        
        # Health check every 30 seconds
        "health-check": {
            "task": "app.core.celery.health_check",
            "schedule": 30.0,
            "options": {"queue": "monitoring"}
        },
        
        # Update customer risk scores every hour
        "update-risk-scores": {
            "task": "app.tasks.metrics_tasks.batch_update_risk_scores",
            "schedule": crontab(minute=0),
            "options": {"queue": "metrics"}
        },
    }

# Initialize periodic tasks
schedule_periodic_tasks()

# Export the Celery app
__all__ = ["celery_app"]
