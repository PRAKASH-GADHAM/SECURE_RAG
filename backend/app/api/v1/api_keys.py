"""API Key management endpoints.

Handles creation, listing, revocation, and deletion of API keys.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_active_user
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.auth import (
    APIKeyCreateRequest,
    APIKeyCreatedResponse,
    APIKeyListResponse,
    APIKeyResponse,
)
from app.schemas.common import SuccessResponse
from app.services.api_key import APIKeyService

router = APIRouter()


@router.post("/", response_model=APIKeyCreatedResponse, status_code=201)
async def create_api_key(
    data: APIKeyCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new API key.

    The raw key is only shown once in the response. Store it securely.

    Args:
        data: API key creation data.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Created API key with raw key (shown once).
    """
    service = APIKeyService(db)
    return await service.create_api_key(current_user.id, data)


@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List all API keys for the current user.

    Args:
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of API keys (without raw keys).
    """
    service = APIKeyService(db)
    keys = await service.list_api_keys(current_user.id)
    return APIKeyListResponse(api_keys=keys, total=len(keys))


@router.delete("/{key_id}", response_model=SuccessResponse)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Revoke (deactivate) an API key.

    Args:
        key_id: API key ID to revoke.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Success confirmation.
    """
    service = APIKeyService(db)
    result = await service.revoke_api_key(key_id, current_user.id)
    if not result:
        raise NotFoundException("API Key", key_id)
    return SuccessResponse(message="API key revoked successfully")


@router.delete("/{key_id}/permanent", response_model=SuccessResponse)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Permanently delete an API key.

    Args:
        key_id: API key ID to delete.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Success confirmation.
    """
    service = APIKeyService(db)
    result = await service.delete_api_key(key_id, current_user.id)
    if not result:
        raise NotFoundException("API Key", key_id)
    return SuccessResponse(message="API key deleted successfully")
