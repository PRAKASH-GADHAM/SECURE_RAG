"""Authentication service.

Handles user registration, login, token refresh, logout, password management,
and session tracking.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserProfile,
)
from app.services.audit import AuditService
from app.services.session import SessionService
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# In-memory password reset tokens (would use Redis in production)
_password_reset_tokens: dict[str, dict] = {}


class AuthService:
    """Service for authentication operations.

    Handles user lifecycle including registration, login, session management,
    token management, and password operations.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the auth service.

        Args:
            db: Async database session.
        """
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit_service = AuditService(db)
        self.session_service = SessionService(db)

    async def register(self, data: RegisterRequest) -> UserResponse:
        """Register a new user.

        Args:
            data: Registration data.

        Returns:
            Created user response.

        Raises:
            ConflictException: If email or username already exists.
            BadRequestException: If password is too weak.
        """
        # Check for existing email
        if await self.user_repo.email_exists(data.email):
            raise ConflictException("Email already registered")

        # Check for existing username
        if await self.user_repo.username_exists(data.username):
            raise ConflictException("Username already taken")

        # Validate password strength
        if len(data.password) < 8:
            raise BadRequestException("Password must be at least 8 characters")

        # Create user
        user = User(
            email=data.email.lower(),
            username=data.username.lower(),
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role="user",
            is_active=True,
            is_verified=False,
        )

        user = await self.user_repo.create(user)

        # Audit log
        await self.audit_service.log_auth_event(
            action="user.register",
            user_id=user.id,
            status="success",
        )

        logger.info(f"New user registered: {user.email}")

        return UserResponse.model_validate(user)

    async def login(
        self,
        data: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        """Authenticate a user and return tokens.

        Creates a session and records the login event.

        Args:
            data: Login credentials.
            ip_address: Client IP address.
            user_agent: Client user agent.

        Returns:
            Token response with access and refresh tokens.

        Raises:
            UnauthorizedException: If credentials are invalid.
        """
        user = await self.user_repo.get_by_email(data.email.lower())

        if user is None:
            await self.audit_service.log_auth_event(
                action="user.login",
                status="failure",
                ip_address=ip_address,
                user_agent=user_agent,
                details=f"Failed login for non-existent email: {data.email}",
            )
            raise UnauthorizedException("Invalid email or password")

        if not verify_password(data.password, user.hashed_password):
            await self.audit_service.log_auth_event(
                action="user.login",
                user_id=user.id,
                status="failure",
                ip_address=ip_address,
                user_agent=user_agent,
                details="Invalid password",
            )
            logger.warning(f"Failed login attempt for: {data.email}")
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            await self.audit_service.log_auth_event(
                action="user.login",
                user_id=user.id,
                status="failure",
                ip_address=ip_address,
                details="Account deactivated",
            )
            raise UnauthorizedException("Account is deactivated")

        # Generate tokens
        tokens = create_token_pair(user_id=user.id, role=user.role)

        # Create session
        await self.session_service.create_session(
            user_id=user.id,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Audit log
        await self.audit_service.log_auth_event(
            action="user.login",
            user_id=user.id,
            status="success",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info(f"User logged in: {user.email}")

        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(
        self,
        user_id: str,
        access_token: Optional[str] = None,
        all_devices: bool = False,
        ip_address: Optional[str] = None,
    ) -> None:
        """Logout a user by invalidating their session(s).

        Args:
            user_id: User ID.
            access_token: Current access token to invalidate.
            all_devices: If True, invalidate all user sessions.
            ip_address: Client IP for audit logging.
        """
        if all_devices:
            count = await self.session_service.invalidate_all_user(user_id)
            logger.info(f"User {user_id} logged out from all devices ({count} sessions)")
        elif access_token:
            await self.session_service.session_repo.deactivate_by_token(access_token)

        # Audit log
        await self.audit_service.log_auth_event(
            action="user.logout",
            user_id=user_id,
            status="success",
            ip_address=ip_address,
            details=f"All devices: {all_devices}",
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh an access token using a refresh token.

        Args:
            refresh_token: JWT refresh token.

        Returns:
            New token pair.

        Raises:
            UnauthorizedException: If refresh token is invalid or expired.
        """
        payload = decode_token(refresh_token)

        if payload is None:
            raise UnauthorizedException("Invalid or expired refresh token")

        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")

        user_id = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException("Invalid token payload")

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UnauthorizedException("User not found")

        if not user.is_active:
            raise UnauthorizedException("Account is deactivated")

        # Generate new tokens
        tokens = create_token_pair(user_id=user.id, role=user.role)

        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def get_current_user(self, user_id: str) -> UserResponse:
        """Get current user profile.

        Args:
            user_id: User ID.

        Returns:
            User response.

        Raises:
            UnauthorizedException: If user not found.
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UnauthorizedException("User not found")

        return UserResponse.model_validate(user)

    async def update_profile(
        self, user_id: str, data: UserProfile
    ) -> UserResponse:
        """Update user profile.

        Args:
            user_id: User ID.
            data: Profile update data.

        Returns:
            Updated user response.

        Raises:
            ConflictException: If username is taken.
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UnauthorizedException("User not found")

        if data.username and data.username.lower() != user.username:
            if await self.user_repo.username_exists(data.username.lower()):
                raise ConflictException("Username already taken")
            user.username = data.username.lower()

        if data.full_name is not None:
            user.full_name = data.full_name

        user = await self.user_repo.update(user)

        await self.audit_service.log_auth_event(
            action="user.profile_updated",
            user_id=user_id,
            status="success",
        )

        return UserResponse.model_validate(user)

    async def change_password(
        self, user_id: str, data: ChangePasswordRequest
    ) -> None:
        """Change user password.

        Invalidates all other sessions after password change.

        Args:
            user_id: User ID.
            data: Password change data.

        Raises:
            UnauthorizedException: If current password is wrong.
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UnauthorizedException("User not found")

        if not verify_password(data.current_password, user.hashed_password):
            await self.audit_service.log_auth_event(
                action="user.password_change",
                user_id=user_id,
                status="failure",
                details="Invalid current password",
            )
            raise UnauthorizedException("Current password is incorrect")

        user.hashed_password = hash_password(data.new_password)
        await self.user_repo.update(user)

        # Invalidate all sessions after password change
        await self.session_service.invalidate_all_user(user_id)

        await self.audit_service.log_auth_event(
            action="user.password_change",
            user_id=user_id,
            status="success",
        )

        logger.info(f"Password changed for user: {user.email}")

    async def request_password_reset(
        self, data: PasswordResetRequest, ip_address: Optional[str] = None
    ) -> dict:
        """Request a password reset token.

        Always returns success to prevent email enumeration.

        Args:
            data: Password reset request.
            ip_address: Client IP.

        Returns:
            Success message (always, regardless of email existence).
        """
        user = await self.user_repo.get_by_email(data.email.lower())

        if user is not None:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

            _password_reset_tokens[token_hash] = {
                "user_id": user.id,
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            }

            await self.audit_service.log_auth_event(
                action="user.password_reset_requested",
                user_id=user.id,
                status="success",
                ip_address=ip_address,
                details="Reset token generated",
            )

            logger.info(f"Password reset requested for: {data.email}")

        # Always return success to prevent email enumeration
        return {
            "message": "If the email exists, a reset link has been sent",
            "success": True,
        }

    async def confirm_password_reset(
        self, token: str, new_password: str
    ) -> None:
        """Confirm a password reset with the token.

        Args:
            token: Reset token.
            new_password: New password.

        Raises:
            BadRequestException: If token is invalid or expired.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        reset_data = _password_reset_tokens.get(token_hash)

        if reset_data is None:
            raise BadRequestException("Invalid or expired reset token")

        if reset_data["expires_at"] < datetime.now(timezone.utc):
            del _password_reset_tokens[token_hash]
            raise BadRequestException("Reset token has expired")

        user = await self.user_repo.get_by_id(reset_data["user_id"])
        if user is None:
            raise BadRequestException("User not found")

        # Update password
        user.hashed_password = hash_password(new_password)
        await self.user_repo.update(user)

        # Invalidate all sessions
        await self.session_service.invalidate_all_user(user.id)

        # Clean up token
        del _password_reset_tokens[token_hash]

        await self.audit_service.log_auth_event(
            action="user.password_reset_completed",
            user_id=user.id,
            status="success",
        )

        logger.info(f"Password reset completed for user: {user.email}")

    async def get_user_sessions(self, user_id: str) -> list:
        """Get all active sessions for a user.

        Args:
            user_id: User ID.

        Returns:
            List of session responses.
        """
        return await self.session_service.get_user_sessions(user_id)

    async def revoke_session(
        self, user_id: str, session_id: str
    ) -> bool:
        """Revoke a specific session.

        Args:
            user_id: User ID.
            session_id: Session ID.

        Returns:
            True if revoked.
        """
        return await self.session_service.invalidate_session(session_id, user_id)
