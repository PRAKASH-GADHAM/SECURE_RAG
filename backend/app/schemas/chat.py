"""Chat schemas for API request/response validation.

Defines Pydantic models for chat sessions, messages, and RAG queries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatCreateRequest(BaseModel):
    """Create new chat request schema."""

    title: Optional[str] = Field(None, max_length=255, description="Chat title")


class ChatResponse(BaseModel):
    """Chat session response schema."""

    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatListResponse(BaseModel):
    """Chat list response schema."""

    chats: List[ChatResponse]
    total: int


class SourceDocument(BaseModel):
    """Source document for RAG citation."""

    document_id: str
    document_name: str
    chunk_id: str
    content: str
    score: float
    rerank_score: Optional[float] = Field(None, description="Cross-encoder rerank score")
    page_number: Optional[int] = None
    section: Optional[str] = None


class QueryRequest(BaseModel):
    """RAG query request schema."""

    query: str = Field(
        ..., min_length=1, max_length=5000, description="User query"
    )
    chat_id: Optional[str] = Field(None, description="Chat ID for conversation context")
    top_k: Optional[int] = Field(
        default=None, ge=1, le=20, description="Number of results to retrieve"
    )
    retrieval_mode: Optional[str] = Field(
        default=None,
        description="Retrieval mode: dense, bm25, hybrid (default from config)",
    )
    document_ids: Optional[list[str]] = Field(
        default=None, description="Filter by specific document IDs"
    )
    use_reranking: bool = Field(
        default=True, description="Whether to use cross-encoder reranking"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None, description="Metadata filters"
    )


class QueryResponse(BaseModel):
    """RAG query response schema."""

    answer: str = Field(..., description="Generated answer")
    sources: List[SourceDocument] = Field(
        default_factory=list, description="Source documents used"
    )
    chat_id: str = Field(..., description="Chat ID")
    message_id: str = Field(..., description="Message ID")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    latency_ms: int = Field(default=0, description="Response latency in ms")
    model_used: Optional[str] = Field(None, description="Model used for generation")


class MessageResponse(BaseModel):
    """Chat message response schema."""

    id: str
    role: str
    content: str
    sources: Optional[str] = None
    tokens_used: int
    latency_ms: Optional[int] = None
    model_used: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackRequest(BaseModel):
    """Message feedback request schema."""

    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, max_length=50)


class FeedbackResponse(BaseModel):
    """Feedback response schema."""

    id: str
    message_id: str
    rating: int
    comment: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
