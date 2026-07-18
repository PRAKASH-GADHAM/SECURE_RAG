"""Retrieval metrics calculator.

Implements:
- Precision@K
- Recall@K
- MRR (Mean Reciprocal Rank)
- nDCG (Normalized Discounted Cumulative Gain)
"""

from typing import Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


class RetrievalMetrics:
    """Calculates retrieval evaluation metrics."""

    def precision_at_k(
        self,
        retrieved: list[str],
        relevant: list[str],
        k: int,
    ) -> float:
        """Calculate Precision@K.

        Args:
            retrieved: List of retrieved document IDs.
            relevant: List of relevant document IDs.
            k: Number of top results to consider.

        Returns:
            Precision@K score.
        """
        if k <= 0 or not retrieved:
            return 0.0

        retrieved_at_k = retrieved[:k]
        relevant_set = set(relevant)

        hits = sum(1 for doc in retrieved_at_k if doc in relevant_set)
        return hits / k

    def recall_at_k(
        self,
        retrieved: list[str],
        relevant: list[str],
        k: int,
    ) -> float:
        """Calculate Recall@K.

        Args:
            retrieved: List of retrieved document IDs.
            relevant: List of relevant document IDs.
            k: Number of top results to consider.

        Returns:
            Recall@K score.
        """
        if k <= 0 or not relevant:
            return 0.0

        retrieved_at_k = retrieved[:k]
        relevant_set = set(relevant)

        hits = sum(1 for doc in retrieved_at_k if doc in relevant_set)
        return hits / len(relevant)

    def mrr(
        self,
        retrieved: list[str],
        relevant: list[str],
    ) -> float:
        """Calculate Mean Reciprocal Rank.

        Args:
            retrieved: List of retrieved document IDs.
            relevant: List of relevant document IDs.

        Returns:
            MRR score.
        """
        if not retrieved or not relevant:
            return 0.0

        relevant_set = set(relevant)

        for i, doc in enumerate(retrieved):
            if doc in relevant_set:
                return 1.0 / (i + 1)

        return 0.0

    def ndcg_at_k(
        self,
        retrieved: list[str],
        relevant: list[str],
        k: int,
    ) -> float:
        """Calculate nDCG@K.

        Args:
            retrieved: List of retrieved document IDs.
            relevant: List of relevant document IDs.
            k: Number of top results to consider.

        Returns:
            nDCG@K score.
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
        ideal_retrieved = list(relevant_set)[:k]
        idcg = 0.0
        for i in range(len(ideal_retrieved)):
            idcg += 1.0 / (i + 1).bit_length()

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def calculate_all_metrics(
        self,
        retrieved: list[str],
        relevant: list[str],
        k: int = 10,
    ) -> dict[str, float]:
        """Calculate all retrieval metrics.

        Args:
            retrieved: List of retrieved document IDs.
            relevant: List of relevant document IDs.
            k: Number of top results to consider.

        Returns:
            Dictionary of all metrics.
        """
        return {
            f"precision_at_{k}": self.precision_at_k(retrieved, relevant, k),
            f"recall_at_{k}": self.recall_at_k(retrieved, relevant, k),
            "mrr": self.mrr(retrieved, relevant),
            f"ndcg_at_{k}": self.ndcg_at_k(retrieved, relevant, k),
        }


# Module-level instance
retrieval_metrics = RetrievalMetrics()
