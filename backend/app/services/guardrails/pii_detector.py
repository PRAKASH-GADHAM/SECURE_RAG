"""PII Detection and redaction.

Detects and optionally redacts:
- Names
- Email addresses
- Phone numbers
- Aadhaar numbers
- PAN numbers
- Passport numbers
- Credit card numbers
- Bank account numbers
- IP addresses
- API keys
- JWT tokens
- Secrets
- Environment variables
"""

import re
from typing import Optional

from app.config import get_settings
from app.services.guardrails.guardrail_models import (
    PIICategory,
    PIIDetection,
    PIIDetectionResult,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class PIIDetector:
    """Detects and optionally redacts PII from text."""

    # Regex patterns for PII detection
    PATTERNS = {
        PIICategory.EMAIL: re.compile(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            re.IGNORECASE,
        ),
        PIICategory.PHONE: re.compile(
            r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
        ),
        PIICategory.AADHAAR: re.compile(
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        ),
        PIICategory.PAN: re.compile(
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        ),
        PIICategory.PASSPORT: re.compile(
            r"\b[A-Z][0-9]{7}\b",
        ),
        PIICategory.CREDIT_CARD: re.compile(
            r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|"
            r"3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|"
            r"6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",
        ),
        PIICategory.BANK_ACCOUNT: re.compile(
            r"\b\d{9,18}\b",
        ),
        PIICategory.IP_ADDRESS: re.compile(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        ),
        PIICategory.API_KEY: re.compile(
            r"(?:api[_-]?key|apikey|api[_-]?secret)[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}['\"]?",
            re.IGNORECASE,
        ),
        PIICategory.JWT_TOKEN: re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
        ),
        PIICategory.SECRET: re.compile(
            r"(?:secret|password|passwd|pwd)[=:]\s*['\"]?[^\s'\"]{8,}['\"]?",
            re.IGNORECASE,
        ),
        PIICategory.ENV_VARIABLE: re.compile(
            r"\b(?:AWS_|AZURE_|GCP_|DATABASE_|REDIS_|SECRET_|API_|TOKEN_|KEY_)[A-Z_]+",
        ),
    }

    def __init__(self):
        """Initialize the PII detector."""
        self._enabled = getattr(settings, "PII_DETECTION_ENABLED", True)
        self._auto_redact = getattr(settings, "PII_AUTO_REDACT", False)
        logger.info(
            "PII detector initialized",
            enabled=self._enabled,
            auto_redact=self._auto_redact,
        )

    def detect(
        self,
        content: str,
        auto_redact: Optional[bool] = None,
    ) -> PIIDetectionResult:
        """Detect PII in content.

        Args:
            content: Text to analyze.
            auto_redact: Override auto-redaction setting.

        Returns:
            PIIDetectionResult with detections and optional redacted content.
        """
        if not self._enabled:
            return PIIDetectionResult(detected=False)

        redact = auto_redact if auto_redact is not None else self._auto_redact
        detections = []
        redacted_content = content

        for category, pattern in self.PATTERNS.items():
            for match in pattern.finditer(content):
                detection = PIIDetection(
                    category=category,
                    start=match.start(),
                    end=match.end(),
                    original=match.group(),
                    redacted=self._get_redacted_text(category, match.group()),
                    confidence=self._calculate_confidence(category, match.group()),
                )
                detections.append(detection)

                if redact:
                    redacted_content = redacted_content.replace(
                        match.group(), detection.redacted
                    )

        # Sort by position (reverse for safe replacement)
        detections.sort(key=lambda d: d.start, reverse=True)

        return PIIDetectionResult(
            detected=len(detections) > 0,
            detections=detections,
            redacted_content=redacted_content if redact else None,
            total_pii_count=len(detections),
        )

    def _get_redacted_text(self, category: PIICategory, text: str) -> str:
        """Generate redacted text for a PII category.

        Args:
            category: PII category.
            text: Original text.

        Returns:
            Redacted text.
        """
        redaction_map = {
            PIICategory.EMAIL: "[EMAIL REDACTED]",
            PIICategory.PHONE: "[PHONE REDACTED]",
            PIICategory.AADHAAR: "[AADHAAR REDACTED]",
            PIICategory.PAN: "[PAN REDACTED]",
            PIICategory.PASSPORT: "[PASSPORT REDACTED]",
            PIICategory.CREDIT_CARD: "[CREDIT CARD REDACTED]",
            PIICategory.BANK_ACCOUNT: "[BANK ACCOUNT REDACTED]",
            PIICategory.IP_ADDRESS: "[IP REDACTED]",
            PIICategory.API_KEY: "[API KEY REDACTED]",
            PIICategory.JWT_TOKEN: "[JWT REDACTED]",
            PIICategory.SECRET: "[SECRET REDACTED]",
            PIICategory.ENV_VARIABLE: "[ENV VAR REDACTED]",
            PIICategory.NAME: "[NAME REDACTED]",
        }

        return redaction_map.get(category, "[REDACTED]")

    def _calculate_confidence(self, category: PIICategory, text: str) -> float:
        """Calculate confidence score for a detection.

        Args:
            category: PII category.
            text: Detected text.

        Returns:
            Confidence score (0.0 to 1.0).
        """
        # Base confidence by category
        base_confidence = {
            PIICategory.EMAIL: 0.95,
            PIICategory.PHONE: 0.85,
            PIICategory.AADHAAR: 0.90,
            PIICategory.PAN: 0.95,
            PIICategory.PASSPORT: 0.80,
            PIICategory.CREDIT_CARD: 0.90,
            PIICategory.BANK_ACCOUNT: 0.70,
            PIICategory.IP_ADDRESS: 0.95,
            PIICategory.API_KEY: 0.85,
            PIICategory.JWT_TOKEN: 0.95,
            PIICategory.SECRET: 0.80,
            PIICategory.ENV_VARIABLE: 0.90,
            PIICategory.NAME: 0.60,
        }

        return base_confidence.get(category, 0.70)

    def is_enabled(self) -> bool:
        """Check if PII detection is enabled.

        Returns:
            True if enabled.
        """
        return self._enabled

    def get_auto_redact(self) -> bool:
        """Get auto-redaction setting.

        Returns:
            True if auto-redaction is enabled.
        """
        return self._auto_redact


# Module-level instance
pii_detector = PIIDetector()
