"""Document repository for database operations.

Implements the Repository pattern for Document and Chunk CRUD operations.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Chunk, Document


class DocumentRepository:
    """Repository for Document database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the repository.

        Args:
            db: Async database session.
        """
        self.db = db

    async def get_by_id(self, document_id: str, user_id: str) -> Optional[Document]:
        """Get a document by ID, scoped to a user.

        Args:
            document_id: Document ID.
            user_id: Owner user ID.

        Returns:
            Document instance or None.
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, document: Document) -> Document:
        """Create a new document.

        Args:
            document: Document instance to create.

        Returns:
            Created document.
        """
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def update(self, document: Document) -> Document:
        """Update an existing document.

        Args:
            document: Document instance with updated fields.

        Returns:
            Updated document.
        """
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def delete(self, document_id: str, user_id: str) -> bool:
        """Delete a document and its chunks.

        Args:
            document_id: Document ID.
            user_id: Owner user ID.

        Returns:
            True if deleted, False if not found.
        """
        document = await self.get_by_id(document_id, user_id)
        if document is None:
            return False
        await self.db.delete(document)
        return True

    async def list_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> tuple[List[Document], int]:
        """List documents for a user with pagination.

        Args:
            user_id: Owner user ID.
            skip: Number of records to skip.
            limit: Maximum records to return.
            status: Filter by processing status.

        Returns:
            Tuple of (list of documents, total count).
        """
        query = select(Document).where(Document.user_id == user_id)

        if status:
            query = query.where(Document.status == status)

        # Get total count
        count_query = select(func.count(Document.id)).where(Document.user_id == user_id)
        if status:
            count_query = count_query.where(Document.status == status)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        documents = list(result.scalars().all())

        return documents, total

    async def get_pending_documents(self, limit: int = 10) -> List[Document]:
        """Get documents pending processing.

        Args:
            limit: Maximum documents to return.

        Returns:
            List of pending documents.
        """
        result = await self.db.execute(
            select(Document)
            .where(Document.status == "pending")
            .order_by(Document.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        document_id: str,
        status: str,
        chunk_count: Optional[int] = None,
        total_tokens: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Document]:
        """Update document processing status.

        Args:
            document_id: Document ID.
            status: New status (pending, processing, completed, failed).
            chunk_count: Number of chunks created.
            total_tokens: Total token count.
            error_message: Error message if failed.

        Returns:
            Updated document or None.
        """
        from sqlalchemy import select

        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if document is None:
            return None

        document.status = status
        if chunk_count is not None:
            document.chunk_count = chunk_count
        if total_tokens is not None:
            document.total_tokens = total_tokens
        if error_message is not None:
            document.error_message = error_message
        if status == "completed":
            document.processed_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(document)
        return document


class ChunkRepository:
    """Repository for Chunk database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the repository.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create(self, chunk: Chunk) -> Chunk:
        """Create a new chunk.

        Args:
            chunk: Chunk instance to create.

        Returns:
            Created chunk.
        """
        self.db.add(chunk)
        await self.db.flush()
        await self.db.refresh(chunk)
        return chunk

    async def create_many(self, chunks: List[Chunk]) -> List[Chunk]:
        """Create multiple chunks.

        Args:
            chunks: List of Chunk instances.

        Returns:
            List of created chunks.
        """
        self.db.add_all(chunks)
        await self.db.flush()
        for chunk in chunks:
            await self.db.refresh(chunk)
        return chunks

    async def get_by_document(
        self, document_id: str, user_id: str
    ) -> List[Chunk]:
        """Get all chunks for a document.

        Args:
            document_id: Document ID.
            user_id: Owner user ID (for security scoping).

        Returns:
            List of chunks.
        """
        result = await self.db.execute(
            select(Chunk)
            .join(Document, Chunk.document_id == Document.id)
            .where(
                Chunk.document_id == document_id,
                Document.user_id == user_id,
            )
            .order_by(Chunk.chunk_index)
        )
        return list(result.scalars().all())

    async def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document.

        Args:
            document_id: Document ID.

        Returns:
            Number of chunks deleted.
        """
        result = await self.db.execute(
            select(Chunk).where(Chunk.document_id == document_id)
        )
        chunks = list(result.scalars().all())
        count = len(chunks)
        for chunk in chunks:
            await self.db.delete(chunk)
        return count

    async def count_by_user(self, user_id: str) -> int:
        """Count total chunks for a user.

        Args:
            user_id: User ID.

        Returns:
            Total chunk count.
        """
        result = await self.db.execute(
            select(func.count(Chunk.id))
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.user_id == user_id)
        )
        return result.scalar() or 0
