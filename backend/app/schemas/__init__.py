"""
Pydantic schemas for request/response validation
"""

# Agent schemas
from .agent import (
    AgentDecisionListFilter,
    AgentDecisionRequest,
    AgentDecisionResponse,
    DecisionApprovalRequest,
    DecisionExecutionRequest,
)

# Authentication schemas
from .auth import (
    AuthStatus,
    EmailVerificationRequest,
    OrganizationResponse,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegistration,
    UserResponse,
)

# Base schemas
from .base import (
    ActionTypeEnum,
    APIResponse,
    CategoryEnum,
    CommonValidators,
    EmailStr,
    ErrorResponse,
    FilterParams,
    OrganizationMixin,
    PaginatedResponse,
    PaginationParams,
    PasswordStr,
    PhoneStr,
    PlatformEnum,
    PriorityEnum,
    SortParams,
    StatusEnum,
    TimestampMixin,
    UrgencyEnum,
    UUIDMixin,
    ValidationErrorResponse,
)

# Customer schemas
from .customer import (
    BulkCustomerUpdate,
    BulkOperationResponse,
    BulkRecoveryRequest,
    CustomerCreate,
    CustomerListFilter,
    CustomerRecoveryRequest,
    CustomerRecoveryResponse,
    CustomerResponse,
    CustomerUpdate,
    RecoveryActionCreate,
    RecoveryActionResponse,
    RecoveryActionUpdate,
    RiskAssessment,
)
from .customer import SupportTicketCreate as CustomerSupportTicketCreate
from .customer import SupportTicketResponse as CustomerSupportTicketResponse
from .customer import SupportTicketUpdate as CustomerSupportTicketUpdate

# Dashboard schemas
from .dashboard import (
    ActionQueue,
    ActivityFeed,
    ActivityItem,
    AgentAnalytics,
    ComprehensiveAnalytics,
    CustomerAnalytics,
    DashboardKPIs,
    DashboardMetrics,
    MetricsRequest,
    MetricsSubscription,
    RealTimeUpdate,
    ReviewAnalytics,
    SentimentTrends,
)

# Review schemas
from .review import (
    BulkReviewUpdate,
    ReviewAnalysis,
    ReviewCreate,
    ReviewIngest,
    ReviewListFilter,
    ReviewResponse,
    ReviewUpdate,
)

# Support Ticket schemas (comprehensive)
from .support_ticket import (
    SupportTicketCreate,
    SupportTicketListResponse,
    SupportTicketResponse,
    SupportTicketUpdate,
    TicketAnalyzeRequest,
    TicketAnalyzeResponse,
    TicketAssignRequest,
    TicketReopenRequest,
    TicketResolveRequest,
    TicketResponseRequest,
    TicketSatisfactionRequest,
    TicketStatsResponse,
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
    "MetricsSubscription",
]
