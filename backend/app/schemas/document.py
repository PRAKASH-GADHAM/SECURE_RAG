"""Document schemas for API request/response validation.

Defines Pydantic models for document upload, status, processing progress, and retrieval.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Document upload response schema."""

    id: str
    filename: str
    file_size: int
    file_type: str
    status: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Document detail response schema."""

    id: str
    filename: str
    file_size: int
    file_type: str
    status: str
    chunk_count: int
    total_tokens: int
    error_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentProcessingStatusResponse(BaseModel):
    """Document processing status response schema.

    Provides detailed processing progress for polling from the frontend.
    """

    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Original filename")
    status: str = Field(
        ...,
        description="Processing status: pending, processing, completed, failed",
    )
    progress: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Processing progress from 0.0 to 1.0",
    )
    chunk_count: int = Field(default=0, description="Number of chunks created")
    total_tokens: int = Field(default=0, description="Total token count")
    error_message: Optional[str] = Field(
        None, description="Error message if processing failed"
    )
    processed_at: Optional[datetime] = Field(
        None, description="When processing completed"
    )
    created_at: datetime = Field(..., description="Upload timestamp")


class DocumentListResponse(BaseModel):
    """Document list response schema with pagination."""

    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ChunkResponse(BaseModel):
    """Chunk response schema."""

    id: str
    content: str
    chunk_index: int
    token_count: int
    page_number: Optional[int] = None
    section: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentMetadata(BaseModel):
    """Document metadata schema."""

    filename: str
    file_type: str
    file_size: int
    page_count: Optional[int] = None
    author: Optional[str] = None
    created_date: Optional[datetime] = None
    custom_metadata: Optional[Dict[str, Any]] = None
