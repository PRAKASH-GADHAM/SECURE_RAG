"""Dependency injection for the application.

Provides FastAPI dependencies for authentication (JWT + API key),
database sessions, and services.
"""

from typing import Optional

from fastapi import Depends, Header, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.security import decode_token
from app.database import get_db_session
from app.models.user import User
from app.repositories.api_key import APIKeyRepository

settings = get_settings()

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Get the current authenticated user from the JWT token.

    Supports both Bearer token and API key authentication.

    Args:
        authorization: The Authorization header value.
        db: Database session.

    Returns:
        The authenticated User instance.

    Raises:
        UnauthorizedException: If token is missing or invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException("Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)

    if payload is None:
        raise UnauthorizedException("Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedException("Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedException("User not found")

    if not user.is_active:
        raise UnauthorizedException("User account is deactivated")

    return user


async def get_current_user_by_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """Authenticate user via API key.

    Returns None if no API key is provided (allows optional API key auth).
    Used for endpoints that support both JWT and API key authentication.

    Args:
        api_key: The X-API-Key header value.
        db: Database session.

    Returns:
        The authenticated User instance or None.
    """
    if api_key is None:
        return None

    api_key_repo = APIKeyRepository(db)
    key_hash = APIKeyRepository.hash_key(api_key)
    api_key_record = await api_key_repo.get_by_key_hash(key_hash)

    if api_key_record is None:
        raise UnauthorizedException("Invalid API key")

    # Check expiration
    from datetime import datetime, timezone as tz
    if api_key_record.expires_at and api_key_record.expires_at < datetime.now(tz.utc):
        raise UnauthorizedException("API key has expired")

    if not api_key_record.is_active:
        raise UnauthorizedException("API key has been revoked")

    # Get user
    result = await db.execute(select(User).where(User.id == api_key_record.user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise UnauthorizedException("User not found or deactivated")

    # Update last used (non-blocking)
    api_key_record.last_used_at = datetime.now(tz.utc)
    await db.flush()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get the current active user.

    Args:
        current_user: The authenticated user.

    Returns:
        The active User instance.

    Raises:
        UnauthorizedException: If user is not active.
    """
    if not current_user.is_active:
        raise UnauthorizedException("User account is deactivated")
    return current_user


def require_role(*allowed_roles: str):
    """Dependency factory that requires the user to have one of the specified roles.

    Args:
        *allowed_roles: Allowed role names.

    Returns:
        A dependency function that checks user role.
    """

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenException(
                f"Required role: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that requires admin role.

    Args:
        current_user: The authenticated user.

    Returns:
        The admin User instance.

    Raises:
        ForbiddenException: If user is not an admin.
    """
    if current_user.role != "admin":
        raise ForbiddenException("Admin access required")
    return current_user
