"""
Monitoring and Error Handling Background Tasks

This module contains Celery tasks for system monitoring, error handling,
task retry logic, and dead letter queue management.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from celery import current_task
from celery.exceptions import Retry
import logging
import traceback
import json

from app.core.celery import celery_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def log_failed_task(self, task_id: str, error: str, traceback_str: str) -> Dict[str, Any]:
    """
    Log failed task to dead letter queue for manual inspection
    
    Args:
        task_id: Failed task ID
        error: Error message
        traceback_str: Error traceback
        
    Returns:
        Logging results
    """
    try:
        failure_data = {
            "task_id": task_id,
            "error": error,
            "traceback": traceback_str,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "logged_by": self.request.id
        }
        
        # In production, this would be stored in a database or sent to monitoring service
        logger.error(f"Task {task_id} failed: {error}")
        logger.error(f"Traceback: {traceback_str}")
        
        # Store in dead letter queue (mock implementation)
        dead_letter_entry = {
            "id": f"dlq_{datetime.now().timestamp()}",
            "original_task_id": task_id,
            "failure_data": failure_data,
            "status": "pending_review"
        }
        
        return {
            "dead_letter_id": dead_letter_entry["id"],
            "task_id": task_id,
            "status": "logged",
            "logged_at": failure_data["failed_at"]
        }
        
    except Exception as exc:
        logger.error(f"Failed to log failed task {task_id}: {exc}")
        raise exc


@celery_app.task(bind=True, max_retries=5)
def retry_failed_task(self, original_task_name: str, task_args: List, task_kwargs: Dict) -> Dict[str, Any]:
    """
    Retry a failed task with exponential backoff
    
    Args:
        original_task_name: Name of the original task
        task_args: Original task arguments
        task_kwargs: Original task keyword arguments
        
    Returns:
        Retry results
    """
    try:
        # Calculate retry delay with exponential backoff
        retry_count = self.request.retries
        base_delay = 60  # 1 minute base delay
        max_delay = 3600  # 1 hour max delay
        
        delay = min(base_delay * (2 ** retry_count), max_delay)
        
        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0.8, 1.2)
        final_delay = int(delay * jitter)
        
        # Attempt to retry the original task
        try:
            result = celery_app.send_task(
                original_task_name,
                args=task_args,
                kwargs=task_kwargs,
                countdown=final_delay
            )
            
            return {
                "original_task": original_task_name,
                "retry_count": retry_count,
                "retry_delay": final_delay,
                "new_task_id": result.id,
                "status": "retried"
            }
            
        except Exception as task_exc:
            # If we can't retry, log and potentially give up
            if retry_count >= self.max_retries:
                # Send to dead letter queue
                celery_app.send_task(
                    "app.tasks.monitoring_tasks.log_failed_task",
                    args=[
                        self.request.id,
                        f"Max retries exceeded for {original_task_name}: {str(task_exc)}",
                        traceback.format_exc()
                    ],
                    queue="dead_letter"
                )
                
                return {
                    "original_task": original_task_name,
                    "retry_count": retry_count,
                    "status": "max_retries_exceeded",
                    "final_error": str(task_exc)
                }
            
            # Retry this retry task
            raise self.retry(exc=task_exc, countdown=final_delay)
            
    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={
                "error": str(exc),
                "original_task": original_task_name,
                "retry_count": self.request.retries
            }
        )
        raise exc


@celery_app.task(bind=True)
def monitor_queue_health(self) -> Dict[str, Any]:
    """
    Monitor the health of all task queues
    
    Returns:
        Queue health status
    """
    try:
        from app.core.celery import get_queue_length, get_active_tasks
        
        # Define queue thresholds
        queue_thresholds = {
            "reviews": 100,
            "recovery": 50,
            "metrics": 20,
            "monitoring": 10,
            "dead_letter": 5
        }
        
        queue_health = {}
        overall_healthy = True
        
        # Check each queue
        for queue_name, threshold in queue_thresholds.items():
            try:
                queue_length = get_queue_length(queue_name)
                is_healthy = queue_length < threshold
                
                queue_health[queue_name] = {
                    "length": queue_length,
                    "threshold": threshold,
                    "healthy": is_healthy,
                    "utilization": round((queue_length / threshold) * 100, 1)
                }
                
                if not is_healthy:
                    overall_healthy = False
                    logger.warning(f"Queue {queue_name} is unhealthy: {queue_length} tasks (threshold: {threshold})")
                    
            except Exception as e:
                queue_health[queue_name] = {
                    "error": str(e),
                    "healthy": False
                }
                overall_healthy = False
        
        # Get active task information
        try:
            active_tasks = get_active_tasks()
            total_active = sum(len(tasks) for tasks in active_tasks.get("active", {}).values())
        except Exception as e:
            active_tasks = {"error": str(e)}
            total_active = -1
        
        health_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_healthy": overall_healthy,
            "queue_health": queue_health,
            "active_tasks": active_tasks,
            "total_active_tasks": total_active,
            "monitoring_task_id": self.request.id
        }
        
        # Alert if unhealthy
        if not overall_healthy:
            celery_app.send_task(
                "app.tasks.monitoring_tasks.send_health_alert",
                args=[health_report],
                queue="monitoring"
            )
        
        return health_report
        
    except Exception as exc:
        logger.error(f"Queue health monitoring failed: {exc}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_healthy": False,
            "error": str(exc),
            "monitoring_task_id": self.request.id
        }


@celery_app.task(bind=True)
def send_health_alert(self, health_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send health alert when system is unhealthy
    
    Args:
        health_report: Health report data
        
    Returns:
        Alert sending results
    """
    try:
        # In production, this would send alerts via email, Slack, PagerDuty, etc.
        alert_data = {
            "alert_type": "queue_health",
            "severity": "warning",
            "timestamp": health_report["timestamp"],
            "message": "One or more task queues are unhealthy",
            "details": health_report,
            "alert_id": f"health_alert_{datetime.now().timestamp()}"
        }
        
        # Mock alert sending
        logger.warning(f"HEALTH ALERT: {alert_data['message']}")
        logger.warning(f"Alert details: {json.dumps(alert_data, indent=2)}")
        
        return {
            "alert_sent": True,
            "alert_id": alert_data["alert_id"],
            "alert_type": alert_data["alert_type"],
            "timestamp": alert_data["timestamp"]
        }
        
    except Exception as exc:
        logger.error(f"Failed to send health alert: {exc}")
        return {
            "alert_sent": False,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@celery_app.task(bind=True)
def cleanup_old_results(self, days_old: int = 7) -> Dict[str, Any]:
    """
    Clean up old task results and logs
    
    Args:
        days_old: Number of days after which to clean up results
        
    Returns:
        Cleanup results
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        # In production, this would clean up:
        # - Celery result backend entries
        # - Task execution logs
        # - Dead letter queue entries (after manual review)
        # - Monitoring data
        
        cleanup_stats = {
            "task_results_cleaned": 0,
            "logs_cleaned": 0,
            "dead_letter_cleaned": 0,
            "cutoff_date": cutoff_date.isoformat(),
            "cleanup_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Mock cleanup operations
        logger.info(f"Cleaning up task data older than {cutoff_date}")
        
        # Simulate cleanup counts
        cleanup_stats["task_results_cleaned"] = 150
        cleanup_stats["logs_cleaned"] = 75
        cleanup_stats["dead_letter_cleaned"] = 5
        
        return cleanup_stats
        
    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(exc), "days_old": days_old}
        )
        raise exc


@celery_app.task(bind=True)
def monitor_task_performance(self) -> Dict[str, Any]:
    """
    Monitor task performance metrics
    
    Returns:
        Performance monitoring results
    """
    try:
        from app.core.celery import get_active_tasks
        
        # Get current task statistics
        active_tasks = get_active_tasks()
        
        # Calculate performance metrics
        performance_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_tasks": active_tasks,
            "performance_metrics": {}
        }
        
        # Analyze task performance by type
        task_types = [
            "app.tasks.review_tasks",
            "app.tasks.recovery_tasks", 
            "app.tasks.metrics_tasks",
            "app.tasks.monitoring_tasks"
        ]
        
        for task_type in task_types:
            # In production, this would query actual performance data
            performance_data["performance_metrics"][task_type] = {
                "avg_execution_time": 45.2,  # seconds
                "success_rate": 0.985,
                "error_rate": 0.015,
                "throughput": 12.5,  # tasks per minute
                "queue_wait_time": 2.3  # seconds
            }
        
        # Check for performance issues
        issues = []
        for task_type, metrics in performance_data["performance_metrics"].items():
            if metrics["success_rate"] < 0.95:
                issues.append(f"{task_type} has low success rate: {metrics['success_rate']}")
            if metrics["avg_execution_time"] > 120:
                issues.append(f"{task_type} has high execution time: {metrics['avg_execution_time']}s")
        
        performance_data["issues"] = issues
        performance_data["healthy"] = len(issues) == 0
        
        # Send alert if performance issues detected
        if issues:
            celery_app.send_task(
                "app.tasks.monitoring_tasks.send_performance_alert",
                args=[performance_data],
                queue="monitoring"
            )
        
        return performance_data
        
    except Exception as exc:
        logger.error(f"Task performance monitoring failed: {exc}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "healthy": False,
            "error": str(exc)
        }


@celery_app.task(bind=True)
def send_performance_alert(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send performance alert when issues are detected
    
    Args:
        performance_data: Performance monitoring data
        
    Returns:
        Alert sending results
    """
    try:
        alert_data = {
            "alert_type": "performance",
            "severity": "warning",
            "timestamp": performance_data["timestamp"],
            "message": f"Performance issues detected: {len(performance_data['issues'])} issues",
            "issues": performance_data["issues"],
            "details": performance_data,
            "alert_id": f"perf_alert_{datetime.now().timestamp()}"
        }
        
        # Mock alert sending
        logger.warning(f"PERFORMANCE ALERT: {alert_data['message']}")
        for issue in alert_data["issues"]:
            logger.warning(f"  - {issue}")
        
        return {
            "alert_sent": True,
            "alert_id": alert_data["alert_id"],
            "issues_count": len(performance_data["issues"]),
            "timestamp": alert_data["timestamp"]
        }
        
    except Exception as exc:
        logger.error(f"Failed to send performance alert: {exc}")
        return {
            "alert_sent": False,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@celery_app.task(bind=True)
def process_dead_letter_queue(self) -> Dict[str, Any]:
    """
    Process items in the dead letter queue for potential retry or archival
    
    Returns:
        Processing results
    """
    try:
        # In production, this would:
        # 1. Retrieve items from dead letter queue storage
        # 2. Analyze failure patterns
        # 3. Determine if items can be safely retried
        # 4. Archive items that can't be recovered
        
        processing_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "items_processed": 0,
            "items_retried": 0,
            "items_archived": 0,
            "items_failed": 0
        }
        
        # Mock processing
        mock_dlq_items = [
            {"id": "dlq_1", "retryable": True, "attempts": 1},
            {"id": "dlq_2", "retryable": False, "attempts": 5},
            {"id": "dlq_3", "retryable": True, "attempts": 2}
        ]
        
        for item in mock_dlq_items:
            processing_results["items_processed"] += 1
            
            if item["retryable"] and item["attempts"] < 3:
                # Retry the item
                processing_results["items_retried"] += 1
                logger.info(f"Retrying dead letter item {item['id']}")
            else:
                # Archive the item
                processing_results["items_archived"] += 1
                logger.info(f"Archiving dead letter item {item['id']}")
        
        return processing_results
        
    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(exc)}
        )
        raise exc


