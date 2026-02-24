"""
Authentication schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class UserRegistration(BaseModel):
    """User registration request schema"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    organization_name: str = Field(..., min_length=2, max_length=255)
    organization_domain: Optional[str] = Field(None, max_length=255)
    
    @field_validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        from app.core.security import SecurityService
        validation = SecurityService.validate_password_strength(v)
        if not validation["is_valid"]:
            raise ValueError("Password does not meet security requirements")
        return v
    
    @field_validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        return v.lower()


class UserLogin(BaseModel):
    """User login request schema"""
    email: EmailStr
    password: str
    remember_me: bool = False
    
    @field_validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        return v.lower()


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserResponse"
    organization: "OrganizationResponse"


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request schema"""
    email: EmailStr
    
    @field_validator('email')
    def validate_email(cls, v):
        return v.lower()


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    def validate_password(cls, v):
        from app.core.security import SecurityService
        validation = SecurityService.validate_password_strength(v)
        if not validation["is_valid"]:
            raise ValueError("Password does not meet security requirements")
        return v


class PasswordChange(BaseModel):
    """Password change schema"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    def validate_password(cls, v):
        from app.core.security import SecurityService
        validation = SecurityService.validate_password_strength(v)
        if not validation["is_valid"]:
            raise ValueError("Password does not meet security requirements")
        return v


class EmailVerificationRequest(BaseModel):
    """Email verification request schema"""
    token: str


class UserResponse(BaseModel):
    """User response schema"""
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    onboarding_completed: bool = False
    onboarding_data: Optional[dict] = None
    last_login: Optional[datetime]
    created_at: datetime
    
    @field_validator('id', mode='before')
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string"""
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    """Organization response schema"""
    id: str
    name: str
    domain: Optional[str]
    created_at: datetime
    
    @field_validator('id', mode='before')
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string"""
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True


class AuthStatus(BaseModel):
    """Authentication status response"""
    is_authenticated: bool
    user: Optional[UserResponse] = None
    organization: Optional[OrganizationResponse] = None
    permissions: list[str] = []


# Update forward references
TokenResponse.model_rebuild()
AuthStatus.model_rebuild()
