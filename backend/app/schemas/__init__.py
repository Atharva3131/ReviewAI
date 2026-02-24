"""
Pydantic schemas for request/response validation
"""

# Base schemas
from .base import (
    TimestampMixin,
    UUIDMixin,
    OrganizationMixin,
    PaginationParams,
    SortParams,
    FilterParams,
    APIResponse,
    PaginatedResponse,
    ErrorResponse,
    ValidationErrorResponse,
    CommonValidators,
    StatusEnum,
    PriorityEnum,
    UrgencyEnum,
    PlatformEnum,
    CategoryEnum,
    ActionTypeEnum,
    EmailStr,
    PhoneStr,
    PasswordStr
)

# Authentication schemas
from .auth import (
    UserRegistration,
    UserResponse,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChange,
    EmailVerificationRequest,
    OrganizationResponse,
    AuthStatus
)

# Review schemas
from .review import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewIngest,
    ReviewAnalysis,
    ReviewListFilter,
    BulkReviewUpdate
)

# Agent schemas
from .agent import (
    AgentDecisionRequest,
    AgentDecisionResponse,
    DecisionApprovalRequest,
    DecisionExecutionRequest,
    AgentDecisionListFilter
)

# Customer schemas
from .customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListFilter,
    SupportTicketCreate as CustomerSupportTicketCreate,
    SupportTicketUpdate as CustomerSupportTicketUpdate,
    SupportTicketResponse as CustomerSupportTicketResponse,
    RecoveryActionCreate,
    RecoveryActionUpdate,
    RecoveryActionResponse,
    CustomerRecoveryRequest,
    CustomerRecoveryResponse,
    RiskAssessment,
    BulkCustomerUpdate,
    BulkRecoveryRequest,
    BulkOperationResponse
)

# Support Ticket schemas (comprehensive)
from .support_ticket import (
    SupportTicketCreate,
    SupportTicketUpdate,
    SupportTicketResponse,
    SupportTicketListResponse,
    TicketAssignRequest,
    TicketResolveRequest,
    TicketReopenRequest,
    TicketSatisfactionRequest,
    TicketResponseRequest,
    TicketAnalyzeRequest,
    TicketAnalyzeResponse,
    TicketStatsResponse
)

# Dashboard schemas
from .dashboard import (
    DashboardMetrics,
    DashboardKPIs,
    ActivityFeed,
    ActivityItem,
    SentimentTrends,
    ActionQueue,
    MetricsRequest,
    ReviewAnalytics,
    CustomerAnalytics,
    AgentAnalytics,
    ComprehensiveAnalytics,
    RealTimeUpdate,
    MetricsSubscription
)

__all__ = [
    # Base
    "TimestampMixin",
    "UUIDMixin", 
    "OrganizationMixin",
    "PaginationParams",
    "SortParams",
    "FilterParams",
    "APIResponse",
    "PaginatedResponse",
    "ErrorResponse",
    "ValidationErrorResponse",
    "CommonValidators",
    "StatusEnum",
    "PriorityEnum",
    "UrgencyEnum",
    "PlatformEnum",
    "CategoryEnum",
    "ActionTypeEnum",
    "EmailStr",
    "PhoneStr",
    "PasswordStr",
    
    # Auth
    "UserRegistration",
    "UserResponse",
    "UserLogin",
    "TokenResponse",
    "RefreshTokenRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "PasswordChange",
    "EmailVerificationRequest",
    "OrganizationResponse",
    "AuthStatus",
    
    # Reviews
    "ReviewCreate",
    "ReviewUpdate",
    "ReviewResponse",
    "ReviewIngest",
    "ReviewAnalysis",
    "ReviewListFilter",
    "BulkReviewUpdate",
    
    # Agents
    "AgentDecisionRequest",
    "AgentDecisionResponse",
    "DecisionApprovalRequest",
    "DecisionExecutionRequest",
    "AgentDecisionListFilter",
    
    # Customers
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    "CustomerListFilter",
    "CustomerSupportTicketCreate",
    "CustomerSupportTicketUpdate",
    "CustomerSupportTicketResponse",
    "RecoveryActionCreate",
    "RecoveryActionUpdate",
    "RecoveryActionResponse",
    "CustomerRecoveryRequest",
    "CustomerRecoveryResponse",
    "RiskAssessment",
    "BulkCustomerUpdate",
    "BulkRecoveryRequest",
    "BulkOperationResponse",
    
    # Support Tickets
    "SupportTicketCreate",
    "SupportTicketUpdate",
    "SupportTicketResponse",
    "SupportTicketListResponse",
    "TicketAssignRequest",
    "TicketResolveRequest",
    "TicketReopenRequest",
    "TicketSatisfactionRequest",
    "TicketResponseRequest",
    "TicketAnalyzeRequest",
    "TicketAnalyzeResponse",
    "TicketStatsResponse",
    
    # Dashboard
    "DashboardMetrics",
    "DashboardKPIs",
    "ActivityFeed",
    "ActivityItem",
    "SentimentTrends",
    "ActionQueue",
    "MetricsRequest",
    "ReviewAnalytics",
    "CustomerAnalytics",
    "AgentAnalytics",
    "ComprehensiveAnalytics",
    "RealTimeUpdate",
    "MetricsSubscription"
]
