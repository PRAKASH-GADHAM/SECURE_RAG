"""Source citation builder service.

Transforms raw retrieval results into structured SourceDocument objects
for API responses and audit trails.
"""

from typing import Optional

from app.schemas.chat import SourceDocument
from app.services.vector_store import VectorSearchResult
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SourceCitationBuilder:
    """Service for building source citations from retrieval results.

    Transforms VectorSearchResult objects into SourceDocument API objects
    with formatted citations for display.
    """

    @staticmethod
    def build_sources(
        results: list[VectorSearchResult],
        max_sources: int = 5,
    ) -> list[SourceDocument]:
        """Build source citations from search results.

        Args:
            results: Ranked search results from retrieval.
            max_sources: Maximum number of sources to include.

        Returns:
            List of SourceDocument objects for API response.
        """
        sources = []

        for result in results[:max_sources]:
            # Extract metadata
            filename = result.metadata.get("filename", "Unknown")
            page_str = result.metadata.get("page_number", "")
            section = result.metadata.get("section", "")

            page_number = None
            if page_str and page_str.isdigit():
                page_number = int(page_str)

            source = SourceDocument(
                document_id=result.document_id,
                document_name=filename,
                chunk_id=result.chunk_id,
                content=result.content,
                score=round(result.score, 4),
                page_number=page_number,
                section=section if section else None,
            )
            sources.append(source)

        logger.info(
            f"Built {len(sources)} source citations from "
            f"{len(results)} results"
        )

        return sources

    @staticmethod
    def build_context_string(
        results: list[VectorSearchResult],
        max_tokens_hint: int = 3000,
    ) -> str:
        """Build a context string from retrieval results for LLM prompting.

        Formats results as numbered references that the LLM can cite
        in its response.

        Args:
            results: Ranked search results.
            max_tokens_hint: Approximate max tokens for context.

        Returns:
            Formatted context string with source references.
        """
        if not results:
            return "No relevant context found."

        context_parts = []
        total_chars = 0
        char_limit = max_tokens_hint * 4  # Rough char-per-token estimate

        for i, result in enumerate(results, 1):
            filename = result.metadata.get("filename", "Unknown document")
            page = result.metadata.get("page_number", "")

            header = f"[Source {i}: {filename}"
            if page and page.isdigit():
                header += f", page {page}"
            header += "]"

            chunk_text = f"{header}\n{result.content}\n"

            if total_chars + len(chunk_text) > char_limit:
                break

            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        return "\n---\n".join(context_parts)

    @staticmethod
    def deduplicate_sources(
        sources: list[SourceDocument],
    ) -> list[SourceDocument]:
        """Remove duplicate sources (same chunk_id).

        Args:
            sources: List of source documents.

        Returns:
            Deduplicated list.
        """
        seen = set()
        deduped = []
        for source in sources:
            if source.chunk_id not in seen:
                seen.add(source.chunk_id)
                deduped.append(source)
        return deduped


# Module-level instance
source_citation_builder = SourceCitationBuilder()
