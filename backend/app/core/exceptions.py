"""
Custom exception classes for Revive AI
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class ReviveAIException(Exception):
    """Base exception class for Revive AI"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class BusinessLogicError(ReviveAIException):
    """Exception for business logic violations"""

    pass


class ResourceNotFoundError(ReviveAIException):
    """Exception for when a requested resource is not found"""

    pass


class ResourceExistsError(ReviveAIException):
    """Exception for when a resource already exists"""

    pass


class ValidationError(ReviveAIException):
    """Exception for validation errors"""

    pass


class AuthenticationError(ReviveAIException):
    """Exception for authentication failures"""

    pass


class AuthorizationError(ReviveAIException):
    """Exception for authorization failures"""

    pass


class ExternalServiceError(ReviveAIException):
    """Exception for external service failures"""

    pass


class DatabaseError(ReviveAIException):
    """Exception for database operation failures"""

    pass


class RateLimitError(ReviveAIException):
    """Exception for rate limit violations"""

    pass


class ConfigurationError(ReviveAIException):
    """Exception for configuration issues"""

    pass


# HTTP Exception classes that map to specific status codes
class BadRequestHTTPException(HTTPException):
    """400 Bad Request"""

    def __init__(
        self, detail: str = "Bad request", headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail, headers=headers
        )


class UnauthorizedHTTPException(HTTPException):
    """401 Unauthorized"""

    def __init__(
        self, detail: str = "Unauthorized", headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=headers
        )


class ForbiddenHTTPException(HTTPException):
    """403 Forbidden"""

    def __init__(
        self, detail: str = "Forbidden", headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, detail=detail, headers=headers
        )


class NotFoundHTTPException(HTTPException):
    """404 Not Found"""

    def __init__(
        self, detail: str = "Not found", headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, detail=detail, headers=headers
        )


class ConflictHTTPException(HTTPException):
    """409 Conflict"""

    def __init__(
        self, detail: str = "Conflict", headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT, detail=detail, headers=headers
        )


class UnprocessableEntityHTTPException(HTTPException):
    """422 Unprocessable Entity"""

    def __init__(
        self,
        detail: str = "Unprocessable entity",
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            headers=headers,
        )


class TooManyRequestsHTTPException(HTTPException):
    """429 Too Many Requests"""

    def __init__(
        self,
        detail: str = "Too many requests",
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
        )


class InternalServerErrorHTTPException(HTTPException):
    """500 Internal Server Error"""

    def __init__(
        self,
        detail: str = "Internal server error",
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            headers=headers,
        )


class ServiceUnavailableHTTPException(HTTPException):
    """503 Service Unavailable"""

    def __init__(
        self,
        detail: str = "Service unavailable",
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            headers=headers,
        )


# Exception mapping for converting custom exceptions to HTTP exceptions
EXCEPTION_MAPPING = {
    ResourceNotFoundError: NotFoundHTTPException,
    ResourceExistsError: ConflictHTTPException,
    ValidationError: UnprocessableEntityHTTPException,
    AuthenticationError: UnauthorizedHTTPException,
    AuthorizationError: ForbiddenHTTPException,
    ExternalServiceError: ServiceUnavailableHTTPException,
    DatabaseError: InternalServerErrorHTTPException,
    RateLimitError: TooManyRequestsHTTPException,
    BusinessLogicError: BadRequestHTTPException,
    ConfigurationError: InternalServerErrorHTTPException,
}


def convert_exception_to_http(exc: ReviveAIException) -> HTTPException:
    """Convert a custom exception to an HTTP exception"""
    http_exception_class = EXCEPTION_MAPPING.get(
        type(exc), InternalServerErrorHTTPException
    )
    return http_exception_class(detail=exc.message)


# Aliases for backward compatibility
NotFoundError = ResourceNotFoundError
NotFoundException = ResourceNotFoundError
ValidationException = ValidationError
