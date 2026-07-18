"""User repository for database operations.

Implements the Repository pattern for User CRUD operations.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Repository for User database operations.

    Provides a clean interface for user CRUD operations,
    abstracting database access from the service layer.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the repository.

        Args:
            db: Async database session.
        """
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: User ID.

        Returns:
            User instance or None.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.

        Args:
            email: User email.

        Returns:
            User instance or None.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username.

        Args:
            username: Username.

        Returns:
            User instance or None.
        """
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: User instance to create.

        Returns:
            Created user with ID.
        """
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: User instance with updated fields.

        Returns:
            Updated user.
        """
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user_id: str) -> bool:
        """Delete a user by ID.

        Args:
            user_id: User ID.

        Returns:
            True if deleted, False if not found.
        """
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        await self.db.delete(user)
        return True

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        """List users with optional filtering and pagination.

        Args:
            skip: Number of records to skip.
            limit: Maximum records to return.
            is_active: Filter by active status.

        Returns:
            List of User instances.
        """
        query = select(User)

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(self, is_active: Optional[bool] = None) -> int:
        """Count users with optional filtering.

        Args:
            is_active: Filter by active status.

        Returns:
            Count of matching users.
        """
        from sqlalchemy import func

        query = select(func.count(User.id))
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def email_exists(self, email: str) -> bool:
        """Check if an email already exists.

        Args:
            email: Email to check.

        Returns:
            True if email exists.
        """
        user = await self.get_by_email(email)
        return user is not None

    async def username_exists(self, username: str) -> bool:
        """Check if a username already exists.

        Args:
            username: Username to check.

        Returns:
            True if username exists.
        """
        user = await self.get_by_username(username)
        return user is not None
