"""Chat repository for database operations.

Implements the Repository pattern for Chat, Message, and Feedback CRUD operations.
"""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat, Feedback, Message


class ChatRepository:
    """Repository for Chat database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the repository.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create(self, chat: Chat) -> Chat:
        """Create a new chat session.

        Args:
            chat: Chat instance to create.

        Returns:
            Created chat.
        """
        self.db.add(chat)
        await self.db.flush()
        await self.db.refresh(chat)
        return chat

    async def get_by_id(self, chat_id: str, user_id: str) -> Optional[Chat]:
        """Get a chat by ID, scoped to a user.

        Args:
            chat_id: Chat ID.
            user_id: Owner user ID.

        Returns:
            Chat instance or None.
        """
        result = await self.db.execute(
            select(Chat).where(
                Chat.id == chat_id,
                Chat.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Chat], int]:
        """List chats for a user.

        Args:
            user_id: Owner user ID.
            skip: Offset for pagination.
            limit: Maximum records.

        Returns:
            Tuple of (list of chats, total count).
        """
        count_result = await self.db.execute(
            select(func.count(Chat.id)).where(Chat.user_id == user_id)
        )
        total = count_result.scalar() or 0

        result = await self.db.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        chats = list(result.scalars().all())

        return chats, total

    async def delete(self, chat_id: str, user_id: str) -> bool:
        """Delete a chat and its messages.

        Args:
            chat_id: Chat ID.
            user_id: Owner user ID.

        Returns:
            True if deleted, False if not found.
        """
        chat = await self.get_by_id(chat_id, user_id)
        if chat is None:
            return False
        await self.db.delete(chat)
        return True


class MessageRepository:
    """Repository for Message database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the repository.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create(self, message: Message) -> Message:
        """Create a new message.

        Args:
            message: Message instance to create.

        Returns:
            Created message.
        """
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_by_chat(
        self, chat_id: str, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Message]:
        """Get messages for a chat, scoped to user.

        Args:
            chat_id: Chat ID.
            user_id: Owner user ID.
            skip: Offset.
            limit: Maximum messages.

        Returns:
            List of messages.
        """
        result = await self.db.execute(
            select(Message)
            .join(Chat, Message.chat_id == Chat.id)
            .where(
                Message.chat_id == chat_id,
                Chat.user_id == user_id,
            )
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        """Count total messages for a user.

        Args:
            user_id: User ID.

        Returns:
            Total message count.
        """
        result = await self.db.execute(
            select(func.count(Message.id))
            .join(Chat, Message.chat_id == Chat.id)
            .where(Chat.user_id == user_id)
        )
        return result.scalar() or 0


class FeedbackRepository:
    """Repository for Feedback database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the repository.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create(self, feedback: Feedback) -> Feedback:
        """Create a new feedback entry.

        Args:
            feedback: Feedback instance.

        Returns:
            Created feedback.
        """
        self.db.add(feedback)
        await self.db.flush()
        await self.db.refresh(feedback)
        return feedback

    async def get_by_message(self, message_id: str) -> List[Feedback]:
        """Get feedback for a message.

        Args:
            message_id: Message ID.

        Returns:
            List of feedback entries.
        """
        result = await self.db.execute(
            select(Feedback).where(Feedback.message_id == message_id)
        )
        return list(result.scalars().all())
