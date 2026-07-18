"""Chat API endpoints.

Handles chat session creation, message history, and RAG queries.
"""

import json
import time
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.chat import (
    ChatCreateRequest,
    ChatListResponse,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    MessageResponse,
    QueryRequest,
    QueryResponse,
)
from app.schemas.common import SuccessResponse
from app.services.chat import ChatService
from app.services.rag import rag_service
from app.utils.logging import get_logger
from app.utils.validators import detect_prompt_injection

logger = get_logger(__name__)

router = APIRouter()


@router.post("/sessions", response_model=ChatResponse, status_code=201)
async def create_chat(
    data: Optional[ChatCreateRequest] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new chat session.

    Args:
        data: Optional chat creation data.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Created chat details.
    """
    service = ChatService(db)
    return await service.create_chat(current_user.id, data)


@router.get("/sessions", response_model=ChatListResponse)
async def list_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List the current user's chat sessions.

    Args:
        skip: Pagination offset.
        limit: Maximum results.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of chat sessions.
    """
    service = ChatService(db)
    return await service.list_chats(current_user.id, skip, limit)


@router.get("/sessions/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get chat session details.

    Args:
        chat_id: Chat ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Chat details with message count.
    """
    service = ChatService(db)
    return await service.get_chat(chat_id, current_user.id)


@router.delete("/sessions/{chat_id}", response_model=SuccessResponse)
async def delete_chat(
    chat_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a chat session and its messages.

    Args:
        chat_id: Chat ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Success confirmation.
    """
    service = ChatService(db)
    await service.delete_chat(chat_id, current_user.id)
    return SuccessResponse(message="Chat deleted successfully")


@router.get("/sessions/{chat_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    chat_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get messages for a chat session.

    Args:
        chat_id: Chat ID.
        skip: Pagination offset.
        limit: Maximum results.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        List of messages.
    """
    service = ChatService(db)
    return await service.get_messages(chat_id, current_user.id, skip, limit)


@router.post("/query", response_model=QueryResponse)
async def rag_query(
    data: QueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Execute a RAG query against the user's documents.

    Performs hybrid retrieval with LLM generation.
    Returns answer with sources and metadata.

    Args:
        data: Query request with retrieval parameters.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Query response with answer, sources, and metadata.
    """
    start_time = time.time()

    # Security: check for prompt injection
    if detect_prompt_injection(data.query):
        logger.warning(
            f"Prompt injection detected: user={current_user.id}, "
            f"query={data.query[:100]}"
        )
        return QueryResponse(
            answer="I'm sorry, but I cannot process this query. "
            "It appears to contain instructions that I'm not able to follow. "
            "Please ask a question about your documents.",
            sources=[],
            chat_id=data.chat_id or "",
            message_id="",
            tokens_used=0,
            latency_ms=int((time.time() - start_time) * 1000),
            model_used=None,
        )

    # Execute full RAG pipeline: retrieval + generation
    rag_result = await rag_service.generate(
        db=db,
        user_id=current_user.id,
        query=data.query,
        top_k=data.top_k,
        retrieval_mode=data.retrieval_mode,
        document_ids=data.document_ids,
        use_reranking=data.use_reranking,
        metadata_filters=data.filters,
    )

    # Build sources for response
    sources = source_citation_builder.build_sources(
        rag_result.results,
        max_sources=data.top_k or 5,
    )

    latency_ms = int((time.time() - start_time) * 1000)

    # Save user message and assistant message to chat
    service = ChatService(db)
    chat_id = data.chat_id

    # Auto-create chat if not provided
    if not chat_id:
        from app.schemas.chat import ChatCreateRequest
        chat_response = await service.create_chat(
            current_user.id,
            ChatCreateRequest(title=data.query[:100]),
        )
        chat_id = chat_response.id

    # Use the answer from LLM generation
    answer = rag_result.answer or (
        "No relevant documents found for your query. "
        "Try rephrasing your question or upload more documents."
    )

    # Save messages with RAG context
    assistant_message = await service.save_rag_message(
        chat_id=chat_id,
        user_id=current_user.id,
        query=data.query,
        sources_json=rag_result.sources_json,
        context_string=rag_result.context_string,
        total_chunks=rag_result.total_chunks,
        retrieval_mode=rag_result.retrieval_mode,
        latency_ms=latency_ms,
    )

    # Get token usage from LLM response
    tokens_used = 0
    model_used = None
    if rag_result.llm_response:
        tokens_used = rag_result.llm_response.usage.total_tokens
        model_used = rag_result.llm_response.model

    logger.info(
        f"RAG query completed: user={current_user.id}, "
        f"results={rag_result.total_chunks}, tokens={tokens_used}, "
        f"latency={latency_ms}ms"
    )

    return QueryResponse(
        answer=answer,
        sources=sources,
        chat_id=chat_id,
        message_id=assistant_message.id,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
        model_used=model_used,
    )


@router.post("/query/stream")
async def rag_query_stream(
    data: QueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Execute a RAG query with streaming response.

    Returns Server-Sent Events (SSE) for real-time token streaming.

    Args:
        data: Query request with retrieval parameters.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        StreamingResponse with SSE events.
    """
    # Security: check for prompt injection
    if detect_prompt_injection(data.query):
        logger.warning(
            f"Prompt injection detected: user={current_user.id}, "
            f"query={data.query[:100]}"
        )

        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'content': 'Query rejected for security reasons'})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
        )

    async def event_stream() -> AsyncIterator[str]:
        """Generate SSE events for streaming response."""
        try:
            # Send metadata event
            metadata = {
                "type": "metadata",
                "user_id": current_user.id,
                "retrieval_mode": data.retrieval_mode or "hybrid",
                "use_reranking": data.use_reranking,
            }
            yield f"data: {json.dumps(metadata)}\n\n"

            # Stream LLM response
            async for chunk in rag_service.generate_stream(
                db=db,
                user_id=current_user.id,
                query=data.query,
                top_k=data.top_k,
                retrieval_mode=data.retrieval_mode,
                document_ids=data.document_ids,
                use_reranking=data.use_reranking,
                metadata_filters=data.filters,
            ):
                if chunk.content:
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk.content})}\n\n"

                if chunk.finish_reason:
                    yield f"data: {json.dumps({'type': 'finish', 'reason': chunk.finish_reason.value})}\n\n"

            # Send completion marker
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/messages/{message_id}/feedback",
    response_model=FeedbackResponse,
    status_code=201,
)
async def add_feedback(
    message_id: str,
    data: FeedbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Add feedback to a chat message.

    Args:
        message_id: Message ID.
        data: Feedback data.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Created feedback.
    """
    service = ChatService(db)
    return await service.add_feedback(message_id, current_user.id, data)
