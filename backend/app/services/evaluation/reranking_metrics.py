"""Reranking metrics calculator.

Implements:
- Pre-reranking vs post-reranking comparison
- Relevance improvement
- Position changes
"""

from typing import Any

from app.utils.logging import get_logger

logger = get_logger(__name__)


class RerankingMetrics:
    """Calculates reranking evaluation metrics."""

    def calculate_improvement(
        self,
        pre_ranked: list[str],
        post_ranked: list[str],
        relevant: list[str],
    ) -> dict[str, Any]:
        """Calculate reranking improvement.

        Args:
            pre_ranked: Document IDs before reranking.
            post_ranked: Document IDs after reranking.
            relevant: List of relevant document IDs.

        Returns:
            Reranking improvement metrics.
        """
        relevant_set = set(relevant)

        # Calculate positions before reranking
        pre_positions = {}
        for i, doc in enumerate(pre_ranked):
            pre_positions[doc] = i

        # Calculate positions after reranking
        post_positions = {}
        for i, doc in enumerate(post_ranked):
            post_positions[doc] = i

        # Calculate position changes for relevant documents
        position_changes = []
        for doc in relevant_set:
            if doc in pre_positions and doc in post_positions:
                change = pre_positions[doc] - post_positions[doc]
                position_changes.append(change)

        # Calculate metrics
        avg_position_change = (
            sum(position_changes) / len(position_changes)
            if position_changes
            else 0.0
        )

        improved_count = sum(1 for c in position_changes if c > 0)
        degraded_count = sum(1 for c in position_changes if c < 0)
        unchanged_count = sum(1 for c in position_changes if c == 0)

        return {
            "avg_position_change": round(avg_position_change, 2),
            "improved_count": improved_count,
            "degraded_count": degraded_count,
            "unchanged_count": unchanged_count,
            "improvement_rate": round(
                improved_count / len(position_changes) if position_changes else 0.0,
                4,
            ),
        }

    def calculate_ndcg_improvement(
        self,
        pre_ranked: list[str],
        post_ranked: list[str],
        relevant: list[str],
        k: int = 10,
    ) -> dict[str, float]:
        """Calculate nDCG improvement from reranking.

        Args:
            pre_ranked: Document IDs before reranking.
            post_ranked: Document IDs after reranking.
            relevant: List of relevant document IDs.
            k: Number of top results to consider.

        Returns:
            nDCG improvement metrics.
        """
        # Calculate nDCG before reranking
        ndcg_before = self._ndcg(pre_ranked, relevant, k)

        # Calculate nDCG after reranking
        ndcg_after = self._ndcg(post_ranked, relevant, k)

        return {
            "ndcg_before": round(ndcg_before, 4),
            "ndcg_after": round(ndcg_after, 4),
            "ndcg_improvement": round(ndcg_after - ndcg_before, 4),
            "improvement_percentage": round(
                ((ndcg_after - ndcg_before) / ndcg_before * 100) if ndcg_before > 0 else 0.0,
                2,
            ),
        }

    def _ndcg(
        self,
        retrieved: list[str],
        relevant: list[str],
        k: int,
    ) -> float:
        """Calculate nDCG.

        Args:
            retrieved: List of retrieved document IDs.
            relevant: List of relevant document IDs.
            k: Number of top results.

        Returns:
            nDCG score.
        """
        if k <= 0 or not retrieved or not relevant:
            return 0.0

        retrieved_at_k = retrieved[:k]
        relevant_set = set(relevant)

        # Calculate DCG
        dcg = 0.0
        for i, doc in enumerate(retrieved_at_k):
            if doc in relevant_set:
                dcg += 1.0 / (i + 1).bit_length()

        # Calculate ideal DCG
        ideal_count = min(len(relevant_set), k)
        idcg = 0.0
        for i in range(ideal_count):
            idcg += 1.0 / (i + 1).bit_length()

        if idcg == 0:
            return 0.0

        return dcg / idcg


# Module-level instance
reranking_metrics = RerankingMetrics()
