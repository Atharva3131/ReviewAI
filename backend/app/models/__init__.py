"""
Database models package
Import all models to ensure they are registered with SQLAlchemy
"""

from .organization import Organization
from .user import User, UserRole
from .review import Review, ReviewPlatform, UrgencyLevel, ReviewStatus, IssueCategory
from .customer import Customer
from .support_ticket import SupportTicket, TicketStatus, TicketPriority, TicketCategory
from .recovery_action import RecoveryAction, ActionType, ActionStatus, ActionPriority
from .agent_decision import AgentDecision, InputType, DecisionType, DecisionStatus
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
