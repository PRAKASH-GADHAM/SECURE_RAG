"""Jailbreak attack detection.

Detects various jailbreak techniques including:
- DAN (Do Anything Now) patterns
- Developer mode jailbreaks
- Roleplay jailbreaks
- Prompt continuation attacks
- Encoding attacks (Base64, ROT13)
- Unicode obfuscation
- Homoglyph attacks
- Invisible characters
- Translation attacks
"""

import base64
import codecs
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


class JailbreakDetector:
    """Detects jailbreak attacks using multiple detection strategies."""

    # DAN patterns
    DAN_PATTERNS = [
        re.compile(r"\bDAN\b.*?(?:mode|version|enable)", re.IGNORECASE),
        re.compile(r"do\s+anything\s+now", re.IGNORECASE),
        re.compile(r"dan\s+(?:1[0-9]|[2-9][0-9])", re.IGNORECASE),
        re.compile(r"jailbreak(?:ed|ing)?\s+(?:mode|version)", re.IGNORECASE),
        re.compile(r"(?:enter|enable|activate)\s+(?:jailbreak|dan|unrestricted)", re.IGNORECASE),
    ]

    # Developer mode patterns
    DEV_MODE_PATTERNS = [
        re.compile(r"developer\s+mode\s+(?:enabled?|on|activated?)", re.IGNORECASE),
        re.compile(r"dev\s+mode", re.IGNORECASE),
        re.compile(r"(?:enable|activate|turn\s+on)\s+developer", re.IGNORECASE),
        re.compile(r"development\s+mode", re.IGNORECASE),
        re.compile(r"debug\s+mode\s+(?:enabled?|on)", re.IGNORECASE),
    ]

    # Roleplay jailbreak patterns
    ROLEPLAY_PATTERNS = [
        re.compile(r"let'?s\s+roleplay\s+(?:as|that|where)", re.IGNORECASE),
        re.compile(r"pretend\s+(?:you|we|that)\s+(?:are|is|have)", re.IGNORECASE),
        re.compile(r"(?:imagine|suppose)\s+(?:you|we|that)\s+(?:are|is|have)", re.IGNORECASE),
        re.compile(r"in\s+(?:this|a)\s+(?:scenario|story|fiction)", re.IGNORECASE),
        re.compile(r"(?:play|acting)\s+as\s+(?:a|an|the)\s+\w+", re.IGNORECASE),
        re.compile(r"you\s+(?:are|play|act)\s+(?:as\s+)?(?:an?\s+)?(?:evil|unrestricted|uncensored)", re.IGNORECASE),
    ]

    # Prompt continuation attacks
    CONTINUATION_PATTERNS = [
        re.compile(r"complete\s+(?:this|the)\s+(?:prompt|sentence|text|story)", re.IGNORECASE),
        re.compile(r"(?:continue|finish)\s+(?:the\s+)?(?:story|text|prompt|following)", re.IGNORECASE),
        re.compile(r"(?:write|generate)\s+(?:more|the\s+rest|continuation)", re.IGNORECASE),
        re.compile(r"and\s+then\s+(?:you|the|he|she)\s+(?:said|did|replied)", re.IGNORECASE),
        re.compile(r"assistant\s*:\s*$", re.IGNORECASE),
    ]

    # Suspicious request patterns
    SUSPICIOUS_REQUEST_PATTERNS = [
        re.compile(r"(?:bypass|circumvent|evade|avoid)\s+(?:all|your|the|these|every)\s+(?:filter|safety|restriction|limitation|rule|guardrail)", re.IGNORECASE),
        re.compile(r"(?:no|without|bypass)\s+(?:filter|restriction|limitation|rule|censorship|moderation)", re.IGNORECASE),
        re.compile(r"(?:unfiltered|unrestricted|uncensored|unmoderated)\s+(?:mode|response|answer|output)", re.IGNORECASE),
        re.compile(r"(?:ignore|disregard|override)\s+(?:your|all|the)\s+(?:safety|content|ethics|moral)", re.IGNORECASE),
        re.compile(r"(?:dangerous|illegal|harmful|unethical|unlawful)\s+(?:content|information|instruction)", re.IGNORECASE),
        re.compile(r"(?:how\s+to|steps\s+to|method\s+to)\s+(?:hack|exploit|attack|steal|destroy|harm|kill|make\s+a\s+bomb)", re.IGNORECASE),
    ]

    def __init__(self):
        """Initialize the jailbreak detector."""
        logger.info("Jailbreak detector initialized")

    def detect(
        self,
        content: str,
        check_encoding: bool = True,
    ) -> SecurityCheckResult:
        """Detect jailbreak attacks in content.

        Args:
            content: User input to check.
            check_encoding: Whether to check for encoding attacks.

        Returns:
            SecurityCheckResult with detection results.
        """
        detected_patterns = []
        risk_score = 0.0
        attack_types = []

        # Check DAN patterns
        dan_risk, dan_patterns = self._check_patterns(
            content, self.DAN_PATTERNS, "dan"
        )
        if dan_patterns:
            detected_patterns.extend(dan_patterns)
            risk_score += dan_risk
            attack_types.append(AttackType.JAILBREAK)

        # Check developer mode patterns
        dev_risk, dev_patterns = self._check_patterns(
            content, self.DEV_MODE_PATTERNS, "dev_mode"
        )
        if dev_patterns:
            detected_patterns.extend(dev_patterns)
            risk_score += dev_risk
            attack_types.append(AttackType.JAILBREAK)

        # Check roleplay jailbreak patterns
        role_risk, role_patterns = self._check_patterns(
            content, self.ROLEPLAY_PATTERNS, "roleplay"
        )
        if role_patterns:
            detected_patterns.extend(role_patterns)
            risk_score += role_risk
            attack_types.append(AttackType.JAILBREAK)

        # Check prompt continuation attacks
        cont_risk, cont_patterns = self._check_patterns(
            content, self.CONTINUATION_PATTERNS, "continuation"
        )
        if cont_patterns:
            detected_patterns.extend(cont_patterns)
            risk_score += cont_risk
            attack_types.append(AttackType.JAILBREAK)

        # Check suspicious request patterns
        susp_risk, susp_patterns = self._check_patterns(
            content, self.SUSPICIOUS_REQUEST_PATTERNS, "suspicious"
        )
        if susp_patterns:
            detected_patterns.extend(susp_patterns)
            risk_score += susp_risk
            attack_types.append(AttackType.JAILBREAK)

        # Check encoding attacks if enabled
        if check_encoding:
            enc_risk, enc_patterns = self._check_encoding_attacks(content)
            if enc_patterns:
                detected_patterns.extend(enc_patterns)
                risk_score += enc_risk
                attack_types.append(AttackType.ENCODING_ATTACK)

        # Check Unicode obfuscation
        uni_risk, uni_patterns = self._check_unicode_attacks(content)
        if uni_patterns:
            detected_patterns.extend(uni_patterns)
            risk_score += uni_risk
            attack_types.append(AttackType.UNICODE_ATTACK)

        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)

        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)

        return SecurityCheckResult(
            check_name="jailbreak_detection",
            passed=risk_level == RiskLevel.SAFE,
            risk_score=risk_score,
            risk_level=risk_level,
            detected_patterns=detected_patterns,
            attack_type=attack_types[0] if attack_types else None,
            details={"attack_types": [at.value for at in attack_types]},
        )

    def _check_patterns(
        self,
        content: str,
        patterns: list[re.Pattern],
        category: str,
    ) -> tuple[float, list[str]]:
        """Check content against a list of patterns.

        Args:
            content: Text to check.
            patterns: List of compiled regex patterns.
            category: Category name for logging.

        Returns:
            Tuple of (risk_score, detected_patterns).
        """
        risk_score = 0.0
        detected = []

        for pattern in patterns:
            matches = pattern.findall(content)
            if matches:
                for match in matches:
                    detected.append(f"{category}:{match[:50]}")
                # Each match contributes 0.2 to risk, max 0.6 per category
                risk_score += min(0.2 * len(matches), 0.6)

        return risk_score, detected

    def _check_encoding_attacks(
        self,
        content: str,
    ) -> tuple[float, list[str]]:
        """Check for Base64 and ROT13 encoding attacks.

        Args:
            content: Text to check.

        Returns:
            Tuple of (risk_score, detected_patterns).
        """
        risk_score = 0.0
        detected = []

        # Check for Base64 encoded content
        base64_pattern = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")
        base64_matches = base64_pattern.findall(content)

        for match in base64_matches:
            try:
                decoded = base64.b64decode(match).decode("utf-8", errors="ignore")
                if self._contains_suspicious_content(decoded):
                    detected.append(f"base64:{match[:30]}...")
                    risk_score += 0.4
            except Exception:
                pass

        # Check for ROT13 encoded content
        rot13_pattern = re.compile(r"\b[A-Za-z]{10,}\b")
        rot13_matches = rot13_pattern.findall(content)

        for match in rot13_matches:
            decoded = codecs.decode(match, "rot_13")
            if self._contains_suspicious_content(decoded):
                detected.append(f"rot13:{match[:30]}")
                risk_score += 0.3

        return min(risk_score, 0.7), detected

    def _check_unicode_attacks(
        self,
        content: str,
    ) -> tuple[float, list[str]]:
        """Check for Unicode obfuscation and homoglyph attacks.

        Args:
            content: Text to check.

        Returns:
            Tuple of (risk_score, detected_patterns).
        """
        risk_score = 0.0
        detected = []

        # Check for invisible characters (zero-width spaces, etc.)
        invisible_chars = [
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\ufeff",  # Zero-width no-break space
            "\u2060",  # Word joiner
            "\u180e",  # Mongolian vowel separator
        ]

        invisible_count = sum(content.count(c) for c in invisible_chars)
        if invisible_count > 5:
            detected.append(f"invisible_chars:{invisible_count}")
            risk_score += 0.3

        # Check for homoglyph characters (Cyrillic lookalikes, etc.)
        homoglyph_map = {
            "а": "a",  # Cyrillic а
            "е": "e",  # Cyrillic е
            "о": "o",  # Cyrillic о
            "р": "p",  # Cyrillic р
            "с": "c",  # Cyrillic с
            "ᴀ": "a",  # Small capital A
            "ʙ": "b",  # Small capital B
        }

        has_homoglyphs = False
        for char in content:
            if char in homoglyph_map:
                has_homoglyphs = True
                break

        if has_homoglyphs:
            detected.append("homoglyph_detected")
            risk_score += 0.3

        # Check for excessive Unicode combining characters
        combining_chars = sum(
            1 for c in content if "\u0300" <= c <= "\u036f"
        )
        if combining_chars > 10:
            detected.append(f"combining_chars:{combining_chars}")
            risk_score += 0.2

        return min(risk_score, 0.5), detected

    def _contains_suspicious_content(self, text: str) -> bool:
        """Check if decoded text contains suspicious content.

        Args:
            text: Decoded text to check.

        Returns:
            True if suspicious content found.
        """
        suspicious_keywords = [
            "hack", "exploit", "inject", "bypass", "override",
            "ignore", "system", "prompt", "admin", "root",
            "password", "secret", "token", "key",
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in suspicious_keywords)

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
jailbreak_detector = JailbreakDetector()
