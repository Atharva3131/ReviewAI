"""Organization model for multi-tenant architecture"""
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Organization(Base):
    """Organization model for multi-tenant support"""
    
    __tablename__ = "organizations"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=True, index=True)
    settings = Column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="organization", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="organization", cascade="all, delete-orphan")
    support_tickets = relationship("SupportTicket", back_populates="organization", cascade="all, delete-orphan")
    recovery_actions = relationship("RecoveryAction", back_populates="organization", cascade="all, delete-orphan")
    agent_decisions = relationship("AgentDecision", back_populates="organization", cascade="all, delete-orphan")
    # embeddings = relationship("Embedding", back_populates="organization", cascade="all, delete-orphan")  # Requires pgvector
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}')>"
    
    @property
    def user_count(self):
        """Get number of users in organization"""
        return len(self.users)
    
    @property
    def review_count(self):
        """Get number of reviews for organization"""
        return len(self.reviews)
    
    def get_setting(self, key: str, default=None):
        """Get organization setting by key"""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value):
        """Set organization setting"""
        if self.settings is None:
            self.settings = {}
        self.settings[key] = value
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "domain": self.domain,
            "settings": self.settings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_count": self.user_count,
            "review_count": self.review_count
        }
