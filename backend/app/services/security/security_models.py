"""Security data models.

Defines data structures for security analysis results,
risk levels, and audit logging.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class RiskLevel(str, Enum):
    """Risk level classification."""

    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


class AttackType(str, Enum):
    """Types of attacks detected."""

    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    ENCODING_ATTACK = "encoding_attack"
    UNICODE_ATTACK = "unicode_attack"
    INPUT_OVERFLOW = "input_overflow"
    CONTROL_CHARACTERS = "control_characters"
    HOMOGLYPH_ATTACK = "homoglyph_attack"
    BASE64_INJECTION = "base64_injection"
    ROT13_ATTACK = "rot13_attack"
    TRANSLATION_ATTACK = "translation_attack"
    ROLE_MANIPULATION = "role_manipulation"
    CONTEXT_POISONING = "context_poisoning"
    UNKNOWN = "unknown"


class SecurityAction(str, Enum):
    """Actions taken by the security pipeline."""

    ALLOW = "allow"
    SANITIZE = "sanitize"
    LOG = "log"
    BLOCK = "block"
    CHALLENGE = "challenge"


@dataclass
class SecurityCheckResult:
    """Result from a single security check."""

    check_name: str
    passed: bool
    risk_score: float  # 0.0 to 1.0
    risk_level: RiskLevel
    detected_patterns: list[str] = field(default_factory=list)
    attack_type: Optional[AttackType] = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAnalysisResult:
    """Complete security analysis result."""

    request_id: str
    user_id: Optional[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.SAFE
    detected_patterns: list[str] = field(default_factory=list)
    attack_types: list[AttackType] = field(default_factory=list)
    recommended_action: SecurityAction = SecurityAction.ALLOW
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    sanitized_content: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAuditLog:
    """Structured security audit log entry."""

    request_id: str
    user_id: Optional[str]
    timestamp: datetime
    risk_score: float
    risk_level: str
    detected_patterns: list[str]
    action_taken: str
    attack_types: list[str]
    # Never log the original prompt
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityMetrics:
    """Security metrics snapshot."""

    total_requests: int = 0
    blocked_requests: int = 0
    flagged_requests: int = 0
    safe_requests: int = 0
    false_positive_counter: int = 0
    average_risk_score: float = 0.0
    attack_types_detected: dict[str, int] = field(default_factory=dict)
