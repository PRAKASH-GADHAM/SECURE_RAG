"""Tests for text chunker service.

Covers text chunking, chunk sizing, overlap, empty handling, and metadata.
"""

import pytest

from app.services.text_chunker import TextChunker, Chunk, ChunkingResult


class TestTextChunkerChunkText:
    """Tests for chunk_text method."""

    def test_returns_chunking_result(self):
        tc = TextChunker(chunk_size=50, chunk_overlap=5)
        result = tc.chunk_text("Hello world, this is a test document.")
        assert isinstance(result, ChunkingResult)

    def test_returns_chunks(self):
        tc = TextChunker(chunk_size=50, chunk_overlap=5)
        result = tc.chunk_text("Hello world, this is a test document.")
        assert len(result.chunks) > 0

    def test_all_chunks_are_chunk_objects(self):
        tc = TextChunker(chunk_size=50, chunk_overlap=5)
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        result = tc.chunk_text(text)
        for chunk in result.chunks:
            assert isinstance(chunk, Chunk)

    def test_chunks_have_content(self):
        tc = TextChunker(chunk_size=50, chunk_overlap=5)
        result = tc.chunk_text("Hello world. This is some content for testing.")
        for chunk in result.chunks:
            assert len(chunk.content.strip()) > 0

    def test_chunks_have_indices(self):
        tc = TextChunker(chunk_size=50, chunk_overlap=5)
        result = tc.chunk_text("word " * 200)
        for i, chunk in enumerate(result.chunks):
            assert chunk.index == i


class TestEmptyAndWhitespaceText:
    """Tests for empty and whitespace text handling."""

    def test_empty_text_returns_empty(self):
        tc = TextChunker(chunk_size=100, chunk_overlap=10)
        result = tc.chunk_text("")
        assert result.total_chunks == 0
        assert len(result.chunks) == 0

    def test_whitespace_only_returns_empty(self):
        tc = TextChunker(chunk_size=100, chunk_overlap=10)
        result = tc.chunk_text("   \n\n   ")
        assert result.total_chunks == 0

    def test_none_like_empty(self):
        tc = TextChunker(chunk_size=100, chunk_overlap=10)
        result = tc.chunk_text("")
        assert result.total_tokens == 0


class TestChunkSizing:
    """Tests for chunk size behavior."""

    def test_chunks_respect_size(self):
        tc = TextChunker(chunk_size=20, chunk_overlap=2)
        text = "word " * 500
        result = tc.chunk_text(text)
        assert len(result.chunks) > 1

    def test_single_chunk_for_short_text(self):
        tc = TextChunker(chunk_size=512, chunk_overlap=50)
        result = tc.chunk_text("Hello world.")
        assert len(result.chunks) == 1

    def test_total_chunks_recorded(self):
        tc = TextChunker(chunk_size=20, chunk_overlap=2)
        text = "word " * 200
        result = tc.chunk_text(text)
        assert result.total_chunks == len(result.chunks)

    def test_total_tokens_positive(self):
        tc = TextChunker(chunk_size=50, chunk_overlap=5)
        result = tc.chunk_text("Hello world. This is a test sentence.")
        assert result.total_tokens > 0


class TestChunkMetadata:
    """Tests for chunk metadata."""

    def test_chunk_has_token_count(self):
        tc = TextChunker(chunk_size=50, chunk_overlap=5)
        result = tc.chunk_text("Hello world. Some more text here.")
        for chunk in result.chunks:
            assert chunk.token_count > 0

    def test_metadata_attached(self):
        tc = TextChunker(chunk_size=50, chunk_overlap=5)
        result = tc.chunk_text("Hello world.", metadata={"source": "test.pdf"})
        for chunk in result.chunks:
            assert "source" in chunk.metadata
            assert chunk.metadata["source"] == "test.pdf"

    def test_chunk_index_in_metadata(self):
        tc = TextChunker(chunk_size=50, chunk_overlap=5)
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three.\n\nParagraph four."
        result = tc.chunk_text(text)
        for i, chunk in enumerate(result.chunks):
            assert chunk.metadata.get("chunk_index") == i

    def test_start_and_end_chars(self):
        tc = TextChunker(chunk_size=50, chunk_overlap=5)
        result = tc.chunk_text("Hello world. This is some test content.")
        for chunk in result.chunks:
            assert chunk.start_char >= 0
            assert chunk.end_char >= chunk.start_char


class TestChunkingResult:
    """Tests for ChunkingResult dataclass."""

    def test_totals_computed(self):
        tc = TextChunker(chunk_size=50, chunk_overlap=5)
        result = tc.chunk_text("word " * 200)
        assert result.total_chunks == len(result.chunks)
        assert result.total_tokens == sum(c.token_count for c in result.chunks)

    def test_empty_result(self):
        result = ChunkingResult(chunks=[])
        assert result.total_chunks == 0
        assert result.total_tokens == 0


class TestCustomSeparators:
    """Tests for custom separators."""

    def test_split_by_period(self):
        tc = TextChunker(chunk_size=10, chunk_overlap=2, separators=[". "])
        result = tc.chunk_text("First sentence. Second sentence. Third sentence.")
        assert len(result.chunks) >= 1

    def test_split_by_newline(self):
        tc = TextChunker(chunk_size=10, chunk_overlap=2, separators=["\n"])
        result = tc.chunk_text("Line one\nLine two\nLine three\nLine four")
        assert len(result.chunks) >= 1


class TestModuleLevelInstance:
    """Tests for module-level text_chunker instance."""

    def test_exists(self):
        assert text_chunker is not None

    def test_is_text_chunker(self):
        assert isinstance(text_chunker, TextChunker)


# Import module-level instance
from app.services.text_chunker import text_chunker
