"""Hallucination metrics calculator.

Implements:
- Groundedness scoring
- Context overlap analysis
- Unsupported statement detection
- Confidence scoring
"""

from typing import Any, Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


class HallucinationMetrics:
    """Calculates hallucination evaluation metrics."""

    def calculate_groundedness(
        self,
        response: str,
        context: str,
    ) -> float:
        """Calculate groundedness score.

        Args:
            response: Generated response.
            context: Source context.

        Returns:
            Groundedness score (0.0 to 1.0).
        """
        if not response or not context:
            return 0.0

        # Extract sentences from response
        sentences = [s.strip() for s in response.split(".") if len(s.strip()) > 10]

        if not sentences:
            return 0.0

        grounded_count = 0
        for sentence in sentences:
            if self._is_grounded(sentence, context):
                grounded_count += 1

        return grounded_count / len(sentences)

    def calculate_context_overlap(
        self,
        response: str,
        context: str,
    ) -> float:
        """Calculate context overlap score.

        Args:
            response: Generated response.
            context: Source context.

        Returns:
            Context overlap score (0.0 to 1.0).
        """
        if not response or not context:
            return 0.0

        response_words = set(response.lower().split())
        context_words = set(context.lower().split())

        overlap = len(response_words & context_words)
        total = len(response_words)

        if total == 0:
            return 0.0

        return overlap / total

    def count_unsupported_statements(
        self,
        response: str,
        context: str,
    ) -> dict[str, Any]:
        """Count unsupported statements.

        Args:
            response: Generated response.
            context: Source context.

        Returns:
            Unsupported statement metrics.
        """
        if not response:
            return {
                "total_statements": 0,
                "unsupported_count": 0,
                "unsupported_ratio": 0.0,
            }

        sentences = [s.strip() for s in response.split(".") if len(s.strip()) > 10]
        total = len(sentences)

        unsupported = 0
        for sentence in sentences:
            if not self._is_grounded(sentence, context):
                unsupported += 1

        return {
            "total_statements": total,
            "unsupported_count": unsupported,
            "unsupported_ratio": round(unsupported / total if total > 0 else 0.0, 4),
        }

    def calculate_confidence_score(
        self,
        groundedness: float,
        context_overlap: float,
        unsupported_ratio: float,
    ) -> float:
        """Calculate overall confidence score.

        Args:
            groundedness: Groundedness score.
            context_overlap: Context overlap score.
            unsupported_ratio: Unsupported statement ratio.

        Returns:
            Confidence score (0.0 to 1.0).
        """
        # Weighted combination
        confidence = (
            groundedness * 0.5
            + context_overlap * 0.3
            + (1 - unsupported_ratio) * 0.2
        )

        return max(0.0, min(1.0, confidence))

    def get_confidence_level(self, confidence: float) -> str:
        """Get confidence level from score.

        Args:
            confidence: Confidence score.

        Returns:
            Confidence level (LOW, MEDIUM, HIGH).
        """
        if confidence >= 0.7:
            return "HIGH"
        elif confidence >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"

    def calculate_all_metrics(
        self,
        response: str,
        context: str,
    ) -> dict[str, Any]:
        """Calculate all hallucination metrics.

        Args:
            response: Generated response.
            context: Source context.

        Returns:
            Dictionary of all metrics.
        """
        groundedness = self.calculate_groundedness(response, context)
        context_overlap = self.calculate_context_overlap(response, context)
        unsupported = self.count_unsupported_statements(response, context)

        confidence = self.calculate_confidence_score(
            groundedness, context_overlap, unsupported["unsupported_ratio"]
        )

        return {
            "groundedness": round(groundedness, 4),
            "context_overlap": round(context_overlap, 4),
            "unsupported_statements": unsupported["unsupported_count"],
            "total_statements": unsupported["total_statements"],
            "unsupported_ratio": unsupported["unsupported_ratio"],
            "confidence_score": round(confidence, 4),
            "confidence_level": self.get_confidence_level(confidence),
        }

    def _is_grounded(self, statement: str, context: str) -> bool:
        """Check if a statement is grounded in context.

        Args:
            statement: Statement to check.
            context: Source context.

        Returns:
            True if grounded.
        """
        statement_words = set(statement.lower().split())
        context_words = set(context.lower().split())

        overlap = len(statement_words & context_words)
        total = len(statement_words)

        if total == 0:
            return False

        return (overlap / total) >= 0.3


# Module-level instance
hallucination_metrics = HallucinationMetrics()
