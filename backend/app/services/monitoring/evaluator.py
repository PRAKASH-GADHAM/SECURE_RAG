"""Evaluation orchestrator for system components.

Orchestrates evaluation of:
- Retrieval quality
- Reranking effectiveness
- Hallucination detection
- Citation accuracy
- End-to-end latency
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import get_settings
from app.services.evaluation.citation_metrics import citation_metrics
from app.services.evaluation.hallucination_metrics import hallucination_metrics
from app.services.evaluation.latency_metrics import latency_metrics_calculator
from app.services.evaluation.reranking_metrics import reranking_metrics
from app.services.evaluation.retrieval_metrics import retrieval_metrics
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class EvaluationResult:
    """Result from system evaluation."""

    retrieval: dict[str, float] = field(default_factory=dict)
    reranking: dict[str, Any] = field(default_factory=dict)
    hallucination: dict[str, Any] = field(default_factory=dict)
    citation: dict[str, Any] = field(default_factory=dict)
    latency: dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0


class Evaluator:
    """Evaluates system performance across components."""

    def __init__(self):
        """Initialize evaluator."""
        logger.info("Evaluator initialized")

    def evaluate_retrieval(
        self,
        retrieved: list[str],
        relevant: list[str],
        k: int = 10,
    ) -> dict[str, float]:
        """Evaluate retrieval quality.

        Args:
            retrieved: Retrieved document IDs.
            relevant: Relevant document IDs.
            k: Top-K value.

        Returns:
            Retrieval metrics.
        """
        return retrieval_metrics.calculate_all_metrics(retrieved, relevant, k)

    def evaluate_reranking(
        self,
        pre_ranked: list[str],
        post_ranked: list[str],
        relevant: list[str],
        k: int = 10,
    ) -> dict[str, Any]:
        """Evaluate reranking effectiveness.

        Args:
            pre_ranked: Document IDs before reranking.
            post_ranked: Document IDs after reranking.
            relevant: Relevant document IDs.
            k: Top-K value.

        Returns:
            Reranking metrics.
        """
        improvement = reranking_metrics.calculate_improvement(
            pre_ranked, post_ranked, relevant
        )
        ndcg_improvement = reranking_metrics.calculate_ndcg_improvement(
            pre_ranked, post_ranked, relevant, k
        )

        return {**improvement, **ndcg_improvement}

    def evaluate_hallucination(
        self,
        response: str,
        context: str,
    ) -> dict[str, Any]:
        """Evaluate hallucination.

        Args:
            response: Generated response.
            context: Source context.

        Returns:
            Hallucination metrics.
        """
        return hallucination_metrics.calculate_all_metrics(response, context)

    def evaluate_citation(
        self,
        statements: list[str],
        citations: list[str],
        valid_sources: list[str],
    ) -> dict[str, Any]:
        """Evaluate citation quality.

        Args:
            statements: Statements in response.
            citations: Citations in response.
            valid_sources: Valid source references.

        Returns:
            Citation metrics.
        """
        return citation_metrics.calculate_all_metrics(
            statements, citations, valid_sources
        )

    def evaluate_latency(
        self,
        latencies: dict[str, list[float]],
        sla_threshold_ms: Optional[float] = None,
    ) -> dict[str, Any]:
        """Evaluate latency across components.

        Args:
            latencies: Dictionary of component latencies.
            sla_threshold_ms: Optional SLA threshold.

        Returns:
            Latency metrics.
        """
        results = {}
        for component, values in latencies.items():
            results[component] = latency_metrics_calculator.calculate_percentiles(values)

            if sla_threshold_ms:
                results[component]["sla_compliance"] = (
                    latency_metrics_calculator.calculate_sla_compliance(
                        values, sla_threshold_ms
                    )
                )

        return results

    def evaluate_end_to_end(
        self,
        retrieved: list[str],
        relevant: list[str],
        pre_ranked: list[str],
        post_ranked: list[str],
        response: str,
        context: str,
        statements: list[str],
        citations: list[str],
        valid_sources: list[str],
    ) -> EvaluationResult:
        """Run end-to-end evaluation.

        Args:
            retrieved: Retrieved document IDs.
            relevant: Relevant document IDs.
            pre_ranked: Document IDs before reranking.
            post_ranked: Document IDs after reranking.
            response: Generated response.
            context: Source context.
            statements: Statements in response.
            citations: Citations in response.
            valid_sources: Valid source references.

        Returns:
            Complete evaluation result.
        """
        # Evaluate retrieval
        retrieval = self.evaluate_retrieval(retrieved, relevant)

        # Evaluate reranking
        reranking = self.evaluate_reranking(pre_ranked, post_ranked, relevant)

        # Evaluate hallucination
        hallucination = self.evaluate_hallucination(response, context)

        # Evaluate citation
        citation = self.evaluate_citation(statements, citations, valid_sources)

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            retrieval, reranking, hallucination, citation
        )

        return EvaluationResult(
            retrieval=retrieval,
            reranking=reranking,
            hallucination=hallucination,
            citation=citation,
            overall_score=overall_score,
        )

    def _calculate_overall_score(
        self,
        retrieval: dict[str, float],
        reranking: dict[str, Any],
        hallucination: dict[str, Any],
        citation: dict[str, Any],
    ) -> float:
        """Calculate overall evaluation score.

        Args:
            retrieval: Retrieval metrics.
            reranking: Reranking metrics.
            hallucination: Hallucination metrics.
            citation: Citation metrics.

        Returns:
            Overall score (0.0 to 1.0).
        """
        scores = []

        # Retrieval score (precision@10)
        if "precision_at_10" in retrieval:
            scores.append(retrieval["precision_at_10"])

        # Reranking score (improvement rate)
        if "improvement_rate" in reranking:
            scores.append(reranking["improvement_rate"])

        # Hallucination score (confidence)
        if "confidence_score" in hallucination:
            scores.append(hallucination["confidence_score"])

        # Citation score (coverage)
        if "coverage" in citation:
            scores.append(citation["coverage"])

        if not scores:
            return 0.0

        return sum(scores) / len(scores)


# Module-level instance
evaluator = Evaluator()
