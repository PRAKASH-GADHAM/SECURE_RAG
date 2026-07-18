"""Input validation for security.

Validates user input for:
- Maximum prompt length
- Maximum conversation length
- Dangerous Unicode characters
- Control characters
- Malformed UTF-8
- Suspicious repeated tokens
"""

import re
from typing import Optional

from app.config import get_settings
from app.services.security.security_models import (
    AttackType,
    RiskLevel,
    SecurityCheckResult,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class InputValidator:
    """Validates user input for security concerns."""

    # Dangerous Unicode ranges
    DANGEROUS_UNICODE_RANGES = [
        (0x0000, 0x001F),  # C0 control characters
        (0x007F, 0x009F),  # C1 control characters
        (0x200B, 0x200F),  # Zero-width characters
        (0x2028, 0x2029),  # Line/paragraph separator
        (0x2060, 0x2064),  # Invisible formatters
        (0xFFF0, 0xFFFF),  # Specials
    ]

    # Suspicious repeated token patterns
    REPEATED_TOKEN_PATTERNS = [
        re.compile(r"(.)\1{10,}"),  # Same character 10+ times
        re.compile(r"(.{2,})\1{5,}"),  # Same 2+ char sequence 5+ times
        re.compile(r"(\w+)\s+\1\s+\1"),  # Same word 3+ times consecutively
    ]

    def __init__(self):
        """Initialize the input validator."""
        self._max_prompt_length = getattr(settings, "SECURITY_MAX_PROMPT_LENGTH", 10000)
        self._max_conversation_length = getattr(settings, "SECURITY_MAX_CONVERSATION_LENGTH", 100000)
        logger.info(
            "Input validator initialized",
            max_prompt=self._max_prompt_length,
            max_conversation=self._max_conversation_length,
        )

    def validate(
        self,
        content: str,
        conversation_length: Optional[int] = None,
    ) -> SecurityCheckResult:
        """Validate input content.

        Args:
            content: User input to validate.
            conversation_length: Optional total conversation length.

        Returns:
            SecurityCheckResult with validation results.
        """
        detected_patterns = []
        risk_score = 0.0

        # Check prompt length
        length_risk, length_patterns = self._check_length(content)
        risk_score += length_risk
        detected_patterns.extend(length_patterns)

        # Check conversation length
        if conversation_length is not None:
            conv_risk, conv_patterns = self._check_conversation_length(conversation_length)
            risk_score += conv_risk
            detected_patterns.extend(conv_patterns)

        # Check control characters
        ctrl_risk, ctrl_patterns = self._check_control_characters(content)
        risk_score += ctrl_risk
        detected_patterns.extend(ctrl_patterns)

        # Check dangerous Unicode
        uni_risk, uni_patterns = self._check_dangerous_unicode(content)
        risk_score += uni_risk
        detected_patterns.extend(uni_patterns)

        # Check malformed content
        malformed_risk, malformed_patterns = self._check_malformed_content(content)
        risk_score += malformed_risk
        detected_patterns.extend(malformed_patterns)

        # Check repeated tokens
        repeated_risk, repeated_patterns = self._check_repeated_tokens(content)
        risk_score += repeated_risk
        detected_patterns.extend(repeated_patterns)

        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)

        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)

        # Determine attack type
        attack_type = None
        if detected_patterns:
            if any("length" in p for p in detected_patterns):
                attack_type = AttackType.INPUT_OVERFLOW
            elif any("control" in p for p in detected_patterns):
                attack_type = AttackType.CONTROL_CHARACTERS
            elif any("unicode" in p for p in detected_patterns):
                attack_type = AttackType.UNICODE_ATTACK

        return SecurityCheckResult(
            check_name="input_validation",
            passed=risk_level == RiskLevel.SAFE,
            risk_score=risk_score,
            risk_level=risk_level,
            detected_patterns=detected_patterns,
            attack_type=attack_type,
        )

    def _check_length(self, content: str) -> tuple[float, list[str]]:
        """Check prompt length.

        Args:
            content: Text to check.

        Returns:
            Tuple of (risk_score, detected_patterns).
        """
        detected = []
        risk_score = 0.0

        if len(content) > self._max_prompt_length:
            ratio = len(content) / self._max_prompt_length
            risk_score = min(ratio * 0.5, 0.8)
            detected.append(f"length:{len(content)}/{self._max_prompt_length}")

        return risk_score, detected

    def _check_conversation_length(self, length: int) -> tuple[float, list[str]]:
        """Check total conversation length.

        Args:
            length: Total conversation length.

        Returns:
            Tuple of (risk_score, detected_patterns).
        """
        detected = []
        risk_score = 0.0

        if length > self._max_conversation_length:
            ratio = length / self._max_conversation_length
            risk_score = min(ratio * 0.3, 0.6)
            detected.append(f"conversation_length:{length}/{self._max_conversation_length}")

        return risk_score, detected

    def _check_control_characters(self, content: str) -> tuple[float, list[str]]:
        """Check for control characters.

        Args:
            content: Text to check.

        Returns:
            Tuple of (risk_score, detected_patterns).
        """
        detected = []
        risk_score = 0.0

        control_count = sum(
            1 for c in content if ord(c) < 0x20 or (0x7F <= ord(c) <= 0x9F)
        )

        if control_count > 0:
            # Exclude common control chars (newline, tab, carriage return)
            significant_count = sum(
                1 for c in content
                if ord(c) < 0x20 and c not in ("\n", "\t", "\r")
            ) + sum(
                1 for c in content
                if 0x7F <= ord(c) <= 0x9F
            )

            if significant_count > 0:
                risk_score = min(significant_count * 0.1, 0.5)
                detected.append(f"control_chars:{significant_count}")

        return risk_score, detected

    def _check_dangerous_unicode(self, content: str) -> tuple[float, list[str]]:
        """Check for dangerous Unicode characters.

        Args:
            content: Text to check.

        Returns:
            Tuple of (risk_score, detected_patterns).
        """
        detected = []
        risk_score = 0.0

        dangerous_count = 0
        for char in content:
            code = ord(char)
            for start, end in self.DANGEROUS_UNICODE_RANGES:
                if start <= code <= end:
                    dangerous_count += 1
                    break

        if dangerous_count > 0:
            risk_score = min(dangerous_count * 0.05, 0.4)
            detected.append(f"dangerous_unicode:{dangerous_count}")

        return risk_score, detected

    def _check_malformed_content(self, content: str) -> tuple[float, list[str]]:
        """Check for malformed content.

        Args:
            content: Text to check.

        Returns:
            Tuple of (risk_score, detected_patterns).
        """
        detected = []
        risk_score = 0.0

        # Check for replacement characters (indicates encoding issues)
        replacement_count = content.count("\ufffd")
        if replacement_count > 0:
            risk_score = min(replacement_count * 0.1, 0.3)
            detected.append(f"malformed_utf8:{replacement_count}")

        # Check for excessively long lines (potential buffer overflow)
        lines = content.split("\n")
        long_lines = sum(1 for line in lines if len(line) > 1000)
        if long_lines > 0:
            risk_score += min(long_lines * 0.1, 0.3)
            detected.append(f"long_lines:{long_lines}")

        return risk_score, detected

    def _check_repeated_tokens(self, content: str) -> tuple[float, list[str]]:
        """Check for suspicious repeated tokens.

        Args:
            content: Text to check.

        Returns:
            Tuple of (risk_score, detected_patterns).
        """
        detected = []
        risk_score = 0.0

        for pattern in self.REPEATED_TOKEN_PATTERNS:
            matches = pattern.findall(content)
            if matches:
                for match in matches[:3]:  # Limit to first 3 matches
                    detected.append(f"repeated_token:{str(match)[:30]}")
                risk_score += min(len(matches) * 0.1, 0.3)

        return risk_score, detected

    def sanitize(self, content: str) -> str:
        """Sanitize content by removing dangerous characters.

        Args:
            content: Text to sanitize.

        Returns:
            Sanitized text.
        """
        sanitized = content

        # Remove control characters except newline, tab, carriage return
        sanitized = "".join(
            c for c in sanitized
            if ord(c) >= 0x20 or c in ("\n", "\t", "\r")
        )

        # Remove zero-width characters
        zero_width_chars = [
            "\u200b", "\u200c", "\u200d", "\ufeff", "\u2060", "\u180e"
        ]
        for char in zero_width_chars:
            sanitized = sanitized.replace(char, "")

        # Remove replacement characters
        sanitized = sanitized.replace("\ufffd", "")

        # Collapse excessive whitespace
        sanitized = re.sub(r" {3,}", "  ", sanitized)

        return sanitized

    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from score.

        Args:
            risk_score: Risk score (0.0 to 1.0).

        Returns:
            RiskLevel classification.
        """
        threshold = getattr(settings, "SECURITY_RISK_THRESHOLD", 0.5)

        if risk_score >= threshold * 1.5:
            return RiskLevel.BLOCKED
        elif risk_score >= threshold * 0.7:
            return RiskLevel.SUSPICIOUS
        else:
            return RiskLevel.SAFE


# Module-level instance
input_validator = InputValidator()
