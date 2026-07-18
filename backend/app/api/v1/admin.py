"""Admin API endpoints.

Handles admin-only operations like user management and system stats.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_admin_user
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import UserResponse
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List all users (admin only).

    Args:
        skip: Pagination offset.
        limit: Maximum results.
        current_user: Admin user.
        db: Database session.

    Returns:
        List of all users.
    """
    user_repo = UserRepository(db)
    users = await user_repo.list_users(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


@router.get("/stats")
async def get_system_stats(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get system statistics (admin only).

    Args:
        current_user: Admin user.
        db: Database session.

    Returns:
        System statistics.
    """
    user_repo = UserRepository(db)
    total_users = await user_repo.count()
    active_users = await user_repo.count(is_active=True)

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
    }


@router.put("/users/{user_id}/deactivate", response_model=SuccessResponse)
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Deactivate a user account (admin only).

    Args:
        user_id: User ID to deactivate.
        current_user: Admin user.
        db: Database session.

    Returns:
        Success confirmation.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        return SuccessResponse(message="User not found", data={"found": False})

    user.is_active = False
    await user_repo.update(user)

    return SuccessResponse(
        message=f"User {user.email} deactivated",
        data={"found": True},
    )
