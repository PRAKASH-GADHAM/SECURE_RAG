"""Session repository for database operations."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Session


class SessionRepository:
    """Repository for Session database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session: Session) -> Session:
        """Create a new session."""
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        result = await self.db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> Optional[Session]:
        """Get a session by access token."""
        result = await self.db.execute(
            select(Session).where(Session.token == token, Session.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_active_by_user(self, user_id: str) -> List[Session]:
        """Get all active sessions for a user."""
        result = await self.db.execute(
            select(Session).where(
                Session.user_id == user_id,
                Session.is_active == True,
            ).order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())

    async def deactivate(self, session_id: str) -> bool:
        """Deactivate a session."""
        session = await self.get_by_id(session_id)
        if session is None:
            return False
        session.is_active = False
        await self.db.flush()
        return True

    async def deactivate_by_token(self, token: str) -> bool:
        """Deactivate a session by access token."""
        session = await self.get_by_token(token)
        if session is None:
            return False
        session.is_active = False
        await self.db.flush()
        return True

    async def deactivate_all_user(self, user_id: str) -> int:
        """Deactivate all sessions for a user.

        Returns:
            Number of sessions deactivated.
        """
        sessions = await self.get_active_by_user(user_id)
        count = 0
        for session in sessions:
            session.is_active = False
            count += 1
        if count > 0:
            await self.db.flush()
        return count

    async def delete_expired(self) -> int:
        """Delete expired sessions.

        Returns:
            Number of sessions deleted.
        """
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Session).where(Session.expires_at < now)
        )
        expired = list(result.scalars().all())
        count = len(expired)
        for session in expired:
            await self.db.delete(session)
        if count > 0:
            await self.db.flush()
        return count
