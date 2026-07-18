"""Celery tasks for document processing.

Handles background document processing including:
- Document parsing (PDF, DOCX, TXT, MD)
- Text chunking
- Embedding generation
- Vector store insertion
- Chunk DB record creation

All async database operations are run via asyncio event loop
since Celery workers execute synchronously.
"""

import asyncio
from typing import Optional

from celery import shared_task

from app.utils.logging import get_logger

logger = get_logger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery worker.

    Uses the existing event loop if available, otherwise creates a new one.

    Args:
        coro: Async coroutine to execute.

    Returns:
        Result of the coroutine.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # Already in an async loop (shouldn't happen in Celery, but safety net)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=300)
    else:
        return asyncio.run(coro)


@shared_task(bind=True, name="tasks.process_document", max_retries=3)
def process_document_task(
    self,
    document_id: str,
    user_id: str,
    file_path: str,
    file_type: str,
    filename: Optional[str] = None,
):
    """Background task to process a document.

    Orchestrates: parse -> chunk -> embed -> store -> DB records.
    Updates document status throughout the pipeline.

    Args:
        document_id: Document ID in the database.
        user_id: Owner user ID.
        file_path: Path to the document file.
        file_type: Document file type extension.
        filename: Original filename.
    """
    from app.database import get_session_factory
    from app.repositories.document import DocumentRepository
    from app.services.document_processor import document_processor

    logger.info(f"Starting document processing task: doc_id={document_id}")

    async def _process():
        session_factory = get_session_factory()
        async with session_factory() as db:
            doc_repo = DocumentRepository(db)

            try:
                # Update status to processing
                await doc_repo.update_status(document_id, status="processing")
                await db.commit()

                # Run the full pipeline with DB session for chunk record creation
                result = await document_processor.process_document(
                    document_id=document_id,
                    user_id=user_id,
                    file_path=file_path,
                    file_type=file_type,
                    filename=filename,
                    db=db,
                )

                # Update status to completed
                await doc_repo.update_status(
                    document_id,
                    status="completed",
                    chunk_count=result["chunk_count"],
                    total_tokens=result["total_tokens"],
                )
                await db.commit()

                logger.info(
                    f"Document processing task completed: doc_id={document_id}, "
                    f"chunks={result['chunk_count']}"
                )

                return result

            except Exception as e:
                logger.error(f"Document processing task failed: {document_id}, error={e}")
                # Only set failed status on final exhaustion (no more retries)
                if self.request.retries >= self.max_retries:
                    try:
                        await doc_repo.update_status(
                            document_id,
                            status="failed",
                            error_message=str(e),
                        )
                        await db.commit()
                    except Exception:
                        logger.error(f"Failed to update document status: {document_id}")
                raise self.retry(exc=e, countdown=60)

    return _run_async(_process())


@shared_task(bind=True, name="tasks.delete_document_vectors", max_retries=2)
def delete_document_vectors_task(
    self,
    document_id: str,
    user_id: str,
):
    """Background task to delete document vectors and chunk records.

    Args:
        document_id: Document ID.
        user_id: Owner user ID.
    """
    from app.database import get_session_factory
    from app.repositories.document import ChunkRepository
    from app.services.vector_store import vector_store

    async def _delete():
        # Delete from vector store
        deleted_count = vector_store.delete_document(user_id, document_id)
        logger.info(f"Deleted {deleted_count} vectors for document: {document_id}")

        # Delete chunk records from DB
        session_factory = get_session_factory()
        async with session_factory() as db:
            chunk_repo = ChunkRepository(db)
            await chunk_repo.delete_by_document(document_id)
            await db.commit()

        return {"deleted_count": deleted_count}

    return _run_async(_delete())
