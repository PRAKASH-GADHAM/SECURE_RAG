"""Citation metrics calculator.

Implements:
- Citation coverage
- Citation accuracy
- Missing citations
"""

from typing import Any

from app.utils.logging import get_logger

logger = get_logger(__name__)


class CitationMetrics:
    """Calculates citation evaluation metrics."""

    def calculate_coverage(
        self,
        statements: list[str],
        citations: list[str],
    ) -> float:
        """Calculate citation coverage.

        Args:
            statements: List of statements in response.
            citations: List of citations in response.

        Returns:
            Citation coverage (0.0 to 1.0).
        """
        if not statements:
            return 1.0

        # Simple heuristic: check if statements have citations
        cited_count = 0
        for statement in statements:
            if self._has_citation(statement, citations):
                cited_count += 1

        return cited_count / len(statements)

    def count_missing_citations(
        self,
        statements: list[str],
        citations: list[str],
    ) -> dict[str, Any]:
        """Count statements missing citations.

        Args:
            statements: List of statements in response.
            citations: List of citations in response.

        Returns:
            Missing citation metrics.
        """
        total = len(statements)
        missing = 0
        missing_statements = []

        for statement in statements:
            if not self._has_citation(statement, citations):
                missing += 1
                if len(missing_statements) < 5:  # Limit for readability
                    missing_statements.append(statement[:100])

        return {
            "total_statements": total,
            "missing_count": missing,
            "missing_ratio": round(missing / total if total > 0 else 0.0, 4),
            "missing_statements": missing_statements,
        }

    def calculate_accuracy(
        self,
        citations: list[str],
        valid_sources: list[str],
    ) -> float:
        """Calculate citation accuracy.

        Args:
            citations: List of citations in response.
            valid_sources: List of valid source references.

        Returns:
            Citation accuracy (0.0 to 1.0).
        """
        if not citations:
            return 1.0

        valid_set = set(valid_sources)
        valid_count = sum(1 for c in citations if c in valid_set)

        return valid_count / len(citations)

    def calculate_all_metrics(
        self,
        statements: list[str],
        citations: list[str],
        valid_sources: list[str],
    ) -> dict[str, Any]:
        """Calculate all citation metrics.

        Args:
            statements: List of statements in response.
            citations: List of citations in response.
            valid_sources: List of valid source references.

        Returns:
            Dictionary of all metrics.
        """
        coverage = self.calculate_coverage(statements, citations)
        missing = self.count_missing_citations(statements, citations)
        accuracy = self.calculate_accuracy(citations, valid_sources)

        return {
            "coverage": round(coverage, 4),
            "accuracy": round(accuracy, 4),
            "total_citations": len(citations),
            "valid_citations": sum(1 for c in citations if c in set(valid_sources)),
            "missing_statements": missing["missing_count"],
            "missing_ratio": missing["missing_ratio"],
        }

    def _has_citation(self, statement: str, citations: list[str]) -> bool:
        """Check if statement has a citation.

        Args:
            statement: Statement to check.
            citations: List of citations.

        Returns:
            True if statement has citation.
        """
        import re

        # Check for common citation patterns
        citation_patterns = [
            r"\[(?:Source|Document|Doc)\s*(?:\d+|[A-Z])\]",
            r"\[(?:source|document|doc)_[a-z\d]+\]",
            r"\((?:Source|Document|Doc)\s*(?:\d+|[A-Z])\)",
        ]

        for pattern in citation_patterns:
            if re.search(pattern, statement, re.IGNORECASE):
                return True

        return False


# Module-level instance
citation_metrics = CitationMetrics()
