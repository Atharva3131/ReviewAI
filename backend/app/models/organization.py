"""Organization model for multi-tenant architecture"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Organization(Base):
    """Organization model for multi-tenant support"""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    users: Mapped[List[Any]] = relationship(
        "User", back_populates="organization", cascade="all, delete-orphan"
    )
    reviews: Mapped[List[Any]] = relationship(
        "Review", back_populates="organization", cascade="all, delete-orphan"
    )
    customers: Mapped[List[Any]] = relationship(
        "Customer", back_populates="organization", cascade="all, delete-orphan"
    )
    support_tickets: Mapped[List[Any]] = relationship(
        "SupportTicket", back_populates="organization", cascade="all, delete-orphan"
    )
    recovery_actions: Mapped[List[Any]] = relationship(
        "RecoveryAction", back_populates="organization", cascade="all, delete-orphan"
    )
    agent_decisions: Mapped[List[Any]] = relationship(
        "AgentDecision", back_populates="organization", cascade="all, delete-orphan"
    )
    # embeddings = relationship("Embedding", back_populates="organization", cascade="all, delete-orphan")  # Requires pgvector

    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}')>"

    @property
    def user_count(self) -> int:
        """Get number of users in organization"""
        return len(cast(Any, self.users)) if self.users else 0

    @property
    def review_count(self) -> int:
        """Get number of reviews for organization"""
        return len(cast(Any, self.reviews)) if self.reviews else 0

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get organization setting by key"""
        if not self.settings:
            return default
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """Set organization setting"""
        current_settings = dict(self.settings or {})
        current_settings[key] = value
        self.settings = current_settings

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
            "review_count": self.review_count,
        }
