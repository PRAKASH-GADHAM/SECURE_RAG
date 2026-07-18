"""Guardrail data models.

Defines data structures for output protection, PII detection,
moderation, citation validation, and hallucination detection.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class OutputDecision(str, Enum):
    """Output decision classification."""

    SAFE = "safe"
    WARNING = "warning"
    BLOCKED = "blocked"


class PIICategory(str, Enum):
    """Categories of PII detected."""

    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    AADHAAR = "aadhaar"
    PAN = "pan"
    PASSPORT = "passport"
    CREDIT_CARD = "credit_card"
    BANK_ACCOUNT = "bank_account"
    IP_ADDRESS = "ip_address"
    API_KEY = "api_key"
    JWT_TOKEN = "jwt_token"
    SECRET = "secret"
    ENV_VARIABLE = "env_variable"


class ModerationCategory(str, Enum):
    """Categories of content moderation."""

    HATE = "hate"
    VIOLENCE = "violence"
    HARASSMENT = "harassment"
    SEXUAL = "sexual"
    SELF_HARM = "self_harm"
    ILLEGAL_ACTIVITY = "illegal_activity"
    MALWARE = "malware"
    SENSITIVE_INFO = "sensitive_info"
    PROMPT_LEAKAGE = "prompt_leakage"
    SYSTEM_PROMPT_LEAKAGE = "system_prompt_leakage"


class ConfidenceLevel(str, Enum):
    """Confidence levels for hallucination detection."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class PIIDetection:
    """Single PII detection result."""

    category: PIICategory
    start: int
    end: int
    original: str
    redacted: str
    confidence: float


@dataclass
class PIIDetectionResult:
    """Result from PII detection."""

    detected: bool
    detections: list[PIIDetection] = field(default_factory=list)
    redacted_content: Optional[str] = None
    total_pii_count: int = 0


@dataclass
class ModerationDetection:
    """Single moderation detection result."""

    category: ModerationCategory
    severity: float  # 0.0 to 1.0
    description: str
    detected_text: Optional[str] = None


@dataclass
class ModerationResult:
    """Result from output moderation."""

    is_safe: bool
    detections: list[ModerationDetection] = field(default_factory=list)
    risk_score: float = 0.0
    blocked: bool = False
    redacted_content: Optional[str] = None


@dataclass
class CitationCheck:
    """Single citation check result."""

    statement: str
    has_citation: bool
    source_reference: Optional[str] = None
    is_supported: bool = False


@dataclass
class CitationValidationResult:
    """Result from citation validation."""

    total_statements: int
    supported_claims: int
    unsupported_claims: int
    missing_citations: int
    citation_coverage: float  # 0.0 to 1.0
    checks: list[CitationCheck] = field(default_factory=list)


@dataclass
class HallucinationResult:
    """Result from hallucination detection."""

    confidence_level: ConfidenceLevel
    groundedness_score: float  # 0.0 to 1.0
    context_overlap_score: float  # 0.0 to 1.0
    unsupported_statements: int
    total_statements: int
    confidence_score: float  # 0.0 to 1.0


@dataclass
class ResponseValidationResult:
    """Result from response validation."""

    is_valid: bool
    issues: list[str] = field(default_factory=list)
    max_length_exceeded: bool = False
    empty_response: bool = False
    repeated_paragraphs: bool = False
    malformed_markdown: bool = False


@dataclass
class OutputAnalysisResult:
    """Complete output analysis result."""

    request_id: str
    user_id: Optional[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decision: OutputDecision = OutputDecision.SAFE
    pii_result: Optional[PIIDetectionResult] = None
    moderation_result: Optional[ModerationResult] = None
    citation_result: Optional[CitationValidationResult] = None
    hallucination_result: Optional[HallucinationResult] = None
    validation_result: Optional[ResponseValidationResult] = None
    original_content: str = ""
    processed_content: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailMetrics:
    """Guardrail metrics snapshot."""

    total_responses: int = 0
    responses_blocked: int = 0
    responses_redacted: int = 0
    responses_warning: int = 0
    responses_safe: int = 0
    hallucination_score: float = 0.0
    citation_coverage: float = 0.0
    average_confidence: float = 0.0
    pii_detections: int = 0
    moderation_detections: int = 0
