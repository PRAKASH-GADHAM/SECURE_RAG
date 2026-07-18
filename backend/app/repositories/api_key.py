"""API key repository for database operations."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import APIKey


class APIKeyRepository:
    """Repository for API key database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, api_key: APIKey) -> APIKey:
        """Create a new API key."""
        self.db.add(api_key)
        await self.db.flush()
        await self.db.refresh(api_key)
        return api_key

    async def get_by_id(self, key_id: str, user_id: str) -> Optional[APIKey]:
        """Get an API key by ID, scoped to user."""
        result = await self.db.execute(
            select(APIKey).where(
                APIKey.id == key_id,
                APIKey.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_key_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get an API key by its hash."""
        result = await self.db.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> List[APIKey]:
        """List all API keys for a user."""
        result = await self.db.execute(
            select(APIKey).where(
                APIKey.user_id == user_id,
            ).order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def deactivate(self, key_id: str, user_id: str) -> bool:
        """Deactivate an API key."""
        key = await self.get_by_id(key_id, user_id)
        if key is None:
            return False
        key.is_active = False
        await self.db.flush()
        return True

    async def update_last_used(self, key_id: str) -> None:
        """Update the last used timestamp."""
        key = await self.get_by_id_no_user(key_id)
        if key:
            key.last_used_at = datetime.now(timezone.utc)
            await self.db.flush()

    async def get_by_id_no_user(self, key_id: str) -> Optional[APIKey]:
        """Get an API key by ID without user scoping."""
        result = await self.db.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, key_id: str, user_id: str) -> bool:
        """Delete an API key."""
        key = await self.get_by_id(key_id, user_id)
        if key is None:
            return False
        await self.db.delete(key)
        return True

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """Generate a new API key.

        Returns:
            Tuple of (raw_key, key_hash, key_prefix).
        """
        raw_key = f"srag_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:10]
        return raw_key, key_hash, key_prefix

    @staticmethod
    def hash_key(raw_key: str) -> str:
        """Hash an API key for lookup."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
