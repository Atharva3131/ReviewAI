"""
Database models package
Import all models to ensure they are registered with SQLAlchemy
"""

from .agent_decision import AgentDecision, DecisionStatus, DecisionType, InputType
from .customer import Customer
from .organization import Organization
from .recovery_action import ActionPriority, ActionStatus, ActionType, RecoveryAction
from .review import IssueCategory, Review, ReviewPlatform, ReviewStatus, UrgencyLevel
from .support_ticket import SupportTicket, TicketCategory, TicketPriority, TicketStatus
from .user import User, UserRole

# Note: embedding model requires pgvector extension - enable it in Supabase first
# from .embedding import Embedding, ContentType, EmbeddingModel, EmbeddingService

__all__ = [
    # Models
    "Organization",
    "User",
    "Review",
    "Customer",
    "SupportTicket",
    "RecoveryAction",
    "AgentDecision",
    # "Embedding",  # Requires pgvector extension
    # Enums
    "UserRole",
    "ReviewPlatform",
    "UrgencyLevel",
    "ReviewStatus",
    "IssueCategory",
    "TicketStatus",
    "TicketPriority",
    "TicketCategory",
    "ActionType",
    "ActionStatus",
    "ActionPriority",
    "InputType",
    "DecisionType",
    "DecisionStatus",
    # "ContentType",  # Requires pgvector extension
    # "EmbeddingModel",  # Requires pgvector extension
    # Services
    # "EmbeddingService"  # Requires pgvector extension
]
