"""Tests for document processor pipeline.

Tests the full parse -> chunk -> embed -> store pipeline with mocks.
"""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.core.exceptions import FileUploadException
from app.services.document_processor import DocumentProcessor


class TestDocumentProcessor:
    """Tests for the DocumentProcessor service with mocked dependencies."""

    def setup_method(self):
        """Set up test fixtures with mocked services."""
        self.processor = DocumentProcessor()

        # Mock parser
        self.mock_parsed = MagicMock()
        self.mock_parsed.content = "This is test document content for processing."
        self.mock_parsed.word_count = 8
        self.mock_parsed.page_count = 1
        self.mock_parsed.metadata = {"parser": "test"}

        # Mock chunker result
        from app.services.text_chunker import Chunk, ChunkingResult
        self.mock_chunk = Chunk(
            content="This is test document content for processing.",
            index=0,
            start_char=0,
            end_char=45,
            metadata={"document_id": "doc-1"},
        )
        self.mock_chunking_result = ChunkingResult(
            chunks=[self.mock_chunk],
            total_tokens=10,
            total_chunks=1,
        )

        # Mock embeddings
        self.mock_embeddings = [[0.1] * 384]

    @pytest.mark.asyncio
    async def test_process_document_success(self):
        """Test successful document processing pipeline."""
        self.processor.parser.parse = MagicMock(return_value=self.mock_parsed)
        self.processor.chunker.chunk_text = MagicMock(
            return_value=self.mock_chunking_result
        )
        self.processor.embedder.embed_batch = MagicMock(
            return_value=self.mock_embeddings
        )
        self.processor.embedder.dimension = 384
        self.processor.vector_store.add_chunks = MagicMock(return_value=1)

        # Mock DB session
        mock_db = AsyncMock()
        mock_chunk_repo = AsyncMock()
        mock_chunk_repo.create_many = AsyncMock()
        with patch(
            "app.services.document_processor.ChunkRepository",
            return_value=mock_chunk_repo,
        ):
            result = await self.processor.process_document(
                document_id="doc-1",
                user_id="user-1",
                file_path="/path/to/doc.pdf",
                file_type="pdf",
                filename="test.pdf",
                db=mock_db,
            )

        assert result["status"] == "completed"
        assert result["document_id"] == "doc-1"
        assert result["user_id"] == "user-1"
        assert result["chunk_count"] == 1
        assert result["total_tokens"] == 10
        assert result["word_count"] == 8
        assert result["embedding_dimension"] == 384
        assert "processing_time_seconds" in result

    @pytest.mark.asyncio
    async def test_process_document_empty_content(self):
        """Test processing document with empty extractable content."""
        self.mock_parsed.content = ""
        self.processor.parser.parse = MagicMock(return_value=self.mock_parsed)

        with pytest.raises(FileUploadException) as exc_info:
            await self.processor.process_document(
                document_id="doc-1",
                user_id="user-1",
                file_path="/path/to/doc.pdf",
                file_type="pdf",
            )

        assert "no extractable text" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_document_whitespace_content(self):
        """Test processing document with whitespace-only content."""
        self.mock_parsed.content = "   \n\n  "
        self.processor.parser.parse = MagicMock(return_value=self.mock_parsed)

        with pytest.raises(FileUploadException):
            await self.processor.process_document(
                document_id="doc-1",
                user_id="user-1",
                file_path="/path/to/doc.pdf",
                file_type="pdf",
            )

    @pytest.mark.asyncio
    async def test_process_document_parser_failure(self):
        """Test handling of parser failure."""
        self.processor.parser.parse = MagicMock(
            side_effect=FileUploadException("Parse error")
        )

        with pytest.raises(FileUploadException):
            await self.processor.process_document(
                document_id="doc-1",
                user_id="user-1",
                file_path="/path/to/bad.pdf",
                file_type="pdf",
            )

    @pytest.mark.asyncio
    async def test_process_document_without_db(self):
        """Test processing without DB session (no chunk records created)."""
        self.processor.parser.parse = MagicMock(return_value=self.mock_parsed)
        self.processor.chunker.chunk_text = MagicMock(
            return_value=self.mock_chunking_result
        )
        self.processor.embedder.embed_batch = MagicMock(
            return_value=self.mock_embeddings
        )
        self.processor.embedder.dimension = 384
        self.processor.vector_store.add_chunks = MagicMock(return_value=1)

        result = await self.processor.process_document(
            document_id="doc-1",
            user_id="user-1",
            file_path="/path/to/doc.pdf",
            file_type="pdf",
            filename="test.pdf",
            db=None,
        )

        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_process_document_stores_correct_metadata(self):
        """Test that correct metadata is passed to vector store."""
        self.processor.parser.parse = MagicMock(return_value=self.mock_parsed)
        self.processor.chunker.chunk_text = MagicMock(
            return_value=self.mock_chunking_result
        )
        self.processor.embedder.embed_batch = MagicMock(
            return_value=self.mock_embeddings
        )
        self.processor.embedder.dimension = 384
        self.processor.vector_store.add_chunks = MagicMock(return_value=1)

        await self.processor.process_document(
            document_id="doc-1",
            user_id="user-1",
            file_path="/path/to/doc.pdf",
            file_type="pdf",
            filename="test.pdf",
        )

        call_kwargs = self.processor.vector_store.add_chunks.call_args[1]
        assert call_kwargs["user_id"] == "user-1"
        assert call_kwargs["document_id"] == "doc-1"
        assert len(call_kwargs["chunk_ids"]) == 1
        assert len(call_kwargs["contents"]) == 1
        assert len(call_kwargs["embeddings"]) == 1
        assert len(call_kwargs["metadatas"]) == 1
        assert call_kwargs["metadatas"][0]["document_id"] == "doc-1"
        assert call_kwargs["metadatas"][0]["user_id"] == "user-1"

    @pytest.mark.asyncio
    async def test_process_document_general_exception(self):
        """Test handling of unexpected exceptions."""
        self.processor.parser.parse = MagicMock(return_value=self.mock_parsed)
        self.processor.chunker.chunk_text = MagicMock(
            side_effect=RuntimeError("Unexpected error")
        )

        with pytest.raises(FileUploadException) as exc_info:
            await self.processor.process_document(
                document_id="doc-1",
                user_id="user-1",
                file_path="/path/to/doc.pdf",
                file_type="pdf",
            )

        assert "Document processing failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_document_filenames(self):
        """Test that filename defaults to path basename when not provided."""
        self.processor.parser.parse = MagicMock(return_value=self.mock_parsed)
        self.processor.chunker.chunk_text = MagicMock(
            return_value=self.mock_chunking_result
        )
        self.processor.embedder.embed_batch = MagicMock(
            return_value=self.mock_embeddings
        )
        self.processor.embedder.dimension = 384
        self.processor.vector_store.add_chunks = MagicMock(return_value=1)

        await self.processor.process_document(
            document_id="doc-1",
            user_id="user-1",
            file_path="/uploads/user1/myfile.pdf",
            file_type="pdf",
            filename=None,
        )

        call_kwargs = self.processor.vector_store.add_chunks.call_args[1]
        assert call_kwargs["metadatas"][0]["filename"] == "myfile.pdf"
