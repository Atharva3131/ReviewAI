"""
Base schemas and validation utilities
"""

import re
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""

    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class UUIDMixin(BaseModel):
    """Mixin for UUID fields"""

    id: Optional[uuid.UUID] = Field(None, description="Unique identifier")


class OrganizationMixin(BaseModel):
    """Mixin for organization-scoped resources"""

    organization_id: uuid.UUID = Field(..., description="Organization identifier")


class PaginationParams(BaseModel):
    """Standard pagination parameters"""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    size: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.size


class SortParams(BaseModel):
    """Standard sorting parameters"""

    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field(
        "asc", pattern="^(asc|desc)$", description="Sort order"
    )


class FilterParams(BaseModel):
    """Base filter parameters"""

    search: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Search query"
    )
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")

    @model_validator(mode="after")
    def validate_date_range(self) -> "FilterParams":
        """Validate date range"""
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be before date_to")
        return self


class APIResponse(BaseModel):
    """Standard API response wrapper"""

    success: bool = Field(True, description="Request success status")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[Any] = Field(None, description="Response data")
    errors: Optional[List[str]] = Field(None, description="Error messages")
    meta: Optional[Dict[str, Any]] = Field(None, description="Response metadata")


class PaginatedResponse(APIResponse):
    """Paginated response wrapper"""

    data: List[Any] = Field([], description="Response data items")
    pagination: Dict[str, Any] = Field(..., description="Pagination metadata")

    @classmethod
    def create(cls, items: List[Any], total: int, page: int, size: int, **kwargs):
        """Create paginated response"""
        total_pages = (total + size - 1) // size  # Ceiling division

        return cls(
            data=items,
            pagination={
                "page": page,
                "size": size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            **kwargs,
        )


class ErrorResponse(BaseModel):
    """Standard error response"""

    success: bool = Field(False, description="Request success status")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )
    request_id: Optional[str] = Field(None, description="Request identifier")


class ValidationErrorDetail(BaseModel):
    """Validation error detail"""

    field: str = Field(..., description="Field name")
    message: str = Field(..., description="Error message")
    value: Optional[Any] = Field(None, description="Invalid value")


class ValidationErrorResponse(ErrorResponse):
    """Validation error response"""

    error: str = Field("Validation error", description="Error message")
    error_code: str = Field("VALIDATION_ERROR", description="Error code")
    validation_errors: List[ValidationErrorDetail] = Field(
        [], description="Validation errors"
    )


# Common field validators
class CommonValidators:
    """Common validation functions"""

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format"""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")
        return email.lower()

    @staticmethod
    def validate_phone(phone: str) -> str:
        """Validate phone number format"""
        # Remove all non-digit characters
        digits_only = re.sub(r"\D", "", phone)

        # Check if it's a valid length (10-15 digits)
        if not (10 <= len(digits_only) <= 15):
            raise ValueError("Phone number must be 10-15 digits")

        return phone

    @staticmethod
    def validate_password_strength(password: str) -> str:
        """Validate password strength"""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", password):
            raise ValueError("Password must contain at least one digit")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError("Password must contain at least one special character")

        return password

    @staticmethod
    def validate_rating(rating: int) -> int:
        """Validate rating value"""
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return rating

    @staticmethod
    def validate_sentiment_score(score: float) -> float:
        """Validate sentiment score"""
        if not (0.0 <= score <= 1.0):
            raise ValueError("Sentiment score must be between 0.0 and 1.0")
        return round(score, 2)

    @staticmethod
    def validate_probability_score(score: float) -> float:
        """Validate probability score"""
        if not (0.0 <= score <= 1.0):
            raise ValueError("Probability score must be between 0.0 and 1.0")
        return round(score, 3)


# Enums for common values
class StatusEnum(str, Enum):
    """Common status values"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PriorityEnum(str, Enum):
    """Priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UrgencyEnum(str, Enum):
    """Urgency levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PlatformEnum(str, Enum):
    """Review platforms"""

    GOOGLE = "google"
    YELP = "yelp"
    FACEBOOK = "facebook"
    TRUSTPILOT = "trustpilot"
    TRIPADVISOR = "tripadvisor"


class CategoryEnum(str, Enum):
    """Issue categories"""

    SUPPORT = "support"
    PRICING = "pricing"
    DELIVERY = "delivery"
    QUALITY = "quality"
    BILLING = "billing"
    TECHNICAL = "technical"
    OTHER = "other"


class ActionTypeEnum(str, Enum):
    """Recovery action types"""

    EMAIL = "email"
    SMS = "sms"
    PHONE_CALL = "phone_call"
    DISCOUNT = "discount"
    REFUND = "refund"
    ESCALATION = "escalation"
    FOLLOW_UP = "follow_up"


# Custom field types
class EmailStr(str):
    """Email string type with validation"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("string required")
        return CommonValidators.validate_email(v)


class PhoneStr(str):
    """Phone string type with validation"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("string required")
        return CommonValidators.validate_phone(v)


class PasswordStr(str):
    """Password string type with validation"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("string required")
        return CommonValidators.validate_password_strength(v)


# Alias for backward compatibility
BaseResponse = APIResponse
