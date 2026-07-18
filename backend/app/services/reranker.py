"""Reranker service.

Provides cross-encoder re-ranking using BAAI/bge-reranker-v2-m3 model.
Uses singleton pattern with lazy loading for efficient model management.

The reranker is completely decoupled from retrieval services to maintain
flexibility for future vector database migrations (Pinecone, Qdrant, Weaviate).
"""

import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.config import get_settings
from app.services.vector_store import VectorSearchResult
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class RerankResult:
    """Result from reranking operation."""

    chunk_id: str
    document_id: str
    content: str
    original_score: float
    rerank_score: float
    metadata: dict
    rank: int


@dataclass
class RerankMetrics:
    """Metrics from reranking operation."""

    total_candidates: int
    reranked_count: int
    filtered_count: int
    rerank_time_ms: int
    avg_score: float
    max_score: float
    min_score: float


class CrossEncoderReranker:
    """Cross-encoder reranker using BAAI/bge-reranker-v2-m3.

    Uses singleton pattern with lazy loading to ensure the model is loaded
    only once during the application's lifetime.

    This service is completely decoupled from retrieval services to support
    future vector database migrations without code changes.
    """

    _instance: Optional["CrossEncoderReranker"] = None
    _model = None

    def __new__(cls) -> "CrossEncoderReranker":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the reranker (only once due to singleton)."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._model_name = settings.RERANKER_MODEL
            self._device = settings.RERANKER_DEVICE
            self._batch_size = settings.RERANK_BATCH_SIZE
            self._score_threshold = settings.RERANK_SCORE_THRESHOLD
            logger.info(
                f"CrossEncoderReranker initialized: model={self._model_name}, "
                f"device={self._device}"
            )

    @property
    def model(self):
        """Get the reranker model (lazy loaded)."""
        if CrossEncoderReranker._model is None:
            logger.info(f"Loading reranker model: {self._model_name}")
            start_time = time.time()

            from sentence_transformers import CrossEncoder
            CrossEncoderReranker._model = CrossEncoder(
                self._model_name,
                device=self._device,
            )

            load_time = time.time() - start_time
            logger.info(f"Reranker model loaded in {load_time:.2f}s")

        return CrossEncoderReranker._model

    @property
    def is_enabled(self) -> bool:
        """Check if reranking is enabled via configuration."""
        return settings.ENABLE_RERANKING

    def rerank(
        self,
        query: str,
        candidates: list[VectorSearchResult],
        top_k: Optional[int] = None,
    ) -> tuple[list[RerankResult], RerankMetrics]:
        """Rerank candidate documents using cross-encoder scoring.

        Args:
            query: User query text.
            candidates: List of candidate documents from retrieval.
            top_k: Number of results to return after reranking.

        Returns:
            Tuple of (reranked results, metrics).
        """
        start_time = time.time()

        if not candidates:
            return [], RerankMetrics(
                total_candidates=0,
                reranked_count=0,
                filtered_count=0,
                rerank_time_ms=0,
                avg_score=0.0,
                max_score=0.0,
                min_score=0.0,
            )

        effective_top_k = top_k or settings.RERANK_TOP_K

        logger.info(
            f"Reranking {len(candidates)} candidates with top_k={effective_top_k}"
        )

        # Prepare query-document pairs
        pairs = [(query, candidate.content) for candidate in candidates]

        # Get cross-encoder scores
        try:
            scores = self.model.predict(
                pairs,
                batch_size=self._batch_size,
                show_progress_bar=False,
            )
            scores = np.array(scores)
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            # Fallback to original scores
            scores = np.array([c.score for c in candidates])

        # Create reranked results with scores
        reranked_results = []
        for i, (candidate, score) in enumerate(zip(candidates, scores)):
            reranked_results.append(
                RerankResult(
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    content=candidate.content,
                    original_score=candidate.score,
                    rerank_score=float(score),
                    metadata={
                        **candidate.metadata,
                        "rerank_score": float(score),
                        "original_score": candidate.score,
                        "rerank_rank": i + 1,
                    },
                    rank=i + 1,
                )
            )

        # Sort by rerank score descending
        reranked_results.sort(key=lambda r: r.rerank_score, reverse=True)

        # Apply score threshold filtering
        if self._score_threshold > 0:
            before_filter = len(reranked_results)
            reranked_results = [
                r for r in reranked_results
                if r.rerank_score >= self._score_threshold
            ]
            filtered_count = before_filter - len(reranked_results)
        else:
            filtered_count = 0

        # Apply top_k limit
        final_results = reranked_results[:effective_top_k]

        # Calculate metrics
        elapsed_ms = int((time.time() - start_time) * 1000)
        scores_array = np.array([r.rerank_score for r in reranked_results]) if reranked_results else np.array([0.0])

        metrics = RerankMetrics(
            total_candidates=len(candidates),
            reranked_count=len(reranked_results),
            filtered_count=filtered_count,
            rerank_time_ms=elapsed_ms,
            avg_score=float(np.mean(scores_array)),
            max_score=float(np.max(scores_array)),
            min_score=float(np.min(scores_array)),
        )

        logger.info(
            f"Reranking completed: candidates={len(candidates)}, "
            f"reranked={len(reranked_results)}, filtered={filtered_count}, "
            f"final={len(final_results)}, time={elapsed_ms}ms"
        )

        return final_results, metrics

    def get_model_info(self) -> dict:
        """Get information about the loaded model.

        Returns:
            Dictionary with model information.
        """
        return {
            "model_name": self._model_name,
            "device": self._device,
            "is_loaded": CrossEncoderReranker._model is not None,
            "batch_size": self._batch_size,
            "score_threshold": self._score_threshold,
        }


# Module-level instance (singleton)
reranker = CrossEncoderReranker()
