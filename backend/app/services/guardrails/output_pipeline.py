"""Output protection pipeline orchestrator.

Orchestrates all output protection checks:
- PII detection and redaction
- Output moderation
- Citation validation
- Hallucination detection
- Response validation

This is the single interface that the RAG service should call.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.config import get_settings
from app.services.guardrails.citation_validator import citation_validator
from app.services.guardrails.guardrail_models import (
    ConfidenceLevel,
    HallucinationResult,
    OutputAnalysisResult,
    OutputDecision,
)
from app.services.guardrails.output_moderator import output_moderator
from app.services.guardrails.pii_detector import pii_detector
from app.services.guardrails.response_validator import response_validator
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class OutputPipeline:
    """Orchestrates all output protection checks.

    This is the single interface that the RAG service should call.
    """

    def __init__(self):
        """Initialize the output pipeline."""
        self._enabled = getattr(settings, "OUTPUT_PROTECTION_ENABLED", True)
        self._block_on_moderation = getattr(settings, "MODERATION_BLOCK_ON_DETECTION", True)
        self._auto_redact_pii = getattr(settings, "PII_AUTO_REDACT", False)

        # Load metrics
        self._metrics = {
            "total_responses": 0,
            "responses_blocked": 0,
            "responses_redacted": 0,
            "responses_warning": 0,
            "responses_safe": 0,
            "hallucination_scores": [],
            "citation_coverages": [],
            "confidence_scores": [],
            "pii_detections": 0,
            "moderation_detections": 0,
        }

        logger.info(
            "Output pipeline initialized",
            enabled=self._enabled,
            block_on_moderation=self._block_on_moderation,
            auto_redact_pii=self._auto_redact_pii,
        )

    def analyze(
        self,
        content: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        context: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> OutputAnalysisResult:
        """Analyze output through the full protection pipeline.

        Args:
            content: LLM response to analyze.
            user_id: Optional user ID for tracking.
            request_id: Optional request ID for tracking.
            context: Optional context (retrieved documents) for citation validation.
            metadata: Optional additional metadata.

        Returns:
            OutputAnalysisResult with full analysis.
        """
        if request_id is None:
            request_id = str(uuid.uuid4())

        if not self._enabled:
            return OutputAnalysisResult(
                request_id=request_id,
                user_id=user_id,
                decision=OutputDecision.SAFE,
                original_content=content,
                processed_content=content,
            )

        # Initialize result
        result = OutputAnalysisResult(
            request_id=request_id,
            user_id=user_id,
            original_content=content,
            processed_content=content,
            metadata=metadata or {},
        )

        # Step 1: PII Detection
        pii_result = pii_detector.detect(content, auto_redact=self._auto_redact_pii)
        result.pii_result = pii_result

        if pii_result.detected:
            self._metrics["pii_detections"] += 1
            if pii_result.redacted_content:
                result.processed_content = pii_result.redacted_content
                result.warnings.append(f"PII detected and redacted: {pii_result.total_pii_count} items")

        # Step 2: Output Moderation
        moderation_result = output_moderator.moderate(result.processed_content)
        result.moderation_result = moderation_result

        if not moderation_result.is_safe:
            self._metrics["moderation_detections"] += 1

            if moderation_result.blocked:
                result.decision = OutputDecision.BLOCKED
                result.processed_content = (
                    "I apologize, but I cannot provide a response to this query. "
                    "Please rephrase your question."
                )
                return result
            elif moderation_result.redacted_content:
                result.processed_content = moderation_result.redacted_content
                result.warnings.append(
                    f"Content moderated: {len(moderation_result.detections)} issues found"
                )

        # Step 3: Citation Validation
        citation_result = citation_validator.validate(result.processed_content, context)
        result.citation_result = citation_result

        if citation_result.citation_coverage < 0.3:
            result.warnings.append(
                f"Low citation coverage: {citation_result.citation_coverage:.1%}"
            )

        # Step 4: Hallucination Detection
        hallucination_result = self._detect_hallucination(result.processed_content, context)
        result.hallucination_result = hallucination_result

        if hallucination_result.confidence_level == ConfidenceLevel.LOW:
            result.decision = OutputDecision.WARNING
            result.warnings.append(
                f"Low confidence response: {hallucination_result.confidence_score:.1%}"
            )

        # Step 5: Response Validation
        validation_result = response_validator.validate(result.processed_content)
        result.validation_result = validation_result

        if not validation_result.is_valid:
            result.warnings.extend(validation_result.issues)

            if validation_result.empty_response:
                result.decision = OutputDecision.BLOCKED
                result.processed_content = (
                    "I apologize, but I couldn't generate a response. "
                    "Please try again."
                )
                return result

        # Update metrics
        self._update_metrics(result)

        return result

    def _detect_hallucination(
        self,
        content: str,
        context: Optional[str],
    ) -> HallucinationResult:
        """Detect potential hallucinations in content.

        Args:
            content: Generated content.
            context: Source context.

        Returns:
            HallucinationResult with detection results.
        """
        # Extract statements
        statements = [s.strip() for s in content.split(".") if len(s.strip()) > 10]
        total_statements = len(statements)

        if total_statements == 0:
            return HallucinationResult(
                confidence_level=ConfidenceLevel.HIGH,
                groundedness_score=1.0,
                context_overlap_score=1.0,
                unsupported_statements=0,
                total_statements=0,
                confidence_score=1.0,
            )

        # Check each statement against context
        unsupported = 0
        grounded_count = 0

        if context:
            for statement in statements:
                if self._is_grounded(statement, context):
                    grounded_count += 1
                else:
                    unsupported += 1
        else:
            # Without context, assume all are unsupported
            unsupported = total_statements

        # Calculate scores
        groundedness = grounded_count / total_statements if total_statements > 0 else 0.0
        context_overlap = groundedness  # Simplified

        # Calculate confidence
        confidence_score = groundedness * 0.7 + (1 - unsupported / total_statements) * 0.3

        # Determine confidence level
        if confidence_score >= 0.7:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence_score >= 0.4:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW

        return HallucinationResult(
            confidence_level=confidence_level,
            groundedness_score=groundedness,
            context_overlap_score=context_overlap,
            unsupported_statements=unsupported,
            total_statements=total_statements,
            confidence_score=confidence_score,
        )

    def _is_grounded(self, statement: str, context: str) -> bool:
        """Check if a statement is grounded in context.

        Args:
            statement: Statement to check.
            context: Source context.

        Returns:
            True if statement is grounded.
        """
        # Simple word overlap check
        statement_words = set(statement.lower().split())
        context_words = set(context.lower().split())

        overlap = len(statement_words & context_words)
        total = len(statement_words)

        if total == 0:
            return False

        # Require at least 30% overlap
        return (overlap / total) >= 0.3

    def _update_metrics(self, result: OutputAnalysisResult) -> None:
        """Update pipeline metrics.

        Args:
            result: Analysis result.
        """
        self._metrics["total_responses"] += 1

        if result.decision == OutputDecision.BLOCKED:
            self._metrics["responses_blocked"] += 1
        elif result.decision == OutputDecision.WARNING:
            self._metrics["responses_warning"] += 1
        else:
            self._metrics["responses_safe"] += 1

        if result.pii_result and result.pii_result.detected:
            self._metrics["responses_redacted"] += 1

        if result.hallucination_result:
            self._metrics["hallucination_scores"].append(
                result.hallucination_result.confidence_score
            )

        if result.citation_result:
            self._metrics["citation_coverages"].append(
                result.citation_result.citation_coverage
            )

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics.

        Returns:
            Dictionary with metrics.
        """
        metrics = {
            "total_responses": self._metrics["total_responses"],
            "responses_blocked": self._metrics["responses_blocked"],
            "responses_redacted": self._metrics["responses_redacted"],
            "responses_warning": self._metrics["responses_warning"],
            "responses_safe": self._metrics["responses_safe"],
            "pii_detections": self._metrics["pii_detections"],
            "moderation_detections": self._metrics["moderation_detections"],
        }

        # Calculate averages
        if self._metrics["hallucination_scores"]:
            metrics["average_hallucination_score"] = (
                sum(self._metrics["hallucination_scores"])
                / len(self._metrics["hallucination_scores"])
            )

        if self._metrics["citation_coverages"]:
            metrics["average_citation_coverage"] = (
                sum(self._metrics["citation_coverages"])
                / len(self._metrics["citation_coverages"])
            )

        if self._metrics["confidence_scores"]:
            metrics["average_confidence"] = (
                sum(self._metrics["confidence_scores"])
                / len(self._metrics["confidence_scores"])
            )

        return metrics


# Module-level instance
output_pipeline = OutputPipeline()
