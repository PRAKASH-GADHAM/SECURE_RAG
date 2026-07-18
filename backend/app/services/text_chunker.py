"""Text chunker service.

Implements recursive character text splitting with token awareness
for preparing documents for embedding and storage.
"""

from dataclasses import dataclass, field
from typing import Optional

import tiktoken

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class Chunk:
    """A text chunk with metadata."""

    content: str
    index: int
    start_char: int
    end_char: int
    token_count: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Calculate token count after initialization."""
        if self.content and not self.token_count:
            encoder = tiktoken.get_encoding("cl100k_base")
            self.token_count = len(encoder.encode(self.content))


@dataclass
class ChunkingResult:
    """Result of text chunking operation."""

    chunks: list[Chunk]
    total_tokens: int = 0
    total_chunks: int = 0

    def __post_init__(self):
        """Calculate totals after initialization."""
        if self.chunks:
            self.total_chunks = len(self.chunks)
            self.total_tokens = sum(c.token_count for c in self.chunks)


class TextChunker:
    """Service for splitting text into chunks.

    Uses recursive character splitting with configurable size and overlap.
    Token-aware to stay within embedding model limits.
    """

    # Default separators in priority order
    DEFAULT_SEPARATORS = [
        "\n\n",  # Paragraph breaks
        "\n",    # Line breaks
        ". ",    # Sentences
        "! ",    # Sentences
        "? ",    # Sentences
        "; ",    # Clauses
        ", ",    # Phrases
        " ",     # Words
        "",      # Characters
    ]

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[list[str]] = None,
        encoding_name: str = "cl100k_base",
    ):
        """Initialize the text chunker.

        Args:
            chunk_size: Maximum tokens per chunk (default from config).
            chunk_overlap: Token overlap between chunks (default from config).
            separators: Custom separators for recursive splitting.
            encoding_name: tiktoken encoding name for token counting.
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.separators = separators or self.DEFAULT_SEPARATORS
        self.encoder = tiktoken.get_encoding(encoding_name)

    def chunk_text(
        self,
        text: str,
        metadata: Optional[dict] = None,
    ) -> ChunkingResult:
        """Split text into chunks using recursive character splitting.

        Args:
            text: Text content to chunk.
            metadata: Optional metadata to attach to each chunk.

        Returns:
            ChunkingResult with chunks and statistics.
        """
        if not text or not text.strip():
            return ChunkingResult(chunks=[])

        metadata = metadata or {}

        # Recursively split text
        raw_chunks = self._recursive_split(text, self.separators)

        # Merge small chunks and create final chunks
        chunks = self._merge_and_create_chunks(raw_chunks, metadata)

        result = ChunkingResult(chunks=chunks)

        logger.info(
            f"Chunked text: {len(text)} chars → {result.total_chunks} chunks, "
            f"{result.total_tokens} tokens"
        )

        return result

    def _recursive_split(
        self,
        text: str,
        separators: list[str],
    ) -> list[str]:
        """Recursively split text using separators.

        Args:
            text: Text to split.
            separators: List of separators in priority order.

        Returns:
            List of text pieces.
        """
        if len(text) <= self.chunk_size * 4:  # Rough char estimate
            # Verify with actual token count to avoid oversized chunks
            token_count = len(self.encoder.encode(text))
            if token_count <= self.chunk_size:
                return [text] if text.strip() else []
            # Fall through to splitting if token count exceeds chunk_size

        if not separators:
            return self._force_split(text)

        separator = separators[0]
        remaining_separators = separators[1:]

        if separator == "":
            return self._force_split(text)

        parts = text.split(separator)

        result = []
        for part in parts:
            if not part.strip():
                continue

            token_count = len(self.encoder.encode(part))
            if token_count <= self.chunk_size:
                result.append(part)
            elif remaining_separators:
                result.extend(self._recursive_split(part, remaining_separators))
            else:
                result.extend(self._force_split(part))

        return result

    def _force_split(self, text: str) -> list[str]:
        """Force split text at token boundaries.

        Args:
            text: Text to split.

        Returns:
            List of text pieces within chunk_size tokens.
        """
        tokens = self.encoder.encode(text)
        pieces = []

        for i in range(0, len(tokens), self.chunk_size - self.chunk_overlap):
            chunk_tokens = tokens[i : i + self.chunk_size]
            piece = self.encoder.decode(chunk_tokens)
            if piece.strip():
                pieces.append(piece)

        return pieces

    def _merge_and_create_chunks(
        self,
        pieces: list[str],
        metadata: dict,
    ) -> list[Chunk]:
        """Merge small pieces and create Chunk objects.

        Args:
            pieces: Text pieces to merge.
            metadata: Metadata to attach to chunks.

        Returns:
            List of Chunk objects.
        """
        chunks = []
        current_text = ""
        current_start = 0
        char_offset = 0

        for piece in pieces:
            piece_tokens = len(self.encoder.encode(piece))
            current_tokens = len(self.encoder.encode(current_text)) if current_text else 0

            if current_tokens + piece_tokens > self.chunk_size and current_text:
                # Finalize current chunk
                chunk = Chunk(
                    content=current_text.strip(),
                    index=len(chunks),
                    start_char=current_start,
                    end_char=current_start + len(current_text),
                    metadata={**metadata, "chunk_index": len(chunks)},
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_text)
                current_text = overlap_text + piece
                current_start = char_offset - len(overlap_text)
            else:
                if not current_text:
                    current_start = char_offset
                current_text += piece + " "

            char_offset += len(piece) + 1  # +1 for separator

        # Don't forget the last chunk
        if current_text.strip():
            chunk = Chunk(
                content=current_text.strip(),
                index=len(chunks),
                start_char=current_start,
                end_char=current_start + len(current_text),
                metadata={**metadata, "chunk_index": len(chunks)},
            )
            chunks.append(chunk)

        return chunks

    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of a chunk.

        Args:
            text: Text to get overlap from.

        Returns:
            Overlap text with approximately chunk_overlap tokens.
        """
        if not text:
            return ""

        tokens = self.encoder.encode(text)
        if len(tokens) <= self.chunk_overlap:
            return text

        overlap_tokens = tokens[-self.chunk_overlap :]
        return self.encoder.decode(overlap_tokens)


# Module-level instance
text_chunker = TextChunker()
