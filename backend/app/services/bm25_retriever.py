"""BM25 retriever service.

Implements keyword-based retrieval using BM25 (Best Matching 25) algorithm.
Builds per-user BM25 indexes from PostgreSQL chunk records with in-memory caching.

BM25 complements dense retrieval by matching exact keywords, acronyms,
and domain-specific terms that embedding models may underweight.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.document import Chunk, Document
from app.services.vector_store import VectorSearchResult
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class BM25Index:
    """Cached BM25 index for a user."""

    user_id: str
    corpus: list[str]
    tokenized_corpus: list[list[str]]
    chunk_ids: list[str]
    document_ids: list[str]
    chunk_contents: list[str]
    chunk_metadatas: list[dict]
    bm25: BM25Okapi
    created_at: float = field(default_factory=time.time)


class BM25Retriever:
    """Service for BM25 keyword-based retrieval.

    Builds and caches BM25 indexes per user from PostgreSQL chunk records.
    Uses simple whitespace + lowercase tokenization for English text.
    """

    # Index cache TTL in seconds (10 minutes)
    CACHE_TTL = 600

    def __init__(self):
        """Initialize the BM25 retriever with an in-memory index cache."""
        self._indexes: dict[str, BM25Index] = {}

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tokenize text for BM25 indexing.

        Uses lowercase + simple word splitting.
        Filters out single-character tokens and common stop words.

        Args:
            text: Input text to tokenize.

        Returns:
            List of tokens.
        """
        # Lowercase and split on non-alphanumeric characters
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        # Filter very short tokens
        return [t for t in tokens if len(t) > 1]

    def _is_cache_valid(self, index: BM25Index) -> bool:
        """Check if a cached index is still valid.

        Args:
            index: The cached BM25 index.

        Returns:
            True if the index is within TTL.
        """
        return (time.time() - index.created_at) < self.CACHE_TTL

    async def _build_index(
        self,
        db: AsyncSession,
        user_id: str,
        document_ids: Optional[list[str]] = None,
    ) -> Optional[BM25Index]:
        """Build a BM25 index from chunk records in PostgreSQL.

        Args:
            db: Database session.
            user_id: Owner user ID.
            document_ids: Optional filter by document IDs.

        Returns:
            BM25Index or None if no chunks found.
        """
        # Query chunks joined with documents for user scoping
        query = (
            select(Chunk, Document.filename)
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.user_id == user_id)
        )

        if document_ids:
            query = query.where(Chunk.document_id.in_(document_ids))

        query = query.order_by(Chunk.document_id, Chunk.chunk_index)

        result = await db.execute(query)
        rows = list(result.all())

        if not rows:
            logger.info(f"No chunks found for BM25 index: user={user_id}")
            return None

        corpus = []
        chunk_ids = []
        document_ids_list = []
        chunk_contents = []
        chunk_metadatas = []

        for chunk, filename in rows:
            tokenized = self.tokenize(chunk.content)
            if tokenized:  # Skip empty chunks
                corpus.append(chunk.content)
                chunk_ids.append(chunk.id)
                document_ids_list.append(chunk.document_id)
                chunk_contents.append(chunk.content)
                chunk_metadatas.append({
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count,
                    "filename": filename or "",
                    "page_number": str(chunk.page_number) if chunk.page_number else "",
                    "section": chunk.section or "",
                })

        if not corpus:
            logger.info(f"No non-empty chunks for BM25 index: user={user_id}")
            return None

        tokenized_corpus = [self.tokenize(doc) for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)

        index = BM25Index(
            user_id=user_id,
            corpus=corpus,
            tokenized_corpus=tokenized_corpus,
            chunk_ids=chunk_ids,
            document_ids=document_ids_list,
            chunk_contents=chunk_contents,
            chunk_metadatas=chunk_metadatas,
            bm25=bm25,
        )

        logger.info(
            f"Built BM25 index: user={user_id}, chunks={len(corpus)}"
        )

        return index

    async def get_or_build_index(
        self,
        db: AsyncSession,
        user_id: str,
        document_ids: Optional[list[str]] = None,
    ) -> Optional[BM25Index]:
        """Get cached BM25 index or build a new one.

        Args:
            db: Database session.
            user_id: Owner user ID.
            document_ids: Optional filter by document IDs.

        Returns:
            BM25Index or None.
        """
        cache_key = f"{user_id}:{'_'.join(sorted(document_ids)) if document_ids else 'all'}"

        # Check cache
        if cache_key in self._indexes:
            cached = self._indexes[cache_key]
            if self._is_cache_valid(cached):
                logger.debug(f"Using cached BM25 index: user={user_id}")
                return cached
            else:
                del self._indexes[cache_key]

        # Build new index
        index = await self._build_index(db, user_id, document_ids)
        if index is not None:
            self._indexes[cache_key] = index

        return index

    def search(
        self,
        query: str,
        index: BM25Index,
        top_k: int = 10,
    ) -> list[VectorSearchResult]:
        """Search the BM25 index with a query.

        Args:
            query: Search query text.
            index: BM25 index to search.
            top_k: Number of results to return.

        Returns:
            List of search results sorted by BM25 score (descending).
        """
        if not index or not index.corpus:
            return []

        tokenized_query = self.tokenize(query)
        if not tokenized_query:
            return []

        # Get BM25 scores
        scores = index.bm25.get_scores(tokenized_query)

        # Normalize scores to [0, 1]
        max_score = float(np.max(scores)) if len(scores) > 0 else 0.0
        if max_score > 0:
            normalized_scores = scores / max_score
        else:
            normalized_scores = scores

        # Get top-k indices sorted by score descending
        top_indices = np.argsort(normalized_scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(normalized_scores[idx])
            if score <= 0:
                continue  # Skip zero-score results

            results.append(
                VectorSearchResult(
                    chunk_id=index.chunk_ids[idx],
                    document_id=index.document_ids[idx],
                    content=index.chunk_contents[idx],
                    score=score,
                    metadata=index.chunk_metadatas[idx],
                )
            )

        logger.info(
            f"BM25 search: query_len={len(query)}, results={len(results)}, "
            f"top_score={results[0].score:.4f}" if results else
            f"BM25 search: query_len={len(query)}, results=0"
        )

        return results

    def invalidate_cache(self, user_id: str) -> None:
        """Invalidate all cached indexes for a user.

        Call this when documents are added/removed.

        Args:
            user_id: User ID whose cache to invalidate.
        """
        keys_to_remove = [k for k in self._indexes if k.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self._indexes[key]

        if keys_to_remove:
            logger.info(f"Invalidated BM25 cache: user={user_id}, keys={len(keys_to_remove)}")

    def get_cache_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats.
        """
        valid = sum(1 for idx in self._indexes.values() if self._is_cache_valid(idx))
        return {
            "total_indexes": len(self._indexes),
            "valid_indexes": valid,
            "expired_indexes": len(self._indexes) - valid,
        }


# Module-level instance
bm25_retriever = BM25Retriever()
