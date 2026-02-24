"""
Dashboard response schemas for metrics and KPIs
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime


class KPIValue(BaseModel):
    """Individual KPI value with trend information"""
    value: float = Field(..., description="Current KPI value")
    trend: str = Field(..., description="Trend direction: up, down, or neutral")
    previous_value: Optional[float] = Field(None, description="Previous period value for comparison")


class KPIData(BaseModel):
    """Collection of all KPI values"""
    average_rating: KPIValue = Field(..., description="Average review rating")
    monthly_reviews: KPIValue = Field(..., description="Review count for the period")
    at_risk_customers: KPIValue = Field(..., description="Number of at-risk customers")
    recovery_success_rate: KPIValue = Field(..., description="Recovery action success rate percentage")


class ActivityItem(BaseModel):
    """Individual activity feed item"""
    id: str = Field(..., description="Unique activity identifier")
    type: str = Field(..., description="Activity type: review, recovery_action, agent_decision")
    title: str = Field(..., description="Activity title")
    description: str = Field(..., description="Activity description")
    timestamp: str = Field(..., description="Activity timestamp in ISO format")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional activity metadata")


class AlertItem(BaseModel):
    """Dashboard alert item"""
    id: str = Field(..., description="Unique alert identifier")
    type: str = Field(..., description="Alert type: info, warning, error, success")
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")
    action: Optional[str] = Field(None, description="Recommended action")
    priority: str = Field(..., description="Alert priority: low, medium, high, critical")


class TrendDataPoint(BaseModel):
    """Individual data point for trend charts"""
    timestamp: str = Field(..., description="Data point timestamp")
    value: float = Field(..., description="Data point value")
    label: Optional[str] = Field(None, description="Human-readable label")


class ChartData(BaseModel):
    """Chart data for dashboard visualizations"""
    sentiment_distribution: Dict[str, int] = Field(
        default_factory=dict, 
        description="Sentiment distribution: positive, neutral, negative"
    )
    rating_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Rating distribution by star rating (1-5)"
    )
    issue_categories: Dict[str, int] = Field(
        default_factory=dict,
        description="Issue category distribution"
    )


class TrendData(BaseModel):
    """Trend data for time-series charts"""
    sentiment_over_time: List[TrendDataPoint] = Field(
        default_factory=list,
        description="Sentiment trends over time"
    )
    review_volume_over_time: List[TrendDataPoint] = Field(
        default_factory=list,
        description="Review volume trends over time"
    )
    recovery_actions_over_time: List[TrendDataPoint] = Field(
        default_factory=list,
        description="Recovery action trends over time"
    )


class DashboardMetadata(BaseModel):
    """Metadata about dashboard metrics"""
    organization_id: str = Field(..., description="Organization UUID")
    time_range: str = Field(..., description="Time range for metrics")
    start_date: str = Field(..., description="Start date in ISO format")
    end_date: str = Field(..., description="End date in ISO format")
    generated_at: str = Field(..., description="Generation timestamp in ISO format")
    cache_ttl: int = Field(..., description="Cache TTL in seconds")


class DashboardMetricsResponse(BaseModel):
    """Complete dashboard metrics response"""
    kpis: KPIData = Field(..., description="Key Performance Indicators")
    trends: TrendData = Field(..., description="Trend data for charts")
    activity_feed: List[ActivityItem] = Field(..., description="Recent activity feed")
    charts: ChartData = Field(..., description="Chart data for visualizations")
    alerts: List[AlertItem] = Field(..., description="Dashboard alerts")
    metadata: DashboardMetadata = Field(..., description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "kpis": {
                    "average_rating": {
                        "value": 4.2,
                        "trend": "up",
                        "previous_value": 4.0
                    },
                    "monthly_reviews": {
                        "value": 127,
                        "trend": "up",
                        "previous_value": 98
                    },
                    "at_risk_customers": {
                        "value": 23,
                        "trend": "down",
                        "previous_value": 31
                    },
                    "recovery_success_rate": {
                        "value": 78.5,
                        "trend": "up",
                        "previous_value": 72.1
                    }
                },
                "trends": {
                    "sentiment_over_time": [
                        {
                            "timestamp": "2024-01-01T00:00:00Z",
                            "value": 0.65,
                            "label": "Jan 1"
                        }
                    ],
                    "review_volume_over_time": [
                        {
                            "timestamp": "2024-01-01T00:00:00Z",
                            "value": 45,
                            "label": "Jan 1"
                        }
                    ],
                    "recovery_actions_over_time": [
                        {
                            "timestamp": "2024-01-01T00:00:00Z",
                            "value": 12,
                            "label": "Jan 1"
                        }
                    ]
                },
                "activity_feed": [
                    {
                        "id": "review_123",
                        "type": "review",
                        "title": "New 2★ review received",
                        "description": "🔴 High urgency - John Doe",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "metadata": {
                            "review_id": "123",
                            "rating": 2,
                            "urgency": "high"
                        }
                    }
                ],
                "charts": {
                    "sentiment_distribution": {
                        "positive": 65,
                        "neutral": 20,
                        "negative": 15
                    },
                    "rating_distribution": {
                        "1": 5,
                        "2": 10,
                        "3": 15,
                        "4": 35,
                        "5": 35
                    },
                    "issue_categories": {
                        "support": 45,
                        "quality": 32,
                        "delivery": 28,
                        "pricing": 15
                    }
                },
                "alerts": [
                    {
                        "id": "high_risk_customers",
                        "type": "warning",
                        "title": "5 high-risk customers detected",
                        "description": "Customers with churn risk score ≥ 80% need immediate attention",
                        "action": "Review customer recovery recommendations",
                        "priority": "high"
                    }
                ],
                "metadata": {
                    "organization_id": "org_123",
                    "time_range": "30d",
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-01-31T23:59:59Z",
                    "generated_at": "2024-01-31T12:00:00Z",
                    "cache_ttl": 300
                }
            }
        }


class KPIResponse(BaseModel):
    """KPI-only response for lightweight requests"""
    kpis: KPIData = Field(..., description="Key Performance Indicators")
    time_range: str = Field(..., description="Time range for KPIs")
    generated_at: str = Field(..., description="Generation timestamp")


class ActivityFeedResponse(BaseModel):
    """Activity feed response"""
    activities: List[ActivityItem] = Field(..., description="Activity feed items")
    total_count: int = Field(..., description="Total number of activities")
    generated_at: str = Field(..., description="Generation timestamp")


class MetricsTrendResponse(BaseModel):
    """Metrics trend response"""
    trends: TrendData = Field(..., description="Trend data")
    time_range: str = Field(..., description="Time range for trends")
    metric_type: Optional[str] = Field(None, description="Specific metric type filter")
    generated_at: str = Field(..., description="Generation timestamp")


class AlertResponse(BaseModel):
    """Dashboard alerts response"""
    alerts: List[AlertItem] = Field(..., description="Dashboard alerts")
    total_count: int = Field(..., description="Total number of alerts")
    priority_filter: Optional[str] = Field(None, description="Priority filter applied")
    generated_at: str = Field(..., description="Generation timestamp")


class AverageRatingResponse(BaseModel):
    """Detailed average rating response"""
    average_rating: float = Field(..., description="Current average rating")
    total_reviews: int = Field(..., description="Total reviews in period")
    previous_rating: float = Field(..., description="Previous period average rating")
    previous_total_reviews: int = Field(..., description="Previous period total reviews")
    trend: str = Field(..., description="Trend direction")
    time_range: str = Field(..., description="Time range")
    generated_at: str = Field(..., description="Generation timestamp")


class AtRiskCustomersResponse(BaseModel):
    """At-risk customers detailed response"""
    high_churn_risk: int = Field(..., description="Customers with high churn risk")
    high_review_risk: int = Field(..., description="Customers with high bad review likelihood")
    both_risks: int = Field(..., description="Customers with both risks")
    total_at_risk: int = Field(..., description="Total at-risk customers")
    thresholds: Dict[str, float] = Field(..., description="Risk thresholds used")
    generated_at: str = Field(..., description="Generation timestamp")


class RecoverySuccessRateResponse(BaseModel):
    """Recovery success rate detailed response"""
    success_rate: float = Field(..., description="Success rate percentage")
    total_actions: int = Field(..., description="Total recovery actions")
    successful_actions: int = Field(..., description="Successful recovery actions")
    failed_actions: int = Field(..., description="Failed recovery actions")
    pending_actions: int = Field(..., description="Pending recovery actions")
    time_range: str = Field(..., description="Time range")
    generated_at: str = Field(..., description="Generation timestamp")


class CacheRefreshResponse(BaseModel):
    """Cache refresh response"""
    message: str = Field(..., description="Success message")
    time_ranges: List[str] = Field(..., description="Time ranges refreshed")
    refreshed_keys: int = Field(..., description="Number of cache keys refreshed")
    timestamp: str = Field(..., description="Refresh timestamp")


# Aliases for backward compatibility
DashboardMetrics = DashboardMetricsResponse
DashboardKPIs = KPIData
ActivityFeed = ActivityFeedResponse
SentimentTrends = TrendData
ActionQueue = ActivityFeedResponse
MetricsRequest = BaseModel
ReviewAnalytics = ChartData
CustomerAnalytics = ChartData
AgentAnalytics = ChartData
ComprehensiveAnalytics = DashboardMetricsResponse
RealTimeUpdate = ActivityItem
MetricsSubscription = BaseModel
