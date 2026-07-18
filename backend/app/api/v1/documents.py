"""Document API endpoints.

Handles document upload, listing, retrieval, status checking, and deletion.
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.document import (
    DocumentListResponse,
    DocumentProcessingStatusResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.document import DocumentService

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Upload a document for RAG processing.

    Supports PDF, DOCX, TXT, and Markdown files.
    Processing begins automatically in the background.

    Args:
        file: Uploaded file.
        background_tasks: FastAPI background tasks (fallback processing).
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Upload confirmation with document details.
    """
    content = await file.read()
    service = DocumentService(db)
    return await service.upload_document(
        user_id=current_user.id,
        filename=file.filename or "unknown",
        file_content=content,
        file_size=len(content),
        content_type=file.content_type,
        background_tasks=background_tasks,
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List the current user's documents.

    Args:
        page: Page number.
        page_size: Items per page.
        status: Status filter.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Paginated document list.
    """
    service = DocumentService(db)
    return await service.list_documents(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get document details by ID.

    Args:
        document_id: Document ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Document details.
    """
    service = DocumentService(db)
    return await service.get_document(document_id, current_user.id)


@router.get(
    "/{document_id}/status",
    response_model=DocumentProcessingStatusResponse,
)
async def get_document_processing_status(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get document processing status with progress.

    Use this endpoint to poll for processing completion.
    The progress field ranges from 0.0 to 1.0.

    Args:
        document_id: Document ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Processing status with progress details.
    """
    service = DocumentService(db)
    return await service.get_processing_status(document_id, current_user.id)


@router.delete("/{document_id}", response_model=SuccessResponse)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a document and its chunks.

    Removes the document from the database, vector store, and filesystem.

    Args:
        document_id: Document ID.
        current_user: Authenticated user.
        db: Database session.

    Returns:
        Success confirmation.
    """
    service = DocumentService(db)
    await service.delete_document(document_id, current_user.id)
    return SuccessResponse(message="Document deleted successfully")
