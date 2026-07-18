"""Document processor service.

Orchestrates the full document processing pipeline:
parse -> chunk -> embed -> store in vector database -> record chunks in DB.

Supports both sync (Celery) and async (FastAPI BackgroundTasks) contexts.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import FileUploadException
from app.models.document import Chunk
from app.repositories.document import ChunkRepository, DocumentRepository
from app.services.document_parser import document_parser, ParsedDocument
from app.services.text_chunker import text_chunker, ChunkingResult
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class DocumentProcessor:
    """Service for processing documents through the full pipeline.

    Pipeline: parse -> chunk -> embed -> vector store -> DB records.
    """

    def __init__(self):
        """Initialize the document processor."""
        self.parser = document_parser
        self.chunker = text_chunker
        self.embedder = embedding_service
        self.vector_store = vector_store

    async def process_document(
        self,
        document_id: str,
        user_id: str,
        file_path: str,
        file_type: str,
        filename: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict:
        """Process a document through the full pipeline.

        Args:
            document_id: Document ID in the database.
            user_id: Owner user ID for namespace isolation.
            file_path: Path to the document file.
            file_type: Document file type extension.
            filename: Original filename for metadata.
            db: Optional database session for chunk record creation.

        Returns:
            Processing result with statistics.

        Raises:
            FileUploadException: If processing fails.
        """
        logger.info(
            f"Starting document processing: doc_id={document_id}, "
            f"user={user_id}, type={file_type}"
        )

        start_time = datetime.now(timezone.utc)

        try:
            # Step 1: Parse document
            parsed = self.parser.parse(file_path, file_type)
            logger.info(f"Parsed document: {parsed.word_count} words, {parsed.page_count} pages")

            if not parsed.content or not parsed.content.strip():
                raise FileUploadException("Document contains no extractable text")

            # Step 2: Chunk text
            chunk_metadata = {
                "document_id": document_id,
                "user_id": user_id,
                "filename": filename or os.path.basename(file_path),
                "file_type": file_type,
                **parsed.metadata,
            }
            chunking_result = self.chunker.chunk_text(parsed.content, chunk_metadata)
            logger.info(
                f"Chunked document: {chunking_result.total_chunks} chunks, "
                f"{chunking_result.total_tokens} tokens"
            )

            # Step 3: Generate embeddings
            chunk_contents = [c.content for c in chunking_result.chunks]
            embeddings = self.embedder.embed_batch(chunk_contents)
            logger.info(f"Generated {len(embeddings)} embeddings")

            # Step 4: Store in vector database
            chunk_ids = [str(uuid.uuid4()) for _ in chunking_result.chunks]
            chunk_metadatas = []
            for i, chunk in enumerate(chunking_result.chunks):
                meta = {
                    "chunk_id": chunk_ids[i],
                    "document_id": document_id,
                    "user_id": user_id,
                    "chunk_index": chunk.index,
                    "token_count": chunk.token_count,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "filename": filename or os.path.basename(file_path),
                    "file_type": file_type,
                    "page_number": str(chunk.metadata.get("page_number", "")),
                    "section": str(chunk.metadata.get("section", "")),
                }
                chunk_metadatas.append(meta)

            stored_count = self.vector_store.add_chunks(
                user_id=user_id,
                document_id=document_id,
                chunk_ids=chunk_ids,
                contents=chunk_contents,
                embeddings=embeddings,
                metadatas=chunk_metadatas,
            )

            # Step 5: Create chunk records in PostgreSQL
            if db is not None:
                await self._create_chunk_records(
                    db=db,
                    document_id=document_id,
                    chunking_result=chunking_result,
                    chunk_ids=chunk_ids,
                )

            # Calculate processing time
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()

            result = {
                "document_id": document_id,
                "user_id": user_id,
                "status": "completed",
                "chunk_count": stored_count,
                "total_tokens": chunking_result.total_tokens,
                "word_count": parsed.word_count,
                "page_count": parsed.page_count,
                "embedding_dimension": self.embedder.dimension,
                "processing_time_seconds": round(processing_time, 2),
            }

            logger.info(
                f"Document processing completed: doc_id={document_id}, "
                f"chunks={stored_count}, tokens={chunking_result.total_tokens}, "
                f"time={processing_time:.2f}s"
            )

            return result

        except FileUploadException:
            raise
        except Exception as e:
            logger.error(f"Document processing failed: doc_id={document_id}, error={e}")
            raise FileUploadException(f"Document processing failed: {str(e)}")

    async def _create_chunk_records(
        self,
        db: AsyncSession,
        document_id: str,
        chunking_result: ChunkingResult,
        chunk_ids: list[str],
    ) -> None:
        """Create Chunk records in PostgreSQL for each chunk.

        Args:
            db: Database session.
            document_id: Parent document ID.
            chunking_result: Result from the text chunker.
            chunk_ids: Vector store chunk IDs (for embedding_id reference).
        """
        chunk_repo = ChunkRepository(db)
        db_chunks = []

        for i, chunk in enumerate(chunking_result.chunks):
            db_chunk = Chunk(
                document_id=document_id,
                content=chunk.content,
                chunk_index=chunk.index,
                token_count=chunk.token_count,
                embedding_id=chunk_ids[i],
                page_number=chunk.metadata.get("page_number"),
                section=chunk.metadata.get("section"),
            )
            db_chunks.append(db_chunk)

        await chunk_repo.create_many(db_chunks)
        logger.info(f"Created {len(db_chunks)} chunk records in database")

    async def reprocess_document(
        self,
        document_id: str,
        user_id: str,
        file_path: str,
        file_type: str,
        filename: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> dict:
        """Reprocess a document (delete old chunks first).

        Args:
            document_id: Document ID.
            user_id: Owner user ID.
            file_path: Path to the document file.
            file_type: Document file type.
            filename: Original filename.
            db: Optional database session.

        Returns:
            Processing result.
        """
        # Delete existing chunks from vector store
        self.vector_store.delete_document(user_id, document_id)
        logger.info(f"Deleted old chunks for document: {document_id}")

        # Delete old DB chunks
        if db is not None:
            chunk_repo = ChunkRepository(db)
            await chunk_repo.delete_by_document(document_id)

        # Process fresh
        return await self.process_document(
            document_id=document_id,
            user_id=user_id,
            file_path=file_path,
            file_type=file_type,
            filename=filename,
            db=db,
        )


# Module-level instance
document_processor = DocumentProcessor()
