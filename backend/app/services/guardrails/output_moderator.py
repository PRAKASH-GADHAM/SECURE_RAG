"""Output moderation for content safety.

Detects:
- Hate speech
- Violence
- Harassment
- Sexual content
- Self-harm content
- Illegal activity
- Malware generation
- Sensitive information leakage
- Prompt leakage
- System prompt leakage
"""

import re
from typing import Optional

from app.config import get_settings
from app.services.guardrails.guardrail_models import (
    ModerationCategory,
    ModerationDetection,
    ModerationResult,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class OutputModerator:
    """Moderates output content for safety and policy compliance."""

    # Moderation patterns by category
    PATTERNS = {
        ModerationCategory.HATE: {
            "patterns": [
                re.compile(r"\b(?:kill|murder|exterminate|eliminate)\s+(?:all|every)\s+\w+", re.IGNORECASE),
                re.compile(r"\b(?:racist|sexist|homophobic|transphobic)\b", re.IGNORECASE),
                re.compile(r"\b(?:supremacy|superior\s+race|inferior\s+race)\b", re.IGNORECASE),
            ],
            "severity": 0.9,
        },
        ModerationCategory.VIOLENCE: {
            "patterns": [
                re.compile(r"\b(?:how\s+to\s+(?:kill|murder|assault|attack))\b", re.IGNORECASE),
                re.compile(r"\b(?:make\s+(?:a\s+)?bomb|explosive\s+device)\b", re.IGNORECASE),
                re.compile(r"\b(?:weapon\s+(?:of|to)\s+(?:mass|kill))\b", re.IGNORECASE),
            ],
            "severity": 0.85,
        },
        ModerationCategory.HARASSMENT: {
            "patterns": [
                re.compile(r"\b(?:you\s+are\s+(?:stupid|idiot|moron|dumb))\b", re.IGNORECASE),
                re.compile(r"\b(?:go\s+(?:kill|die)\s+yourself)\b", re.IGNORECASE),
                re.compile(r"\b(?:dox|doxx)\s+(?:someone|people|them)\b", re.IGNORECASE),
            ],
            "severity": 0.8,
        },
        ModerationCategory.SEXUAL: {
            "patterns": [
                re.compile(r"\b(?:pornography|pornographic|explicit\s+sexual)\b", re.IGNORECASE),
                re.compile(r"\b(?:sex\s+(?:tape|video|chat))\b", re.IGNORECASE),
                re.compile(r"\b(?:nude|naked)\s+(?:photo|image|picture|video)\b", re.IGNORECASE),
            ],
            "severity": 0.75,
        },
        ModerationCategory.SELF_HARM: {
            "patterns": [
                re.compile(r"\b(?:how\s+to\s+(?:commit\s+)?suicide)\b", re.IGNORECASE),
                re.compile(r"\b(?:self[-\s]?harm|cut\s+yourself)\b", re.IGNORECASE),
                re.compile(r"\b(?:overdose|end\s+your\s+life)\b", re.IGNORECASE),
            ],
            "severity": 0.95,
        },
        ModerationCategory.ILLEGAL_ACTIVITY: {
            "patterns": [
                re.compile(r"\b(?:how\s+to\s+(?:hack|steal|fraud|scam|launder))\b", re.IGNORECASE),
                re.compile(r"\b(?:buy\s+(?:drugs|illegal|contraband))\b", re.IGNORECASE),
                re.compile(r"\b(?:counterfeit|forgery|smuggling)\b", re.IGNORECASE),
            ],
            "severity": 0.85,
        },
        ModerationCategory.MALWARE: {
            "patterns": [
                re.compile(r"\b(?:create|write|build)\s+(?:a\s+)?(?:virus|malware|trojan|ransomware)\b", re.IGNORECASE),
                re.compile(r"\b(?:exploit|payload|backdoor)\s+(?:code|tool|script)\b", re.IGNORECASE),
                re.compile(r"\b(?:keylogger|spyware|adware)\b", re.IGNORECASE),
            ],
            "severity": 0.9,
        },
        ModerationCategory.SENSITIVE_INFO: {
            "patterns": [
                re.compile(r"\b(?:password|secret|api[_\s]?key|token)\s*[=:]\s*\S+", re.IGNORECASE),
                re.compile(r"\b(?:confidential|classified|top\s+secret)\b", re.IGNORECASE),
                re.compile(r"\b(?:private\s+(?:key|data|information))\b", re.IGNORECASE),
            ],
            "severity": 0.7,
        },
        ModerationCategory.PROMPT_LEAKAGE: {
            "patterns": [
                re.compile(r"\b(?:my\s+system\s+prompt|the\s+system\s+prompt)\b", re.IGNORECASE),
                re.compile(r"\b(?:instruction[s]?\s+(?:were|was|are|is):)\b", re.IGNORECASE),
                re.compile(r"\b(?:you\s+were\s+(?:told|instructed|programmed)\s+to)\b", re.IGNORECASE),
            ],
            "severity": 0.8,
        },
        ModerationCategory.SYSTEM_PROMPT_LEAKAGE: {
            "patterns": [
                re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
                re.compile(r"INST:.*system", re.IGNORECASE),
                re.compile(r"<\|system\|>.*<\|/system\|>", re.IGNORECASE),
            ],
            "severity": 0.85,
        },
    }

    def __init__(self):
        """Initialize the output moderator."""
        self._enabled = getattr(settings, "OUTPUT_MODERATION_ENABLED", True)
        self._block_on_detection = getattr(settings, "MODERATION_BLOCK_ON_DETECTION", True)
        logger.info(
            "Output moderator initialized",
            enabled=self._enabled,
            block_on_detection=self._block_on_detection,
        )

    def moderate(
        self,
        content: str,
        block_on_detection: Optional[bool] = None,
    ) -> ModerationResult:
        """Moderate output content.

        Args:
            content: Text to moderate.
            block_on_detection: Override block setting.

        Returns:
            ModerationResult with detection results.
        """
        if not self._enabled:
            return ModerationResult(is_safe=True)

        block = block_on_detection if block_on_detection is not None else self._block_on_detection
        detections = []
        max_severity = 0.0

        for category, config in self.PATTERNS.items():
            for pattern in config["patterns"]:
                matches = pattern.findall(content)
                if matches:
                    detection = ModerationDetection(
                        category=category,
                        severity=config["severity"],
                        description=f"Detected {category.value}: {matches[0][:50]}",
                        detected_text=matches[0][:100] if matches else None,
                    )
                    detections.append(detection)
                    max_severity = max(max_severity, config["severity"])

        # Calculate overall risk score
        risk_score = self._calculate_risk_score(detections)

        # Determine if blocked
        blocked = block and risk_score >= 0.7

        # Redact content if needed
        redacted_content = None
        if detections and not blocked:
            redacted_content = self._redact_content(content, detections)

        return ModerationResult(
            is_safe=len(detections) == 0,
            detections=detections,
            risk_score=risk_score,
            blocked=blocked,
            redacted_content=redacted_content,
        )

    def _calculate_risk_score(self, detections: list[ModerationDetection]) -> float:
        """Calculate overall risk score from detections.

        Args:
            detections: List of moderation detections.

        Returns:
            Risk score (0.0 to 1.0).
        """
        if not detections:
            return 0.0

        # Use maximum severity with some averaging
        severities = [d.severity for d in detections]
        max_severity = max(severities)
        avg_severity = sum(severities) / len(severities)

        # Weighted combination
        return 0.7 * max_severity + 0.3 * avg_severity

    def _redact_content(
        self,
        content: str,
        detections: list[ModerationDetection],
    ) -> str:
        """Redact flagged content.

        Args:
            content: Original content.
            detections: Detected issues.

        Returns:
            Redacted content.
        """
        redacted = content

        for detection in detections:
            if detection.detected_text:
                redacted = redacted.replace(
                    detection.detected_text,
                    f"[{detection.category.value.upper()} REDACTED]",
                )

        return redacted

    def is_enabled(self) -> bool:
        """Check if output moderation is enabled.

        Returns:
            True if enabled.
        """
        return self._enabled


# Module-level instance
output_moderator = OutputModerator()
