"""Session management service.

Handles session creation, tracking, and invalidation.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import Session
from app.repositories.session import SessionRepository
from app.schemas.auth import SessionResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SessionService:
    """Service for session lifecycle management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_repo = SessionRepository(db)

    async def create_session(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Session:
        """Create a new session on login.

        Args:
            user_id: User ID.
            access_token: JWT access token.
            refresh_token: JWT refresh token.
            ip_address: Client IP.
            user_agent: Client user agent.

        Returns:
            Created Session instance.
        """
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

        session = Session(
            user_id=user_id,
            token=access_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
            expires_at=expires_at,
        )

        session = await self.session_repo.create(session)
        logger.info(f"Session created for user {user_id}")
        return session

    async def get_user_sessions(self, user_id: str) -> List[SessionResponse]:
        """Get all active sessions for a user.

        Args:
            user_id: User ID.

        Returns:
            List of session responses.
        """
        sessions = await self.session_repo.get_active_by_user(user_id)
        return [
            SessionResponse(
                id=s.id,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                is_active=s.is_active,
                created_at=s.created_at,
                expires_at=s.expires_at,
            )
            for s in sessions
        ]

    async def invalidate_session(self, session_id: str, user_id: str) -> bool:
        """Invalidate a specific session.

        Args:
            session_id: Session ID.
            user_id: User ID (for ownership check).

        Returns:
            True if invalidated.
        """
        session = await self.session_repo.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            return False

        result = await self.session_repo.deactivate(session_id)
        if result:
            logger.info(f"Session {session_id} invalidated for user {user_id}")
        return result

    async def invalidate_all_user(self, user_id: str) -> int:
        """Invalidate all sessions for a user (e.g., on password change).

        Args:
            user_id: User ID.

        Returns:
            Number of sessions invalidated.
        """
        count = await self.session_repo.deactivate_all_user(user_id)
        logger.info(f"All sessions invalidated for user {user_id}: {count} sessions")
        return count

    async def cleanup_expired(self) -> int:
        """Remove expired sessions.

        Returns:
            Number of sessions cleaned up.
        """
        count = await self.session_repo.delete_expired()
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")
        return count
