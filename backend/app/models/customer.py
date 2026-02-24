"""Customer model for tracking customer relationships"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, DECIMAL, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import Base


class Customer(Base):
    """Customer model for tracking customer relationships and risk"""
    
    __tablename__ = "customers"
    
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
    
    # Customer identification
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    name = Column(String(255), nullable=True, index=True)
    external_id = Column(String(255), nullable=True, index=True)  # CRM system ID
    
    # Risk assessment
    churn_risk_score = Column(DECIMAL(3, 2), nullable=True, index=True)  # 0.00 to 1.00
    bad_review_likelihood = Column(DECIMAL(3, 2), nullable=True, index=True)  # 0.00 to 1.00
    
    # Interaction tracking
    last_interaction = Column(DateTime(timezone=True), nullable=True, index=True)
    interaction_count = Column(Integer, default=0, nullable=False)
    
    # Customer context
    context_summary = Column(Text, nullable=True)  # AI-generated summary
    tags = Column(Text, nullable=True)  # Comma-separated tags
    
    # Customer value metrics
    lifetime_value = Column(DECIMAL(10, 2), nullable=True)
    total_orders = Column(Integer, default=0, nullable=False)
    avg_order_value = Column(DECIMAL(10, 2), nullable=True)
    
    # Satisfaction metrics
    avg_rating_given = Column(DECIMAL(3, 2), nullable=True)  # Average rating they give
    total_reviews = Column(Integer, default=0, nullable=False)
    positive_reviews = Column(Integer, default=0, nullable=False)
    negative_reviews = Column(Integer, default=0, nullable=False)
    
    # Communication preferences
    preferred_contact_method = Column(String(50), nullable=True)  # email, phone, sms
    timezone = Column(String(50), nullable=True)
    language = Column(String(10), default="en", nullable=False)
    
    # Status tracking
    status = Column(String(50), default="active", nullable=False, index=True)  # active, churned, recovered
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="customers")
    reviews = relationship("Review", back_populates="customer")
    support_tickets = relationship("SupportTicket", back_populates="customer")
    recovery_actions = relationship("RecoveryAction", back_populates="customer")
    
    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.name}', email='{self.email}')>"
    
    @property
    def display_name(self) -> str:
        """Get display name for customer"""
        if self.name:
            return self.name
        elif self.email:
            return self.email.split("@")[0]
        elif self.phone:
            return f"Customer {self.phone}"
        else:
            return f"Customer {str(self.id)[:8]}"
    
    @property
    def risk_level(self) -> str:
        """Get human-readable risk level"""
        if self.churn_risk_score is None:
            return "Unknown"
        
        score = float(self.churn_risk_score)
        if score >= 0.8:
            return "Critical"
        elif score >= 0.6:
            return "High"
        elif score >= 0.4:
            return "Medium"
        elif score >= 0.2:
            return "Low"
        else:
            return "Very Low"
    
    @property
    def review_likelihood_level(self) -> str:
        """Get human-readable bad review likelihood level"""
        if self.bad_review_likelihood is None:
            return "Unknown"
        
        score = float(self.bad_review_likelihood)
        if score >= 0.8:
            return "Very High"
        elif score >= 0.6:
            return "High"
        elif score >= 0.4:
            return "Medium"
        elif score >= 0.2:
            return "Low"
        else:
            return "Very Low"
    
    @property
    def satisfaction_score(self) -> Optional[float]:
        """Calculate satisfaction score based on reviews"""
        if self.total_reviews == 0:
            return None
        
        return self.positive_reviews / self.total_reviews
    
    @property
    def days_since_last_interaction(self) -> Optional[int]:
        """Get days since last interaction"""
        if not self.last_interaction:
            return None
        
        delta = datetime.now(timezone.utc) - self.last_interaction
        return delta.days
    
    @property
    def is_at_risk(self) -> bool:
        """Check if customer is at risk"""
        return (
            self.churn_risk_score and 
            float(self.churn_risk_score) >= 0.6
        )
    
    @property
    def is_high_value(self) -> bool:
        """Check if customer is high value"""
        return (
            self.lifetime_value and 
            float(self.lifetime_value) >= 1000  # Configurable threshold
        )
    
    def update_interaction(self):
        """Update last interaction timestamp and count"""
        self.last_interaction = datetime.now(timezone.utc)
        self.interaction_count += 1
    
    def update_risk_scores(self, churn_risk: float, review_risk: float):
        """Update risk scores"""
        self.churn_risk_score = min(max(churn_risk, 0.0), 1.0)  # Clamp to 0-1
        self.bad_review_likelihood = min(max(review_risk, 0.0), 1.0)
    
    def add_review_stats(self, rating: int):
        """Update review statistics"""
        self.total_reviews += 1
        
        if rating >= 4:
            self.positive_reviews += 1
        elif rating <= 2:
            self.negative_reviews += 1
        
        # Update average rating
        if self.avg_rating_given is None:
            self.avg_rating_given = rating
        else:
            # Calculate new average
            total_rating = float(self.avg_rating_given) * (self.total_reviews - 1) + rating
            self.avg_rating_given = total_rating / self.total_reviews
    
    def add_tag(self, tag: str):
        """Add tag to customer"""
        if not self.tags:
            self.tags = tag
        else:
            tags = self.tags.split(",")
            if tag not in tags:
                tags.append(tag)
                self.tags = ",".join(tags)
    
    def remove_tag(self, tag: str):
        """Remove tag from customer"""
        if self.tags:
            tags = [t.strip() for t in self.tags.split(",")]
            if tag in tags:
                tags.remove(tag)
                self.tags = ",".join(tags) if tags else None
    
    def get_tags(self) -> List[str]:
        """Get list of tags"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",")]
    
    def update_context_summary(self, summary: str):
        """Update AI-generated context summary"""
        self.context_summary = summary
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "email": self.email,
            "phone": self.phone,
            "name": self.name,
            "display_name": self.display_name,
            "external_id": self.external_id,
            "churn_risk_score": float(self.churn_risk_score) if self.churn_risk_score else None,
            "bad_review_likelihood": float(self.bad_review_likelihood) if self.bad_review_likelihood else None,
            "risk_level": self.risk_level,
            "review_likelihood_level": self.review_likelihood_level,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "interaction_count": self.interaction_count,
            "context_summary": self.context_summary,
            "tags": self.get_tags(),
            "lifetime_value": float(self.lifetime_value) if self.lifetime_value else None,
            "total_orders": self.total_orders,
            "avg_order_value": float(self.avg_order_value) if self.avg_order_value else None,
            "avg_rating_given": float(self.avg_rating_given) if self.avg_rating_given else None,
            "total_reviews": self.total_reviews,
            "positive_reviews": self.positive_reviews,
            "negative_reviews": self.negative_reviews,
            "satisfaction_score": self.satisfaction_score,
            "preferred_contact_method": self.preferred_contact_method,
            "timezone": self.timezone,
            "language": self.language,
            "status": self.status,
            "days_since_last_interaction": self.days_since_last_interaction,
            "is_at_risk": self.is_at_risk,
            "is_high_value": self.is_high_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
