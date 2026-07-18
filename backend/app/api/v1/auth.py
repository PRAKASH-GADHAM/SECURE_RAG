"""Authentication API endpoints.

Handles user registration, login, token refresh, logout, profile management,
password reset, and session management.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_active_user, get_current_user
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    SessionListResponse,
    TokenResponse,
    UserResponse,
    UserProfile,
)
from app.schemas.common import SuccessResponse
from app.services.auth import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user account.

    Args:
        data: Registration data.
        db: Database session.

    Returns:
        Created user profile.
    """
    service = AuthService(db)
    return await service.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Authenticate a user and return JWT tokens.

    Creates a session and logs the authentication event.

    Args:
        data: Login credentials.
        request: HTTP request for IP/user-agent.
        db: Database session.

    Returns:
        JWT access and refresh tokens.
    """
    service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await service.login(data, ip_address=ip_address, user_agent=user_agent)


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    data: LogoutRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Logout the current user.

    Optionally invalidates all sessions across devices.

    Args:
        data: Logout options.
        request: HTTP request for IP.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Success confirmation.
    """
    service = AuthService(db)
    ip_address = request.client.host if request.client else None
    authorization = request.headers.get("authorization", "")
    access_token = authorization.split(" ", 1)[1] if authorization.startswith("Bearer ") else None

    await service.logout(
        user_id=current_user.id,
        access_token=access_token,
        all_devices=data.all_devices,
        ip_address=ip_address,
    )
    return SuccessResponse(message="Logged out successfully")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Refresh an access token using a refresh token.

    Args:
        data: Refresh token request.
        db: Database session.

    Returns:
        New token pair.
    """
    service = AuthService(db)
    return await service.refresh_token(data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """Get the current authenticated user's profile.

    Args:
        current_user: Authenticated user.

    Returns:
        User profile.
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    data: UserProfile,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update the current user's profile.

    Args:
        data: Profile update data.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Updated user profile.
    """
    service = AuthService(db)
    return await service.update_profile(current_user.id, data)


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Change the current user's password.

    Invalidates all other sessions after successful change.

    Args:
        data: Password change data.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Success message.
    """
    service = AuthService(db)
    await service.change_password(current_user.id, data)
    return SuccessResponse(message="Password changed successfully. All other sessions have been invalidated.")


@router.post("/password-reset/request", response_model=SuccessResponse)
async def request_password_reset(
    data: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Request a password reset token.

    Always returns success to prevent email enumeration.

    Args:
        data: Password reset request with email.
        request: HTTP request for IP.
        db: Database session.

    Returns:
        Success message (always).
    """
    service = AuthService(db)
    ip_address = request.client.host if request.client else None
    result = await service.request_password_reset(data, ip_address=ip_address)
    return SuccessResponse(**result)


@router.post("/password-reset/confirm", response_model=SuccessResponse)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db_session),
):
    """Confirm a password reset with the token.

    Args:
        data: Reset token and new password.
        db: Database session.

    Returns:
        Success message.
    """
    service = AuthService(db)
    await service.confirm_password_reset(data.token, data.new_password)
    return SuccessResponse(message="Password reset successfully")


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List all active sessions for the current user.

    Args:
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of active sessions.
    """
    service = AuthService(db)
    sessions = await service.get_user_sessions(current_user.id)
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Revoke a specific session.

    Args:
        session_id: Session ID to revoke.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Success confirmation.
    """
    service = AuthService(db)
    result = await service.revoke_session(current_user.id, session_id)
    if not result:
        raise NotFoundException("Session", session_id)
    return SuccessResponse(message="Session revoked successfully")
