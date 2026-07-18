"""Chat service.

Handles chat session management, message operations,
and RAG context persistence.
"""

import json
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.chat import Chat, Feedback, Message
from app.repositories.chat import ChatRepository, FeedbackRepository, MessageRepository
from app.schemas.chat import (
    ChatCreateRequest,
    ChatListResponse,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    MessageResponse,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """Service for chat management operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the chat service.

        Args:
            db: Async database session.
        """
        self.db = db
        self.chat_repo = ChatRepository(db)
        self.message_repo = MessageRepository(db)
        self.feedback_repo = FeedbackRepository(db)

    async def create_chat(
        self, user_id: str, data: Optional[ChatCreateRequest] = None
    ) -> ChatResponse:
        """Create a new chat session.

        Args:
            user_id: Owner user ID.
            data: Optional chat creation data.

        Returns:
            Created chat response.
        """
        title = "New Chat"
        if data and data.title:
            title = data.title

        chat = Chat(user_id=user_id, title=title)
        chat = await self.chat_repo.create(chat)

        logger.info(f"Chat created: {chat.id} by user {user_id}")

        return ChatResponse(
            id=chat.id,
            title=chat.title,
            message_count=0,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    async def get_chat(self, chat_id: str, user_id: str) -> ChatResponse:
        """Get chat details.

        Args:
            chat_id: Chat ID.
            user_id: Owner user ID.

        Returns:
            Chat response.

        Raises:
            NotFoundException: If chat not found.
        """
        chat = await self.chat_repo.get_by_id(chat_id, user_id)
        if chat is None:
            raise NotFoundException("Chat", chat_id)

        messages = await self.message_repo.get_by_chat(chat_id, user_id)

        return ChatResponse(
            id=chat.id,
            title=chat.title,
            message_count=len(messages),
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    async def list_chats(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> ChatListResponse:
        """List user's chats.

        Args:
            user_id: Owner user ID.
            skip: Offset.
            limit: Maximum results.

        Returns:
            Chat list response.
        """
        chats, total = await self.chat_repo.list_by_user(user_id, skip, limit)

        return ChatListResponse(
            chats=[
                ChatResponse(
                    id=chat.id,
                    title=chat.title,
                    message_count=0,
                    created_at=chat.created_at,
                    updated_at=chat.updated_at,
                )
                for chat in chats
            ],
            total=total,
        )

    async def delete_chat(self, chat_id: str, user_id: str) -> bool:
        """Delete a chat and its messages.

        Args:
            chat_id: Chat ID.
            user_id: Owner user ID.

        Returns:
            True if deleted.
        """
        result = await self.chat_repo.delete(chat_id, user_id)
        if result:
            logger.info(f"Chat deleted: {chat_id} by user {user_id}")
        return result

    async def get_messages(
        self, chat_id: str, user_id: str, skip: int = 0, limit: int = 100
    ) -> list[MessageResponse]:
        """Get messages for a chat.

        Args:
            chat_id: Chat ID.
            user_id: Owner user ID.
            skip: Offset.
            limit: Maximum messages.

        Returns:
            List of message responses.
        """
        messages = await self.message_repo.get_by_chat(chat_id, user_id, skip, limit)

        return [
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                sources=msg.sources,
                tokens_used=msg.tokens_used,
                latency_ms=msg.latency_ms,
                model_used=msg.model_used,
                created_at=msg.created_at,
            )
            for msg in messages
        ]

    async def save_rag_message(
        self,
        chat_id: str,
        user_id: str,
        query: str,
        sources_json: str,
        context_string: str,
        total_chunks: int,
        retrieval_mode: str,
        latency_ms: int,
    ) -> Message:
        """Save RAG query and response messages to the chat.

        Creates both the user message (query) and assistant message (context)
        for audit trail and conversation history.

        Args:
            chat_id: Chat ID.
            user_id: Owner user ID.
            query: User query text.
            sources_json: Serialized source citations.
            context_string: Retrieved context string.
            total_chunks: Number of chunks retrieved.
            retrieval_mode: Retrieval mode used.
            latency_ms: Retrieval latency in milliseconds.

        Returns:
            The created assistant message.
        """
        # Save user message
        user_message = Message(
            chat_id=chat_id,
            role="user",
            content=query,
            sources=None,
            tokens_used=0,
            latency_ms=None,
            model_used=None,
        )
        await self.message_repo.create(user_message)

        # Save assistant message with RAG context
        context_used = json.dumps({
            "context_string": context_string,
            "total_chunks": total_chunks,
            "retrieval_mode": retrieval_mode,
        }, default=str)

        assistant_message = Message(
            chat_id=chat_id,
            role="assistant",
            content=f"[RAG Context Retrieved: {total_chunks} chunks via {retrieval_mode}]",
            sources=sources_json,
            context_used=context_used,
            tokens_used=0,
            model_used=None,
            latency_ms=latency_ms,
        )
        await self.message_repo.create(assistant_message)

        logger.info(
            f"RAG messages saved: chat={chat_id}, "
            f"chunks={total_chunks}, mode={retrieval_mode}"
        )

        return assistant_message

    async def add_feedback(
        self,
        message_id: str,
        user_id: str,
        data: FeedbackRequest,
    ) -> FeedbackResponse:
        """Add feedback to a message.

        Args:
            message_id: Message ID.
            user_id: User providing feedback.
            data: Feedback data.

        Returns:
            Feedback response.
        """
        feedback = Feedback(
            message_id=message_id,
            user_id=user_id,
            rating=data.rating,
            comment=data.comment,
            category=data.category,
        )

        feedback = await self.feedback_repo.create(feedback)

        logger.info(f"Feedback added: message={message_id}, rating={data.rating}")

        return FeedbackResponse(
            id=feedback.id,
            message_id=feedback.message_id,
            rating=feedback.rating,
            comment=feedback.comment,
            created_at=feedback.created_at,
        )
