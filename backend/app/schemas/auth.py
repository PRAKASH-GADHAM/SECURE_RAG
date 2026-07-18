"""Authentication schemas for API request/response validation.

Defines Pydantic models for login, registration, token refresh, and password reset.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """User registration request schema."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(
        ..., min_length=3, max_length=50, description="Unique username"
    )
    password: str = Field(
        ..., min_length=8, max_length=128, description="User password"
    )
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username contains only allowed characters."""
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        return v.lower()


class LoginRequest(BaseModel):
    """User login request schema."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class RefreshTokenRequest(BaseModel):
    """Token refresh request schema."""

    refresh_token: str = Field(..., description="JWT refresh token")


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""

    email: EmailStr = Field(..., description="Email for password reset")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New password"
    )


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New password"
    )


class UserResponse(BaseModel):
    """User response schema."""

    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfile(BaseModel):
    """User profile update schema."""

    full_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=50)


# ===========================================
# Session Schemas
# ===========================================


class SessionResponse(BaseModel):
    """Session response schema."""

    id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    """Session list response schema."""

    sessions: list[SessionResponse]
    total: int


# ===========================================
# API Key Schemas
# ===========================================


class APIKeyCreateRequest(BaseModel):
    """API key creation request schema."""

    name: str = Field(..., min_length=1, max_length=255, description="API key name")
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime")


class APIKeyResponse(BaseModel):
    """API key response schema (without raw key)."""

    id: str
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class APIKeyCreatedResponse(BaseModel):
    """API key creation response (includes raw key shown once)."""

    id: str
    name: str
    key: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    message: str


class APIKeyListResponse(BaseModel):
    """API key list response schema."""

    api_keys: list[APIKeyResponse]
    total: int


# ===========================================
# Audit Log Schemas
# ===========================================


class AuditLogEntry(BaseModel):
    """Individual audit log entry."""

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


class AuditLogListResponse(BaseModel):
    """Audit log list response schema."""

    logs: list[AuditLogEntry]
    total: int


# ===========================================
# Logout Schema
# ===========================================


class LogoutRequest(BaseModel):
    """Logout request schema."""

    all_devices: bool = Field(default=False, description="Invalidate all sessions across devices")
