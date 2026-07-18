"""Document service.

Handles document upload, processing, and management.
Supports background processing via Celery with fallback to FastAPI BackgroundTasks.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import FileUploadException, NotFoundException
from app.models.document import Document
from app.repositories.document import ChunkRepository, DocumentRepository
from app.schemas.document import (
    DocumentListResponse,
    DocumentProcessingStatusResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.utils.logging import get_logger
from app.utils.validators import validate_file_upload

logger = get_logger(__name__)
settings = get_settings()


async def _fallback_process_document(
    document_id: str,
    user_id: str,
    file_path: str,
    file_type: str,
    filename: Optional[str],
) -> None:
    """Fallback synchronous processing when Celery is unavailable.

    Runs the full document processing pipeline using a new DB session.

    Args:
        document_id: Document ID in the database.
        user_id: Owner user ID.
        file_path: Path to the document file.
        file_type: Document file type.
        filename: Original filename.
    """
    from app.database import get_session_factory
    from app.repositories.document import DocumentRepository
    from app.services.document_processor import document_processor

    session_factory = get_session_factory()
    async with session_factory() as db:
        doc_repo = DocumentRepository(db)
        try:
            await doc_repo.update_status(document_id, status="processing")
            await db.commit()

            result = await document_processor.process_document(
                document_id=document_id,
                user_id=user_id,
                file_path=file_path,
                file_type=file_type,
                filename=filename,
                db=db,
            )

            await doc_repo.update_status(
                document_id,
                status="completed",
                chunk_count=result["chunk_count"],
                total_tokens=result["total_tokens"],
            )
            await db.commit()

            logger.info(
                f"Fallback processing completed: doc_id={document_id}, "
                f"chunks={result['chunk_count']}"
            )

        except Exception as e:
            try:
                await doc_repo.update_status(
                    document_id,
                    status="failed",
                    error_message=str(e),
                )
                await db.commit()
            except Exception:
                logger.error(f"Failed to update document status: {document_id}")

            logger.error(f"Fallback processing failed: {document_id}, error={e}")


class DocumentService:
    """Service for document management operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the document service.

        Args:
            db: Async database session.
        """
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.chunk_repo = ChunkRepository(db)

    async def upload_document(
        self,
        user_id: str,
        filename: str,
        file_content: bytes,
        file_size: int,
        content_type: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> DocumentUploadResponse:
        """Upload and validate a document, then trigger background processing.

        Tries Celery first; falls back to FastAPI BackgroundTasks if Celery
        broker is unavailable.

        Args:
            user_id: Owner user ID.
            filename: Original filename.
            file_content: File content bytes.
            file_size: Size in bytes.
            content_type: MIME type.
            background_tasks: FastAPI BackgroundTasks for fallback processing.

        Returns:
            Upload response with document details.

        Raises:
            FileUploadException: If file validation fails.
        """
        # Validate file
        validate_file_upload(filename, file_size, content_type)

        # Generate unique filename
        file_ext = filename.rsplit(".", 1)[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, user_id, unique_filename)

        # Ensure upload directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save file
        try:
            with open(file_path, "wb") as f:
                f.write(file_content)
        except IOError as e:
            raise FileUploadException(f"Failed to save file: {str(e)}")

        # Create document record
        document = Document(
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_ext,
            mime_type=content_type,
            status="pending",
        )

        document = await self.doc_repo.create(document)

        # Try Celery first, fall back to BackgroundTasks
        processing_triggered = False
        try:
            from app.tasks.document_tasks import process_document_task
            process_document_task.delay(
                document_id=document.id,
                user_id=user_id,
                file_path=file_path,
                file_type=file_ext,
                filename=filename,
            )
            processing_triggered = True
            logger.info(f"Triggered Celery processing task for document: {document.id}")
        except Exception as e:
            logger.warning(f"Celery unavailable, trying fallback: {e}")

        if not processing_triggered and background_tasks is not None:
            background_tasks.add_task(
                _fallback_process_document,
                document_id=document.id,
                user_id=user_id,
                file_path=file_path,
                file_type=file_ext,
                filename=filename,
            )
            logger.info(f"Triggered fallback processing for document: {document.id}")

        logger.info(
            f"Document uploaded: {filename} by user {user_id}, "
            f"doc_id={document.id}"
        )

        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            file_size=document.file_size,
            file_type=document.file_type,
            status=document.status,
            message="Document uploaded successfully. Processing will begin shortly.",
            created_at=document.created_at,
        )

    async def get_document(
        self, document_id: str, user_id: str
    ) -> DocumentResponse:
        """Get document details.

        Args:
            document_id: Document ID.
            user_id: Owner user ID.

        Returns:
            Document response.

        Raises:
            NotFoundException: If document not found.
        """
        document = await self.doc_repo.get_by_id(document_id, user_id)
        if document is None:
            raise NotFoundException("Document", document_id)

        return DocumentResponse.model_validate(document)

    async def get_processing_status(
        self, document_id: str, user_id: str
    ) -> DocumentProcessingStatusResponse:
        """Get detailed document processing status.

        Args:
            document_id: Document ID.
            user_id: Owner user ID.

        Returns:
            Processing status response with progress details.

        Raises:
            NotFoundException: If document not found.
        """
        document = await self.doc_repo.get_by_id(document_id, user_id)
        if document is None:
            raise NotFoundException("Document", document_id)

        # Calculate progress percentage based on status
        progress_map = {
            "pending": 0.0,
            "processing": 0.5,
            "completed": 1.0,
            "failed": 1.0,
        }

        return DocumentProcessingStatusResponse(
            id=document.id,
            filename=document.filename,
            status=document.status,
            progress=progress_map.get(document.status, 0.0),
            chunk_count=document.chunk_count,
            total_tokens=document.total_tokens,
            error_message=document.error_message,
            processed_at=document.processed_at,
            created_at=document.created_at,
        )

    async def list_documents(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> DocumentListResponse:
        """List user's documents with pagination.

        Args:
            user_id: Owner user ID.
            page: Page number (1-based).
            page_size: Items per page.
            status: Filter by status.

        Returns:
            Paginated document list.
        """
        skip = (page - 1) * page_size
        documents, total = await self.doc_repo.list_by_user(
            user_id, skip=skip, limit=page_size, status=status
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(doc) for doc in documents],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """Delete a document and its chunks.

        Args:
            document_id: Document ID.
            user_id: Owner user ID.

        Returns:
            True if deleted.

        Raises:
            NotFoundException: If document not found.
        """
        document = await self.doc_repo.get_by_id(document_id, user_id)
        if document is None:
            raise NotFoundException("Document", document_id)

        # Delete chunks from DB first
        await self.chunk_repo.delete_by_document(document_id)

        # Delete vectors from ChromaDB (try Celery, fallback to sync)
        try:
            from app.tasks.document_tasks import delete_document_vectors_task
            delete_document_vectors_task.delay(
                document_id=document_id,
                user_id=user_id,
            )
        except Exception as e:
            logger.warning(f"Celery unavailable for vector deletion: {e}")
            # Fallback: delete vectors synchronously
            try:
                from app.services.vector_store import vector_store
                vector_store.delete_document(user_id, document_id)
            except Exception as ve:
                logger.error(f"Failed to delete vectors: {ve}")

        # Delete physical file
        if os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
            except OSError as e:
                logger.warning(f"Failed to delete file {document.file_path}: {e}")

        # Delete document record
        await self.doc_repo.delete(document_id, user_id)

        logger.info(f"Document deleted: {document_id} by user {user_id}")

        return True
