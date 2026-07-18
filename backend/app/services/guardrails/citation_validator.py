"""Citation validation for RAG responses.

Validates that generated responses properly cite sources:
- Tracks supported claims
- Identifies unsupported claims
- Detects missing citations
- Calculates citation coverage percentage
"""

import re
from typing import Optional

from app.config import get_settings
from app.services.guardrails.guardrail_models import (
    CitationCheck,
    CitationValidationResult,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class CitationValidator:
    """Validates citations in generated responses."""

    # Patterns for detecting citations in text
    CITATION_PATTERNS = [
        re.compile(r"\[(?:Source|Document|Doc)\s*(?:\d+|[A-Z])\]", re.IGNORECASE),
        re.compile(r"\[(?:source|document|doc)_[a-z\d]+\]", re.IGNORECASE),
        re.compile(r"\((?:Source|Document|Doc)\s*(?:\d+|[A-Z])\)", re.IGNORECASE),
        re.compile(r"(?:Source|Document|Doc)\s*:\s*\d+", re.IGNORECASE),
        re.compile(r"(?:According|As\s+per)\s+(?:Source|Document|Doc)\s*\d+", re.IGNORECASE),
    ]

    # Patterns for detecting factual claims
    CLAIM_PATTERNS = [
        re.compile(r"(?:is|are|was|were|has|have|had)\s+(?:a|an|the)?\s*\w+", re.IGNORECASE),
        re.compile(r"(?:according|states|shows|indicates|suggests)", re.IGNORECASE),
        re.compile(r"(?:data|evidence|research|study|report)\s+(?:shows|indicates|suggests)", re.IGNORECASE),
        re.compile(r"\d+(?:\.\d+)?\s*(?:%|percent|million|billion|thousand)", re.IGNORECASE),
    ]

    def __init__(self):
        """Initialize the citation validator."""
        self._enabled = getattr(settings, "CITATION_VALIDATION_ENABLED", True)
        self._min_coverage = getattr(settings, "CITATION_MIN_COVERAGE", 0.5)
        logger.info(
            "Citation validator initialized",
            enabled=self._enabled,
            min_coverage=self._min_coverage,
        )

    def validate(
        self,
        content: str,
        context: Optional[str] = None,
    ) -> CitationValidationResult:
        """Validate citations in content.

        Args:
            content: Generated response to validate.
            context: Optional context containing source references.

        Returns:
            CitationValidationResult with validation results.
        """
        if not self._enabled:
            return CitationValidationResult(
                total_statements=0,
                supported_claims=0,
                unsupported_claims=0,
                missing_citations=0,
                citation_coverage=1.0,
            )

        # Extract statements from content
        statements = self._extract_statements(content)
        total_statements = len(statements)

        if total_statements == 0:
            return CitationValidationResult(
                total_statements=0,
                supported_claims=0,
                unsupported_claims=0,
                missing_citations=0,
                citation_coverage=1.0,
            )

        # Check each statement for citations
        checks = []
        supported = 0
        unsupported = 0
        missing = 0

        for statement in statements:
            check = self._check_statement_citation(statement, context)
            checks.append(check)

            if check.has_citation and check.is_supported:
                supported += 1
            elif check.has_citation and not check.is_supported:
                unsupported += 1
            else:
                missing += 1

        # Calculate citation coverage
        coverage = supported / total_statements if total_statements > 0 else 0.0

        return CitationValidationResult(
            total_statements=total_statements,
            supported_claims=supported,
            unsupported_claims=unsupported,
            missing_citations=missing,
            citation_coverage=coverage,
            checks=checks,
        )

    def _extract_statements(self, content: str) -> list[str]:
        """Extract statements from content.

        Args:
            content: Text to extract statements from.

        Returns:
            List of extracted statements.
        """
        # Split by sentences
        sentences = re.split(r'[.!?]+', content)

        # Filter out short or empty statements
        statements = [
            s.strip() for s in sentences
            if len(s.strip()) > 20  # Minimum length for a meaningful statement
        ]

        return statements[:50]  # Limit to prevent excessive processing

    def _check_statement_citation(
        self,
        statement: str,
        context: Optional[str],
    ) -> CitationCheck:
        """Check if a statement has proper citation.

        Args:
            statement: Statement to check.
            context: Optional context for reference.

        Returns:
            CitationCheck with results.
        """
        # Check if statement contains a citation
        has_citation = False
        source_reference = None

        for pattern in self.CITATION_PATTERNS:
            match = pattern.search(statement)
            if match:
                has_citation = True
                source_reference = match.group()
                break

        # Check if statement is a factual claim
        is_factual = self._is_factual_claim(statement)

        # If factual claim without citation, it's missing
        if is_factual and not has_citation:
            return CitationCheck(
                statement=statement[:100],
                has_citation=False,
                source_reference=None,
                is_supported=False,
            )

        # If has citation, check if it's supported by context
        is_supported = False
        if has_citation and context:
            is_supported = self._check_source_support(source_reference, context)

        return CitationCheck(
            statement=statement[:100],
            has_citation=has_citation,
            source_reference=source_reference,
            is_supported=is_supported,
        )

    def _is_factual_claim(self, statement: str) -> bool:
        """Check if statement is a factual claim.

        Args:
            statement: Statement to check.

        Returns:
            True if statement appears to be a factual claim.
        """
        for pattern in self.CLAIM_PATTERNS:
            if pattern.search(statement):
                return True
        return False

    def _check_source_support(
        self,
        source_reference: str,
        context: str,
    ) -> bool:
        """Check if source reference is supported by context.

        Args:
            source_reference: Reference to check.
            context: Context to check against.

        Returns:
            True if source is supported.
        """
        # Simple check - look for the source reference in context
        if source_reference.lower() in context.lower():
            return True

        # Extract source number/name
        source_match = re.search(r"\d+|[A-Z]", source_reference)
        if source_match:
            source_id = source_match.group()
            if source_id in context:
                return True

        return False

    def is_enabled(self) -> bool:
        """Check if citation validation is enabled.

        Returns:
            True if enabled.
        """
        return self._enabled


# Module-level instance
citation_validator = CitationValidator()
