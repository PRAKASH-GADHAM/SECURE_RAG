"""Core exception classes.

Provides custom exceptions for the application with proper HTTP status codes.
"""

from typing import Any, Optional


class AppException(Exception):
    """Base application exception.

    Attributes:
        status_code: HTTP status code.
        detail: Error detail message.
        error_code: Application-specific error code.
    """

    def __init__(
        self,
        status_code: int = 500,
        detail: str = "Internal server error",
        error_code: str = "INTERNAL_ERROR",
        headers: Optional[dict[str, str]] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        self.headers = headers
        super().__init__(self.detail)


class NotFoundException(AppException):
    """Resource not found."""

    def __init__(self, resource: str = "Resource", resource_id: Any = None):
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} with id '{resource_id}' not found"
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="NOT_FOUND",
        )


class UnauthorizedException(AppException):
    """Authentication required or failed."""

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=401,
            detail=detail,
            error_code="UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(AppException):
    """Insufficient permissions."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=403,
            detail=detail,
            error_code="FORBIDDEN",
        )


class BadRequestException(AppException):
    """Invalid request data."""

    def __init__(self, detail: str = "Bad request"):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="BAD_REQUEST",
        )


class ConflictException(AppException):
    """Resource already exists."""

    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(
            status_code=409,
            detail=detail,
            error_code="CONFLICT",
        )


class RateLimitException(AppException):
    """Rate limit exceeded."""

    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=429,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED",
            headers={"Retry-After": "60"},
        )


class FileUploadException(AppException):
    """File upload error."""

    def __init__(self, detail: str = "File upload failed"):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="FILE_UPLOAD_ERROR",
        )


class SecurityException(AppException):
    """Security violation detected."""

    def __init__(self, detail: str = "Security violation detected"):
        super().__init__(
            status_code=403,
            detail=detail,
            error_code="SECURITY_VIOLATION",
        )


class ValidationException(AppException):
    """Validation error."""

    def __init__(self, detail: str = "Validation error"):
        super().__init__(
            status_code=422,
            detail=detail,
            error_code="VALIDATION_ERROR",
        )


class ExternalServiceException(AppException):
    """External service error (LLM, embeddings, etc.)."""

    def __init__(self, service: str = "External service", detail: str = "Service unavailable"):
        super().__init__(
            status_code=503,
            detail=f"{service}: {detail}",
            error_code="EXTERNAL_SERVICE_ERROR",
        )
