"""
Agent decision schemas for request/response validation
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.agent_decision import DecisionStatus, DecisionType, InputType


class AgentDecisionRequest(BaseModel):
    """Request schema for agent decision"""

    input_type: str = Field(..., pattern="^(review|support_ticket|customer_profile)$")
    input_id: str
    context: Optional[Dict[str, Any]] = None
    business_rules: Optional[Dict[str, Any]] = None

    @field_validator("input_id")
    def validate_input_id(cls, v):
        """Validate input ID format"""
        if not v or not v.strip():
            raise ValueError("Input ID cannot be empty")
        return v.strip()


class AgentDecisionResponse(BaseModel):
    """Response schema for agent decision"""

    decision_id: str
    input_type: str
    input_id: str
    input_summary: str
    decision_type: str
    status: str
    confidence_score: float
    confidence_level: str
    reasoning: str
    generated_content: Optional[str]
    content_type: Optional[str]
    requires_approval: bool
    requires_human_review: bool
    processing_time_ms: int
    context_factors: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    rule_name: Optional[str]
    model_version: Optional[str]
    model_provider: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AgentDecisionValidationRequest(BaseModel):
    """Request schema for decision validation"""

    action: str = Field(..., pattern="^(approve|reject)$")
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("notes")
    def validate_notes(cls, v):
        """Validate notes"""
        if v and len(v.strip()) == 0:
            return None
        return v.strip() if v else None


class AgentDecisionExecutionRequest(BaseModel):
    """Request schema for decision execution"""

    execution_context: Optional[Dict[str, Any]] = None
    notify_customer: bool = True
    schedule_followup: bool = False
    followup_delay_hours: Optional[int] = Field(None, ge=1, le=168)  # 1 hour to 1 week


class AgentDecisionExecutionResponse(BaseModel):
    """Response schema for decision execution"""

    decision_id: str
    execution_status: str
    executed_at: Optional[datetime]
    executed_by: Optional[str]
    execution_result: Optional[Dict[str, Any]]
    message: str


class AgentDecisionFilter(BaseModel):
    """Filter schema for agent decisions"""

    input_type: Optional[str] = Field(
        None, pattern="^(review|support_ticket|customer_profile)$"
    )
    decision_type: Optional[str] = None
    status: Optional[str] = None
    confidence_min: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence_max: Optional[float] = Field(None, ge=0.0, le=1.0)
    requires_approval: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    executed_by: Optional[str] = None


class AgentDecisionStats(BaseModel):
    """Agent decision statistics"""

    total_decisions: int
    decisions_by_type: Dict[str, int]
    decisions_by_status: Dict[str, int]
    avg_confidence_score: float
    high_confidence_rate: float
    approval_rate: float
    execution_rate: float
    avg_processing_time_ms: float
    decisions_requiring_review: int
    recent_decisions: int


class DecisionRuleSummary(BaseModel):
    """Summary of a decision rule"""

    name: str
    action: str
    confidence: float
    priority: int
    reasoning: str
    rule_type: str


class DecisionRulesResponse(BaseModel):
    """Response schema for decision rules summary"""

    review_rules: List[DecisionRuleSummary]
    ticket_rules: List[DecisionRuleSummary]
    safety_rules: List[DecisionRuleSummary]
    total_rules: int
    last_updated: datetime


class AgentPerformanceMetrics(BaseModel):
    """Agent performance metrics"""

    decision_accuracy: float
    customer_satisfaction_score: Optional[float]
    response_time_avg_ms: float
    escalation_rate: float
    auto_resolution_rate: float
    human_override_rate: float
    successful_outcomes: int
    failed_outcomes: int
    pending_outcomes: int


class AgentDecisionOutcome(BaseModel):
    """Agent decision outcome tracking"""

    decision_id: str
    outcome_success: bool
    outcome_rating: Optional[float] = Field(None, ge=0.0, le=1.0)
    customer_feedback: Optional[str] = Field(None, max_length=2000)
    follow_up_required: bool = False
    lessons_learned: Optional[str] = Field(None, max_length=1000)


class AgentDecisionBulkRequest(BaseModel):
    """Bulk decision request"""

    input_items: List[Dict[str, Any]]
    common_context: Optional[Dict[str, Any]] = None
    business_rules: Optional[Dict[str, Any]] = None
    parallel_processing: bool = True

    @field_validator("input_items")
    def validate_input_items(cls, v):
        """Validate input items"""
        if not v or len(v) == 0:
            raise ValueError("At least one input item is required")
        if len(v) > 100:
            raise ValueError("Maximum 100 items allowed per bulk request")

        for item in v:
            if "input_type" not in item or "input_id" not in item:
                raise ValueError("Each item must have input_type and input_id")

        return v


class AgentDecisionBulkResponse(BaseModel):
    """Bulk decision response"""

    total_processed: int
    successful_decisions: int
    failed_decisions: int
    decisions: List[AgentDecisionResponse]
    errors: List[Dict[str, Any]]
    processing_time_ms: int


class AgentConfigurationRequest(BaseModel):
    """Agent configuration request"""

    confidence_thresholds: Optional[Dict[str, float]] = None
    auto_approval_rules: Optional[Dict[str, Any]] = None
    escalation_rules: Optional[Dict[str, Any]] = None
    notification_settings: Optional[Dict[str, Any]] = None
    custom_rules: Optional[List[Dict[str, Any]]] = None

    @field_validator("confidence_thresholds")
    def validate_confidence_thresholds(cls, v):
        """Validate confidence thresholds"""
        if v:
            for key, value in v.items():
                if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
                    raise ValueError(
                        f"Confidence threshold {key} must be between 0.0 and 1.0"
                    )
        return v


class AgentConfiguration(BaseModel):
    """Agent configuration response"""

    organization_id: str
    confidence_thresholds: Dict[str, float]
    auto_approval_enabled: bool
    auto_approval_rules: Dict[str, Any]
    escalation_rules: Dict[str, Any]
    notification_settings: Dict[str, Any]
    custom_rules_count: int
    last_updated: datetime
    updated_by: str


class AgentAuditLog(BaseModel):
    """Agent audit log entry"""

    id: str
    organization_id: str
    decision_id: str
    action: str
    performed_by: str
    timestamp: datetime
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]


class AgentHealthCheck(BaseModel):
    """Agent system health check"""

    status: str
    version: str
    uptime_seconds: int
    decisions_processed_today: int
    avg_response_time_ms: float
    error_rate_percent: float
    queue_length: int
    last_decision_at: Optional[datetime]
    system_resources: Dict[str, Any]
    dependencies_status: Dict[str, str]


# Aliases for backward compatibility
DecisionApprovalRequest = AgentDecisionValidationRequest
DecisionExecutionRequest = AgentDecisionExecutionRequest
AgentDecisionListFilter = AgentDecisionFilter
