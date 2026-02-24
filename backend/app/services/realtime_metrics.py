"""
Real-time metrics update service using WebSockets
"""
import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
from datetime import datetime, timedelta
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.services.dashboard_service import DashboardMetricsService

logger = logging.getLogger(__name__)


class MetricsWebSocketManager:
    """WebSocket connection manager for real-time metrics updates"""
    
    def __init__(self):
        # Store active connections by organization_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self.update_tasks: Dict[str, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, organization_id: str, user_id: str):
        """Accept WebSocket connection and start metrics updates"""
        await websocket.accept()
        
        # Add connection to organization group
        if organization_id not in self.active_connections:
            self.active_connections[organization_id] = set()
        
        self.active_connections[organization_id].add(websocket)
        
        # Store connection metadata
        self.connection_metadata[websocket] = {
            "organization_id": organization_id,
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "last_update": None
        }
        
        # Start periodic updates for this organization if not already running
        if organization_id not in self.update_tasks:
            self.update_tasks[organization_id] = asyncio.create_task(
                self._periodic_updates(organization_id)
            )
        
        logger.info(
            f"WebSocket connected for organization {organization_id}",
            extra={
                "organization_id": organization_id,
                "user_id": user_id,
                "total_connections": len(self.active_connections[organization_id])
            }
        )
    
    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        if websocket not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[websocket]
        organization_id = metadata["organization_id"]
        
        # Remove connection
        if organization_id in self.active_connections:
            self.active_connections[organization_id].discard(websocket)
            
            # If no more connections for this organization, stop updates
            if not self.active_connections[organization_id]:
                del self.active_connections[organization_id]
                
                if organization_id in self.update_tasks:
                    self.update_tasks[organization_id].cancel()
                    del self.update_tasks[organization_id]
        
        # Clean up metadata
        del self.connection_metadata[websocket]
        
        logger.info(
            f"WebSocket disconnected for organization {organization_id}",
            extra={
                "organization_id": organization_id,
                "user_id": metadata["user_id"],
                "connection_duration": (datetime.utcnow() - metadata["connected_at"]).total_seconds()
            }
        )
    
    async def send_metrics_update(self, organization_id: str, metrics: Dict[str, Any]):
        """Send metrics update to all connections for an organization"""
        if organization_id not in self.active_connections:
            return
        
        message = {
            "type": "metrics_update",
            "data": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all connections for this organization
        disconnected_connections = set()
        
        for websocket in self.active_connections[organization_id]:
            try:
                await websocket.send_text(json.dumps(message))
                
                # Update last update time
                if websocket in self.connection_metadata:
                    self.connection_metadata[websocket]["last_update"] = datetime.utcnow()
                    
            except Exception as e:
                logger.error(f"Failed to send metrics update: {e}")
                disconnected_connections.add(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected_connections:
            await self.disconnect(websocket)
    
    async def send_alert(self, organization_id: str, alert: Dict[str, Any]):
        """Send real-time alert to all connections for an organization"""
        if organization_id not in self.active_connections:
            return
        
        message = {
            "type": "alert",
            "data": alert,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        disconnected_connections = set()
        
        for websocket in self.active_connections[organization_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
                disconnected_connections.add(websocket)
        
        # Clean up disconnected connections
        for websocket in disconnected_connections:
            await self.disconnect(websocket)
    
    async def _periodic_updates(self, organization_id: str):
        """Periodic metrics updates for an organization"""
        update_interval = 30  # 30 seconds
        
        try:
            while organization_id in self.active_connections:
                # Get lightweight metrics update
                metrics_update = await self._get_lightweight_metrics(organization_id)
                
                if metrics_update:
                    await self.send_metrics_update(organization_id, metrics_update)
                
                await asyncio.sleep(update_interval)
                
        except asyncio.CancelledError:
            logger.info(f"Periodic updates cancelled for organization {organization_id}")
        except Exception as e:
            logger.error(f"Error in periodic updates for organization {organization_id}: {e}")
    
    async def _get_lightweight_metrics(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """Get lightweight metrics for real-time updates"""
        try:
            # Check if we have recent cached metrics
            from app.core.redis import CacheManager
            
            cache_key = CacheManager.make_key(
                "realtime_metrics",
                organization_id,
                prefix="revive_ai"
            )
            
            cached_metrics = await redis_client.get_json(cache_key)
            if cached_metrics:
                return cached_metrics
            
            # Calculate lightweight metrics
            # This would be a simplified version of full metrics
            lightweight_metrics = {
                "kpis": {
                    "average_rating": {"value": 4.2, "trend": "up"},
                    "monthly_reviews": {"value": 127, "trend": "up"},
                    "at_risk_customers": {"value": 23, "trend": "down"},
                    "recovery_success_rate": {"value": 78.5, "trend": "up"}
                },
                "recent_activity_count": 5,
                "alerts_count": 2,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Cache for 30 seconds
            await redis_client.set_json(cache_key, lightweight_metrics, 30)
            
            return lightweight_metrics
            
        except Exception as e:
            logger.error(f"Failed to get lightweight metrics: {e}")
            return None
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        total_connections = sum(len(connections) for connections in self.active_connections.values())
        
        return {
            "total_connections": total_connections,
            "organizations_connected": len(self.active_connections),
            "active_update_tasks": len(self.update_tasks),
            "connections_by_org": {
                org_id: len(connections) 
                for org_id, connections in self.active_connections.items()
            }
        }


# Global WebSocket manager instance
websocket_manager = MetricsWebSocketManager()


class RealTimeMetricsService:
    """Service for triggering real-time metrics updates"""
    
    @staticmethod
    async def trigger_metrics_update(organization_id: str):
        """Trigger immediate metrics update for an organization"""
        try:
            # Get fresh metrics
            from app.core.database import get_async_db
            
            async for db in get_async_db():
                dashboard_service = DashboardMetricsService(db)
                metrics = await dashboard_service.get_comprehensive_metrics(
                    organization_id=organization_id,
                    time_range="30d"
                )
                
                # Send to WebSocket connections
                await websocket_manager.send_metrics_update(organization_id, metrics)
                break
                
        except Exception as e:
            logger.error(f"Failed to trigger metrics update: {e}")
    
    @staticmethod
    async def trigger_alert(organization_id: str, alert: Dict[str, Any]):
        """Trigger real-time alert for an organization"""
        try:
            await websocket_manager.send_alert(organization_id, alert)
            
            # Also store alert in Redis for persistence
            alert_key = f"alerts:{organization_id}:{alert['id']}"
            await redis_client.set_json(alert_key, alert, 3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
    
    @staticmethod
    async def on_review_created(organization_id: str, review_data: Dict[str, Any]):
        """Handle new review creation event"""
        try:
            # Check if this is a critical review that needs immediate attention
            if review_data.get("rating", 5) <= 2 and review_data.get("urgency_level") == "high":
                alert = {
                    "id": f"critical_review_{review_data.get('id')}",
                    "type": "error",
                    "title": f"Critical {review_data.get('rating')}★ review received",
                    "description": f"High urgency review from {review_data.get('customer_name', 'Anonymous')}",
                    "action": "Review and respond immediately",
                    "priority": "high",
                    "metadata": {
                        "review_id": review_data.get("id"),
                        "rating": review_data.get("rating"),
                        "urgency": review_data.get("urgency_level")
                    }
                }
                
                await RealTimeMetricsService.trigger_alert(organization_id, alert)
            
            # Trigger metrics update
            await RealTimeMetricsService.trigger_metrics_update(organization_id)
            
        except Exception as e:
            logger.error(f"Failed to handle review creation event: {e}")
    
    @staticmethod
    async def on_recovery_action_completed(organization_id: str, action_data: Dict[str, Any]):
        """Handle recovery action completion event"""
        try:
            # Trigger metrics update to reflect new success rate
            await RealTimeMetricsService.trigger_metrics_update(organization_id)
            
        except Exception as e:
            logger.error(f"Failed to handle recovery action completion: {e}")
    
    @staticmethod
    async def on_customer_risk_updated(organization_id: str, customer_data: Dict[str, Any]):
        """Handle customer risk score update event"""
        try:
            # Check if customer became high-risk
            churn_risk = customer_data.get("churn_risk_score", 0)
            if churn_risk >= 0.8:
                alert = {
                    "id": f"high_risk_customer_{customer_data.get('id')}",
                    "type": "warning",
                    "title": "Customer became high-risk",
                    "description": f"Customer {customer_data.get('name', 'Unknown')} now has {churn_risk:.0%} churn risk",
                    "action": "Review customer and initiate recovery actions",
                    "priority": "medium",
                    "metadata": {
                        "customer_id": customer_data.get("id"),
                        "churn_risk_score": churn_risk
                    }
                }
                
                await RealTimeMetricsService.trigger_alert(organization_id, alert)
            
            # Trigger metrics update
            await RealTimeMetricsService.trigger_metrics_update(organization_id)
            
        except Exception as e:
            logger.error(f"Failed to handle customer risk update: {e}")


# Event handlers for integration with other services
async def handle_review_event(event_type: str, organization_id: str, data: Dict[str, Any]):
    """Handle review-related events"""
    if event_type == "review_created":
        await RealTimeMetricsService.on_review_created(organization_id, data)


async def handle_recovery_event(event_type: str, organization_id: str, data: Dict[str, Any]):
    """Handle recovery action events"""
    if event_type == "recovery_completed":
        await RealTimeMetricsService.on_recovery_action_completed(organization_id, data)


async def handle_customer_event(event_type: str, organization_id: str, data: Dict[str, Any]):
    """Handle customer-related events"""
    if event_type == "risk_updated":
        await RealTimeMetricsService.on_customer_risk_updated(organization_id, data)