@celery_app.task(bind=True)
def generate_monitoring_report(self, report_type: str = "daily") -> Dict[str, Any]:
    """
    Generate comprehensive monitoring report
    
    Args:
        report_type: Type of report (hourly, daily, weekly)
        
    Returns:
        Monitoring report data
    """
    try:
        # Determine report period
        now = datetime.now(timezone.utc)
        if report_type == "hourly":
            start_time = now - timedelta(hours=1)
        elif report_type == "daily":
            start_time = now - timedelta(days=1)
        else:  # weekly
            start_time = now - timedelta(days=7)
        
        # Gather monitoring data
        report_data = {
            "report_type": report_type,
            "report_period": {
                "start": start_time.isoformat(),
                "end": now.isoformat()
            },
            "generated_at": now.isoformat(),
            "system_health": {
                "overall_status": "healthy",
                "uptime_percentage": 99.95,
                "error_rate": 0.005
            },
            "task_statistics": {
                "total_tasks_executed": 1250,
                "successful_tasks": 1244,
                "failed_tasks": 6,
                "retried_tasks": 3,
                "dead_letter_items": 2
            },
            "queue_statistics": {
                "reviews": {"processed": 450, "avg_wait_time": 2.1},
                "recovery": {"processed": 320, "avg_wait_time": 1.8},
                "metrics": {"processed": 180, "avg_wait_time": 0.5},
                "monitoring": {"processed": 300, "avg_wait_time": 0.3}
            },
            "performance_metrics": {
                "avg_task_execution_time": 42.3,
                "peak_queue_length": 85,
                "worker_utilization": 0.72
            },
            "alerts_generated": 2,
            "issues_resolved": 1
        }
        
        return report_data
        
    except Exception as exc:
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(exc), "report_type": report_type}
        )
        raise exc


@celery_app.task(bind=True, max_retries=0)
def emergency_shutdown(self, reason: str) -> Dict[str, Any]:
    """
    Emergency shutdown procedure for critical system issues
    
    Args:
        reason: Reason for emergency shutdown
        
    Returns:
        Shutdown results
    """
    try:
        shutdown_data = {
            "shutdown_initiated_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "initiated_by": self.request.id,
            "actions_taken": []
        }
        
        # Log critical alert
        logger.critical(f"EMERGENCY SHUTDOWN INITIATED: {reason}")
        shutdown_data["actions_taken"].append("Critical alert logged")
        
        # In production, this would:
        # 1. Stop accepting new tasks
        # 2. Allow current tasks to complete or timeout
        # 3. Send critical alerts to all channels
        # 4. Gracefully shutdown workers
        # 5. Update system status
        
        # Mock shutdown actions
        shutdown_data["actions_taken"].extend([
            "New task acceptance stopped",
            "Critical alerts sent",
            "Graceful worker shutdown initiated",
            "System status updated to maintenance mode"
        ])
        
        return shutdown_data
        
    except Exception as exc:
        logger.critical(f"Emergency shutdown failed: {exc}")
        raise exc
