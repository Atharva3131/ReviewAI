"""
Error response schemas for consistent API error formatting
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ErrorDetail(BaseModel):
    """Individual error detail"""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")
    input: Optional[Any] = Field(None, description="Input value that caused the error")


class ErrorResponse(BaseModel):
    """Standard error response format"""
    type: str = Field(..., description="Error type identifier")
    message: str = Field(..., description="Human-readable error message")
    status_code: int = Field(..., description="HTTP status code")
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: float = Field(..., description="Unix timestamp when error occurred")
    path: str = Field(..., description="API path where error occurred")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    validation_errors: Optional[List[ErrorDetail]] = Field(None, description="Validation error details")


class ErrorContainer(BaseModel):
    """Container for error response"""
    error: ErrorResponse


# Predefined error responses for OpenAPI documentation
class ValidationErrorResponse(BaseModel):
    """422 Validation Error Response"""
    error: ErrorResponse = Field(
        ...,
        example={
            "type": "validation_error",
            "message": "Request validation failed",
            "status_code": 422,
            "request_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": 1640995200.0,
            "path": "/api/v1/reviews",
            "details": None,
            "validation_errors": [
                {
                    "field": "rating",
                    "message": "ensure this value is greater than or equal to 1",
                    "type": "value_error.number.not_ge",
                    "input": 0
                }
            ]
        }
    )


class NotFoundErrorResponse(BaseModel):
    """404 Not Found Error Response"""
    error: ErrorResponse = Field(
        ...,
        example={
            "type": "resource_not_found",
            "message": "Requested resource not found",
            "status_code": 404,
            "request_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": 1640995200.0,
            "path": "/api/v1/reviews/123",
            "details": {"resource_type": "review", "resource_id": "123"}
        }
    )


class UnauthorizedErrorResponse(BaseModel):
    """401 Unauthorized Error Response"""
    error: ErrorResponse = Field(
        ...,
        example={
            "type": "authentication_error",
            "message": "Invalid or expired authentication token",
            "status_code": 401,
            "request_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": 1640995200.0,
            "path": "/api/v1/reviews",
            "details": None
        }
    )


class ForbiddenErrorResponse(BaseModel):
    """403 Forbidden Error Response"""
    error: ErrorResponse = Field(
        ...,
        example={
            "type": "authorization_error",
            "message": "Insufficient permissions to access this resource",
            "status_code": 403,
            "request_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": 1640995200.0,
            "path": "/api/v1/reviews",
            "details": {"required_permission": "reviews:read"}
        }
    )


class ConflictErrorResponse(BaseModel):
    """409 Conflict Error Response"""
    error: ErrorResponse = Field(
        ...,
        example={
            "type": "resource_exists",
            "message": "Resource already exists",
            "status_code": 409,
            "request_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": 1640995200.0,
            "path": "/api/v1/reviews",
            "details": {"existing_resource_id": "456"}
        }
    )


class RateLimitErrorResponse(BaseModel):
    """429 Too Many Requests Error Response"""
    error: ErrorResponse = Field(
        ...,
        example={
            "type": "rate_limit_exceeded",
            "message": "Rate limit exceeded",
            "status_code": 429,
            "request_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": 1640995200.0,
            "path": "/api/v1/reviews",
            "details": {"retry_after": 60, "limit": 100, "window": "1 minute"}
        }
    )


class InternalServerErrorResponse(BaseModel):
    """500 Internal Server Error Response"""
    error: ErrorResponse = Field(
        ...,
        example={
            "type": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "status_code": 500,
            "request_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": 1640995200.0,
            "path": "/api/v1/reviews",
            "details": None
        }
    )


class ServiceUnavailableErrorResponse(BaseModel):
    """503 Service Unavailable Error Response"""
    error: ErrorResponse = Field(
        ...,
        example={
            "type": "service_unavailable",
            "message": "Service temporarily unavailable. Please try again later.",
            "status_code": 503,
            "request_id": "123e4567-e89b-12d3-a456-426614174000",
            "timestamp": 1640995200.0,
            "path": "/api/v1/reviews",
            "details": {"service": "database", "estimated_recovery": "5 minutes"}
        }
    )


# Common error responses for OpenAPI documentation
COMMON_ERROR_RESPONSES = {
    400: {"model": ErrorContainer, "description": "Bad Request"},
    401: {"model": UnauthorizedErrorResponse, "description": "Unauthorized"},
    403: {"model": ForbiddenErrorResponse, "description": "Forbidden"},
    404: {"model": NotFoundErrorResponse, "description": "Not Found"},
    409: {"model": ConflictErrorResponse, "description": "Conflict"},
    422: {"model": ValidationErrorResponse, "description": "Validation Error"},
    429: {"model": RateLimitErrorResponse, "description": "Too Many Requests"},
    500: {"model": InternalServerErrorResponse, "description": "Internal Server Error"},
    503: {"model": ServiceUnavailableErrorResponse, "description": "Service Unavailable"},
}
