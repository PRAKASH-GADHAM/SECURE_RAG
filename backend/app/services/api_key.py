"""API key management service.

Handles creation, validation, listing, and revocation of API keys.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.user import APIKey
from app.repositories.api_key import APIKeyRepository
from app.schemas.auth import APIKeyCreateRequest, APIKeyResponse, APIKeyCreatedResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)


class APIKeyService:
    """Service for API key lifecycle management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_key_repo = APIKeyRepository(db)

    async def create_api_key(
        self,
        user_id: str,
        data: APIKeyCreateRequest,
    ) -> APIKeyCreatedResponse:
        """Create a new API key.

        Args:
            user_id: Owner user ID.
            data: API key creation data.

        Returns:
            Created API key response with raw key (shown once).
        """
        raw_key, key_hash, key_prefix = APIKeyRepository.generate_key()

        api_key = APIKey(
            user_id=user_id,
            name=data.name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            is_active=True,
            expires_at=data.expires_at,
        )

        api_key = await self.api_key_repo.create(api_key)

        logger.info(f"API key created: {data.name} for user {user_id}")

        return APIKeyCreatedResponse(
            id=api_key.id,
            name=api_key.name,
            key=raw_key,
            key_prefix=key_prefix,
            is_active=api_key.is_active,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            message="Save this key securely. It will not be shown again.",
        )

    async def list_api_keys(self, user_id: str) -> List[APIKeyResponse]:
        """List all API keys for a user.

        Args:
            user_id: Owner user ID.

        Returns:
            List of API key responses (without raw keys).
        """
        keys = await self.api_key_repo.list_by_user(user_id)
        return [
            APIKeyResponse(
                id=k.id,
                name=k.name,
                key_prefix=k.key_prefix,
                is_active=k.is_active,
                last_used_at=k.last_used_at,
                created_at=k.created_at,
                expires_at=k.expires_at,
            )
            for k in keys
        ]

    async def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """Revoke (deactivate) an API key.

        Args:
            key_id: API key ID.
            user_id: Owner user ID.

        Returns:
            True if revoked.
        """
        result = await self.api_key_repo.deactivate(key_id, user_id)
        if result:
            logger.info(f"API key revoked: {key_id} by user {user_id}")
        return result

    async def delete_api_key(self, key_id: str, user_id: str) -> bool:
        """Permanently delete an API key.

        Args:
            key_id: API key ID.
            user_id: Owner user ID.

        Returns:
            True if deleted.
        """
        result = await self.api_key_repo.delete(key_id, user_id)
        if result:
            logger.info(f"API key deleted: {key_id} by user {user_id}")
        return result

    async def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate an API key and return the associated key record.

        Args:
            raw_key: Raw API key string.

        Returns:
            APIKey if valid and active, None otherwise.
        """
        key_hash = APIKeyRepository.hash_key(raw_key)
        api_key = await self.api_key_repo.get_by_key_hash(key_hash)

        if api_key is None:
            return None

        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            logger.warning(f"Expired API key used: {api_key.id}")
            return None

        # Update last used
        await self.api_key_repo.update_last_used(api_key.id)

        return api_key
