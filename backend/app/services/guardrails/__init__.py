"""Guardrails services package.

Provides responsible AI output protection including PII detection,
output moderation, citation validation, and hallucination detection.
"""

from app.services.guardrails.citation_validator import CitationValidator, citation_validator
from app.services.guardrails.guardrail_models import (
    ConfidenceLevel,
    HallucinationResult,
    ModerationCategory,
    ModerationDetection,
    ModerationResult,
    OutputAnalysisResult,
    OutputDecision,
    PIICategory,
    PIIDetection,
    PIIDetectionResult,
    ResponseValidationResult,
)
from app.services.guardrails.output_moderator import OutputModerator, output_moderator
from app.services.guardrails.output_pipeline import OutputPipeline, output_pipeline
from app.services.guardrails.pii_detector import PIIDetector, pii_detector
from app.services.guardrails.response_validator import ResponseValidator, response_validator

__all__ = [
    # Models
    "ConfidenceLevel",
    "HallucinationResult",
    "ModerationCategory",
    "ModerationDetection",
    "ModerationResult",
    "OutputAnalysisResult",
    "OutputDecision",
    "PIICategory",
    "PIIDetection",
    "PIIDetectionResult",
    "ResponseValidationResult",
    # Validators
    "PIIDetector",
    "OutputModerator",
    "CitationValidator",
    "ResponseValidator",
    "OutputPipeline",
    # Instances
    "pii_detector",
    "output_moderator",
    "citation_validator",
    "response_validator",
    "output_pipeline",
]
