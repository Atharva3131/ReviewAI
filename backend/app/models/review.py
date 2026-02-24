"""Review model for reputation management"""
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, ForeignKey, Enum, DECIMAL, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from typing import List, Optional

from app.core.database import Base


class ReviewPlatform(str, enum.Enum):
    """Review platform enumeration"""
    GOOGLE = "google"
    YELP = "yelp"
    FACEBOOK = "facebook"
    TRUSTPILOT = "trustpilot"
    TRIPADVISOR = "tripadvisor"
    AMAZON = "amazon"
    OTHER = "other"


class UrgencyLevel(str, enum.Enum):
    """Review urgency level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReviewStatus(str, enum.Enum):
    """Review status enumeration"""
    PENDING = "pending"
    RESPONDED = "responded"
    ESCALATED = "escalated"
    IGNORED = "ignored"


class IssueCategory(str, enum.Enum):
    """Issue category enumeration"""
    SUPPORT = "support"
    PRICING = "pricing"
    DELIVERY = "delivery"
    QUALITY = "quality"
    BILLING = "billing"
    TECHNICAL = "technical"
    OTHER = "other"


class Review(Base):
    """Review model for managing customer reviews"""
    
    __tablename__ = "reviews"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )
    organization_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("organizations.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Review source information
    platform = Column(Enum(ReviewPlatform), nullable=False, index=True)
    external_id = Column(String(255), nullable=True, index=True)  # Platform-specific ID
    review_url = Column(Text, nullable=True)
    
    # Customer information
    customer_name = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)
    customer_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("customers.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    
    # Review content
    rating = Column(Integer, nullable=False, index=True)  # 1-5 stars
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    
    # AI Analysis results
    sentiment_score = Column(DECIMAL(3, 2), nullable=True, index=True)  # 0.00 to 1.00
    urgency_level = Column(Enum(UrgencyLevel), nullable=True, index=True)
    issue_categories = Column(ARRAY(Enum(IssueCategory)), nullable=True)
    
    # Processing status
    status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False, index=True)
    requires_private_recovery = Column(Boolean, default=False, nullable=False, index=True)
    
    # Response information
    public_response = Column(Text, nullable=True)
    public_response_date = Column(DateTime(timezone=True), nullable=True)
    internal_notes = Column(Text, nullable=True)
    
    # Metadata
    review_date = Column(DateTime(timezone=True), nullable=True)  # When review was posted
    processed_at = Column(DateTime(timezone=True), nullable=True)  # When AI processed it
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="reviews")
    customer = relationship("Customer", back_populates="reviews")
    recovery_actions = relationship("RecoveryAction", back_populates="review")
    # Note: agent_decisions relationship removed - use input_id query instead (polymorphic relationship)
    
    def __repr__(self):
        return f"<Review(id={self.id}, platform='{self.platform}', rating={self.rating})>"
    
    @property
    def is_positive(self) -> bool:
        """Check if review is positive (4-5 stars)"""
        return self.rating >= 4
    
    @property
    def is_negative(self) -> bool:
        """Check if review is negative (1-2 stars)"""
        return self.rating <= 2
    
    @property
    def is_neutral(self) -> bool:
        """Check if review is neutral (3 stars)"""
        return self.rating == 3
    
    @property
    def is_critical(self) -> bool:
        """Check if review is critical (needs immediate attention)"""
        return (
            self.rating <= 2 and 
            self.urgency_level == UrgencyLevel.HIGH
        )
    
    @property
    def sentiment_label(self) -> str:
        """Get human-readable sentiment label"""
        if self.sentiment_score is None:
            return "Unknown"
        
        score = float(self.sentiment_score)
        if score >= 0.7:
            return "Very Positive"
        elif score >= 0.5:
            return "Positive"
        elif score >= 0.3:
            return "Neutral"
        elif score >= 0.1:
            return "Negative"
        else:
            return "Very Negative"
    
    @property
    def days_since_posted(self) -> Optional[int]:
        """Get days since review was posted"""
        if not self.review_date:
            return None
        
        from datetime import datetime, timezone
        delta = datetime.now(timezone.utc) - self.review_date
        return delta.days
    
    def add_issue_category(self, category: IssueCategory):
        """Add issue category to review"""
        if self.issue_categories is None:
            self.issue_categories = []
        
        if category not in self.issue_categories:
            self.issue_categories.append(category)
    
    def remove_issue_category(self, category: IssueCategory):
        """Remove issue category from review"""
        if self.issue_categories and category in self.issue_categories:
            self.issue_categories.remove(category)
    
    def has_issue_category(self, category: IssueCategory) -> bool:
        """Check if review has specific issue category"""
        return self.issue_categories and category in self.issue_categories
    
    def set_public_response(self, response: str):
        """Set public response and update status"""
        self.public_response = response
        from datetime import datetime, timezone
        self.public_response_date = datetime.now(timezone.utc)
        self.status = ReviewStatus.RESPONDED
    
    def escalate(self, reason: str = None):
        """Escalate review for human attention"""
        self.status = ReviewStatus.ESCALATED
        if reason:
            if self.internal_notes:
                self.internal_notes += f"\n\nEscalated: {reason}"
            else:
                self.internal_notes = f"Escalated: {reason}"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "platform": self.platform.value,
            "external_id": self.external_id,
            "review_url": self.review_url,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "rating": self.rating,
            "title": self.title,
            "content": self.content,
            "sentiment_score": float(self.sentiment_score) if self.sentiment_score else None,
            "sentiment_label": self.sentiment_label,
            "urgency_level": self.urgency_level.value if self.urgency_level else None,
            "issue_categories": [cat.value for cat in self.issue_categories] if self.issue_categories else [],
            "status": self.status.value,
            "requires_private_recovery": self.requires_private_recovery,
            "public_response": self.public_response,
            "public_response_date": self.public_response_date.isoformat() if self.public_response_date else None,
            "internal_notes": self.internal_notes,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_positive": self.is_positive,
            "is_negative": self.is_negative,
            "is_neutral": self.is_neutral,
            "is_critical": self.is_critical,
            "days_since_posted": self.days_since_posted
        }
