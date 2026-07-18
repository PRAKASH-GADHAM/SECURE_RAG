"""Common schemas used across the application.

Defines shared response models, pagination, and error schemas.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Error detail with code and message."""

    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: ErrorDetail


class SuccessResponse(BaseModel):
    """Standard success response schema."""

    success: bool = True
    message: str
    data: Optional[Any] = None


class PaginatedResponse(BaseModel):
    """Paginated response schema."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str
    services: dict[str, str]


class AuditLogResponse(BaseModel):
    """Audit log response schema."""

    id: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    status: str
    ip_address: Optional[str] = None
    risk_level: str
    details: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class APIUsageResponse(BaseModel):
    """API usage response schema."""

    total_requests: int
    total_tokens: int
    average_latency_ms: float
    period: str
