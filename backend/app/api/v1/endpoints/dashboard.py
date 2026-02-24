"""
Dashboard API endpoints for metrics and KPIs
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import json

from app.core.database import get_async_db
from app.core.dependencies import get_current_user, get_current_organization
from app.services.dashboard_service import DashboardMetricsService, KPICalculationService
from app.services.realtime_metrics import websocket_manager, RealTimeMetricsService
from app.schemas.dashboard import (
    DashboardMetricsResponse,
    KPIResponse,
    ActivityFeedResponse,
    MetricsTrendResponse,
    AlertResponse
)
from app.models.user import User
from app.models.organization import Organization

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/metrics", response_model=DashboardMetricsResponse, tags=["dashboard"])
async def get_dashboard_metrics(
    time_range: str = Query("30d", pattern="^(7d|30d|90d|1y)$", description="Time range for metrics"),
    refresh_cache: bool = Query(False, description="Force refresh cached metrics"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
):
    """
    Get comprehensive dashboard metrics and KPIs
    
    Returns all dashboard metrics including:
    - Key Performance Indicators (KPIs)
    - Trend data for charts
    - Recent activity feed
    - Chart data for visualizations
    - System alerts
    
    **Time Ranges:**
    - `7d`: Last 7 days
    - `30d`: Last 30 days (default)
    - `90d`: Last 90 days
    - `1y`: Last year
    
    **Caching:**
    - Metrics are cached for 5 minutes for performance
    - Use `refresh_cache=true` to force refresh
    """
    try:
        # Verify organization access
        organization_id = str(organization.id)
        
        # Clear cache if refresh requested
        if refresh_cache:
            from app.core.redis import CacheManager, redis_client
            cache_key = CacheManager.make_key(
                "dashboard_metrics", 
                organization_id, 
                time_range,
                prefix="revive_ai"
            )
            await redis_client.delete(cache_key)
        
        # Get metrics
        dashboard_service = DashboardMetricsService(db)
        metrics = await dashboard_service.get_comprehensive_metrics(
            organization_id=organization_id,
            time_range=time_range
        )
        
        logger.info(
            f"Dashboard metrics retrieved for organization {organization_id}",
            extra={
                "organization_id": organization_id,
                "time_range": time_range,
                "user_id": str(current_user.id),
                "refresh_cache": refresh_cache
            }
        )
        
        return DashboardMetricsResponse(**metrics)
        
    except Exception as e:
        logger.error(
            f"Failed to get dashboard metrics: {e}",
            extra={
                "organization_id": getattr(current_user, "organization_id", None),
                "time_range": time_range,
                "user_id": str(current_user.id)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard metrics"
        )


@router.get("/kpis", response_model=KPIResponse, tags=["dashboard"])
async def get_kpis(
    time_range: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
):
    """
    Get Key Performance Indicators (KPIs) only
    
    Returns just the KPI values without charts or activity feed.
    Useful for lightweight dashboard updates or mobile apps.
    """
    try:
        organization_id = str(organization.id)
        
        dashboard_service = DashboardMetricsService(db)
        
        # Parse time range
        days = dashboard_service._parse_time_range(time_range)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Calculate KPIs
        kpis = await dashboard_service._calculate_kpis(organization_id, start_date)
        
        return KPIResponse(
            kpis=kpis,
            time_range=time_range,
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to get KPIs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve KPIs"
        )


@router.get("/activity", response_model=ActivityFeedResponse, tags=["dashboard"])
async def get_activity_feed(
    limit: int = Query(10, ge=1, le=50, description="Number of activities to return"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
):
    """
    Get recent activity feed
    
    Returns recent activities including:
    - New reviews received
    - Recovery actions executed
    - Agent decisions made
    - System alerts
    """
    try:
        organization_id = str(organization.id)
        
        dashboard_service = DashboardMetricsService(db)
        activities = await dashboard_service._generate_activity_feed(
            organization_id=organization_id,
            limit=limit
        )
        
        return ActivityFeedResponse(
            activities=activities,
            total_count=len(activities),
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to get activity feed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve activity feed"
        )


@router.get("/trends", response_model=MetricsTrendResponse, tags=["dashboard"])
async def get_metrics_trends(
    time_range: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    metric_type: Optional[str] = Query(None, pattern="^(sentiment|reviews|recovery)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
):
    """
    Get metrics trends for charts
    
    Returns time-series data for dashboard charts:
    - Sentiment trends over time
    - Review volume trends
    - Recovery action trends
    
    **Metric Types:**
    - `sentiment`: Sentiment score trends
    - `reviews`: Review volume trends  
    - `recovery`: Recovery action trends
    - `null`: All trends (default)
    """
    try:
        organization_id = str(organization.id)
        
        dashboard_service = DashboardMetricsService(db)
        
        days = dashboard_service._parse_time_range(time_range)
        start_date = datetime.utcnow() - timedelta(days=days)
        
        trends = await dashboard_service._calculate_trends(organization_id, start_date)
        
        # Filter by metric type if specified
        if metric_type:
            if metric_type == "sentiment":
                trends = {"sentiment_over_time": trends.get("sentiment_over_time", [])}
            elif metric_type == "reviews":
                trends = {"review_volume_over_time": trends.get("review_volume_over_time", [])}
            elif metric_type == "recovery":
                trends = {"recovery_actions_over_time": trends.get("recovery_actions_over_time", [])}
        
        return MetricsTrendResponse(
            trends=trends,
            time_range=time_range,
            metric_type=metric_type,
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to get metrics trends: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics trends"
        )


@router.get("/alerts", response_model=AlertResponse, tags=["dashboard"])
async def get_dashboard_alerts(
    priority: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
):
    """
    Get dashboard alerts and notifications
    
    Returns system alerts including:
    - High-risk customer alerts
    - Negative review spikes
    - System performance issues
    - Recovery action failures
    
    **Priority Levels:**
    - `low`: Informational alerts
    - `medium`: Attention needed
    - `high`: Urgent action required
    - `critical`: Immediate action required
    """
    try:
        organization_id = str(organization.id)
        
        dashboard_service = DashboardMetricsService(db)
        alerts = await dashboard_service._generate_alerts(organization_id)
        
        # Filter by priority if specified
        if priority:
            alerts = [alert for alert in alerts if alert.get("priority") == priority]
        
        return AlertResponse(
            alerts=alerts,
            total_count=len(alerts),
            priority_filter=priority,
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to get dashboard alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard alerts"
        )


@router.get("/kpis/average-rating", tags=["dashboard"])
async def get_average_rating(
    time_range: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
):
    """
    Get detailed average rating calculation
    
    Returns comprehensive rating analysis including:
    - Current average rating
    - Rating distribution
    - Trend analysis
    - Comparison with previous period
    """
    try:
        organization_id = str(organization.id)
        
        kpi_service = KPICalculationService(db)
        
        days = int(time_range.rstrip('dy'))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        avg_rating, total_reviews = await kpi_service.calculate_average_rating(
            organization_id=organization_id,
            start_date=start_date
        )
        
        # Get previous period for comparison
        prev_start = start_date - timedelta(days=days)
        prev_avg_rating, prev_total_reviews = await kpi_service.calculate_average_rating(
            organization_id=organization_id,
            start_date=prev_start,
            end_date=start_date
        )
        
        # Calculate trend
        trend = "neutral"
        if prev_avg_rating > 0:
            change = ((avg_rating - prev_avg_rating) / prev_avg_rating) * 100
            if change > 5:
                trend = "up"
            elif change < -5:
                trend = "down"
        
        return {
            "average_rating": round(avg_rating, 2),
            "total_reviews": total_reviews,
            "previous_rating": round(prev_avg_rating, 2),
            "previous_total_reviews": prev_total_reviews,
            "trend": trend,
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get average rating: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve average rating"
        )


@router.get("/kpis/at-risk-customers", tags=["dashboard"])
async def get_at_risk_customers(
    churn_threshold: float = Query(0.7, ge=0.0, le=1.0),
    review_threshold: float = Query(0.6, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
):
    """
    Get detailed at-risk customer analysis
    
    Returns comprehensive at-risk customer breakdown including:
    - High churn risk customers
    - High bad review likelihood customers
    - Customers with both risks
    - Risk distribution analysis
    """
    try:
        organization_id = str(organization.id)
        
        kpi_service = KPICalculationService(db)
        at_risk_data = await kpi_service.calculate_at_risk_customer_count(
            organization_id=organization_id,
            churn_threshold=churn_threshold,
            review_threshold=review_threshold
        )
        
        return {
            **at_risk_data,
            "thresholds": {
                "churn_risk": churn_threshold,
                "review_risk": review_threshold
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get at-risk customers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve at-risk customers"
        )


@router.get("/kpis/recovery-success-rate", tags=["dashboard"])
async def get_recovery_success_rate(
    time_range: str = Query("30d", pattern="^(7d|30d|90d|1y)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
):
    """
    Get detailed recovery success rate analysis
    
    Returns comprehensive recovery performance including:
    - Overall success rate
    - Action breakdown by status
    - Success rate by action type
    - Trend analysis
    """
    try:
        organization_id = str(organization.id)
        
        kpi_service = KPICalculationService(db)
        
        days = int(time_range.rstrip('dy'))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        recovery_data = await kpi_service.calculate_recovery_success_rate(
            organization_id=organization_id,
            start_date=start_date
        )
        
        return {
            **recovery_data,
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get recovery success rate: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recovery success rate"
        )


@router.post("/metrics/refresh", tags=["dashboard"])
async def refresh_dashboard_cache(
    time_ranges: List[str] = Query(["30d"], description="Time ranges to refresh"),
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
):
    """
    Refresh dashboard metrics cache
    
    Forces refresh of cached dashboard metrics for specified time ranges.
    Useful after bulk data imports or system maintenance.
    """
    try:
        organization_id = str(organization.id)
        
        from app.core.redis import CacheManager, redis_client
        
        refreshed_keys = []
        for time_range in time_ranges:
            cache_key = CacheManager.make_key(
                "dashboard_metrics", 
                organization_id, 
                time_range,
                prefix="revive_ai"
            )
            await redis_client.delete(cache_key)
            refreshed_keys.append(cache_key)
        
        logger.info(
            f"Dashboard cache refreshed for organization {organization_id}",
            extra={
                "organization_id": organization_id,
                "time_ranges": time_ranges,
                "user_id": str(current_user.id),
                "refreshed_keys": refreshed_keys
            }
        )
        
        return {
            "message": "Dashboard cache refreshed successfully",
            "time_ranges": time_ranges,
            "refreshed_keys": len(refreshed_keys),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh dashboard cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh dashboard cache"
        )


@router.websocket("/ws/metrics")
async def websocket_metrics_endpoint(
    websocket: WebSocket,
    organization_id: str = Query(..., description="Organization ID for metrics"),
    user_id: str = Query(..., description="User ID for connection tracking")
):
    """
    WebSocket endpoint for real-time dashboard metrics updates
    
    Provides real-time updates for:
    - KPI changes
    - New alerts
    - Activity feed updates
    - System status changes
    
    **Connection Parameters:**
    - `organization_id`: Organization UUID for metrics scope
    - `user_id`: User UUID for connection tracking
    
    **Message Types:**
    - `metrics_update`: Updated KPI values and trends
    - `alert`: New system alerts
    - `activity`: New activity feed items
    - `status`: Connection status updates
    """
    try:
        # Connect to WebSocket manager
        await websocket_manager.connect(websocket, organization_id, user_id)
        
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "data": {
                "organization_id": organization_id,
                "user_id": user_id,
                "connected_at": datetime.utcnow().isoformat()
            }
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                message = await websocket.receive_text()
                data = json.loads(message)
                
                # Handle different message types
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
                elif data.get("type") == "request_update":
                    # Client requesting immediate metrics update
                    await RealTimeMetricsService.trigger_metrics_update(organization_id)
                
                elif data.get("type") == "subscribe":
                    # Client subscribing to specific metric types
                    # TODO: Implement selective subscriptions
                    pass
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # Invalid JSON received
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Internal server error"
                }))
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for organization {organization_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Clean up connection
        await websocket_manager.disconnect(websocket)


@router.get("/ws/stats", tags=["dashboard"])
async def get_websocket_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get WebSocket connection statistics
    
    Returns information about active WebSocket connections,
    useful for monitoring and debugging real-time features.
    """
    try:
        # TODO: Add admin permission check
        stats = websocket_manager.get_connection_stats()
        
        return {
            "websocket_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve WebSocket statistics"
        )


