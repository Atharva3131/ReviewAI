"""User model with authentication support"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from passlib.context import CryptContext
import uuid
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """User model with authentication and authorization"""
    
    __tablename__ = "users"
    
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
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    
    # User profile
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    onboarding_data = Column(JSON, nullable=True)
    
    # Authentication tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
    
    @property
    def full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email.split("@")[0]
    
    @property
    def is_admin(self):
        """Check if user is admin"""
        return self.role == UserRole.ADMIN
    
    @property
    def is_manager(self):
        """Check if user is manager or admin"""
        return self.role in [UserRole.ADMIN, UserRole.MANAGER]
    
    @property
    def is_locked(self):
        """Check if account is locked"""
        if self.locked_until is None:
            return False
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) < self.locked_until
    
    def set_password(self, password: str):
        """Hash and set password"""
        self.password_hash = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(password, self.password_hash)
    
    def increment_failed_login(self):
        """Increment failed login attempts"""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts for 30 minutes
        if self.failed_login_attempts >= 5:
            from datetime import datetime, timezone, timedelta
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    def reset_failed_login(self):
        """Reset failed login attempts"""
        self.failed_login_attempts = 0
        self.locked_until = None
        from datetime import datetime, timezone
        self.last_login = datetime.now(timezone.utc)
    
    def can_access_organization(self, org_id: str) -> bool:
        """Check if user can access specific organization"""
        return str(self.organization_id) == str(org_id)
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary"""
        data = {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "email": self.email,
            "role": self.role.value,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_locked": self.is_locked,
            "onboarding_completed": self.onboarding_completed,
            "onboarding_data": self.onboarding_data,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            data.update({
                "failed_login_attempts": self.failed_login_attempts,
                "locked_until": self.locked_until.isoformat() if self.locked_until else None
            })
        
        return data
