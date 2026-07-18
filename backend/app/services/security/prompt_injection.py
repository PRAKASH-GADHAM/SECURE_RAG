"""Prompt injection detection.

Detects various prompt injection attacks using rule-based patterns
and optional ML classification.

Supports detection of:
- Ignore previous instructions
- System prompt extraction
- Prompt leaking
- Instruction overriding
- Role manipulation
- Context poisoning
- Hidden prompt injection
- Indirect prompt injection from uploaded documents
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


# Rule-based patterns for prompt injection detection
INJECTION_PATTERNS = {
    "ignore_instructions": [
        re.compile(r"ignore\s+(?:previous|all|above|prior)\s+(?:instructions?|prompts?|rules?|guidelines?)", re.IGNORECASE),
        re.compile(r"disregard\s+(?:previous|all|above|prior)\s+(?:instructions?|prompts?|rules?)", re.IGNORECASE),
        re.compile(r"forget\s+(?:previous|all|above|prior)\s+(?:instructions?|prompts?|rules?)", re.IGNORECASE),
        re.compile(r"override\s+(?:previous|all|above|prior)\s+(?:instructions?|prompts?|rules?)", re.IGNORECASE),
        re.compile(r"new\s+instructions?:", re.IGNORECASE),
        re.compile(r"update\s+instructions?:", re.IGNORECASE),
    ],
    "system_prompt_extraction": [
        re.compile(r"reveal\s+(?:your|the|system)\s+(?:prompt|instructions?|rules?|guidelines?)", re.IGNORECASE),
        re.compile(r"what\s+(?:are|is)\s+your\s+(?:system|initial)\s+(?:prompt|instructions?)", re.IGNORECASE),
        re.compile(r"show\s+me\s+your\s+(?:system|initial)\s+(?:prompt|instructions?)", re.IGNORECASE),
        re.compile(r"print\s+your\s+(?:system|initial)\s+(?:prompt|instructions?)", re.IGNORECASE),
        re.compile(r"display\s+your\s+(?:system|initial)\s+(?:prompt|instructions?)", re.IGNORECASE),
        re.compile(r"output\s+your\s+(?:system|initial)\s+(?:prompt|instructions?)", re.IGNORECASE),
    ],
    "prompt_leaking": [
        re.compile(r"repeat\s+(?:the|your)\s+(?:system|initial)\s+(?:prompt|instructions?)", re.IGNORECASE),
        re.compile(r"copy\s+(?:the|your)\s+(?:system|initial)\s+(?:prompt|instructions?)", re.IGNORECASE),
        re.compile(r"echo\s+(?:the|your)\s+(?:system|initial)\s+(?:prompt|instructions?)", re.IGNORECASE),
        re.compile(r"what\s+was\s+(?:the|your)\s+(?:first|initial|original)\s+(?:prompt|message|instruction)", re.IGNORECASE),
    ],
    "role_manipulation": [
        re.compile(r"you\s+are\s+now\s+(?:a|an|the)\s+", re.IGNORECASE),
        re.compile(r"act\s+as\s+(?:if|a|an|the)\s+", re.IGNORECASE),
        re.compile(r"pretend\s+you\s+(?:are|were|have|can)\s+", re.IGNORECASE),
        re.compile(r"roleplay\s+as\s+", re.IGNORECASE),
        re.compile(r"simulate\s+(?:being|a|an)\s+", re.IGNORECASE),
        re.compile(r"from\s+now\s+on\s+you\s+(?:are|will|should)", re.IGNORECASE),
        re.compile(r"switch\s+to\s+(?:a|an|the)\s+\w+\s+(?:mode|persona|role)", re.IGNORECASE),
    ],
    "instruction_overriding": [
        re.compile(r"system\s*:\s*", re.IGNORECASE),
        re.compile(r"<\|system\|>", re.IGNORECASE),
        re.compile(r"\[system\]", re.IGNORECASE),
        re.compile(r"```system", re.IGNORECASE),
        re.compile(r"---\s*system\s*---", re.IGNORECASE),
        re.compile(r"INST:", re.IGNORECASE),
        re.compile(r"Human:", re.IGNORECASE),
        re.compile(r"Assistant:", re.IGNORECASE),
        re.compile(r">>>\s*system", re.IGNORECASE),
    ],
    "context_poisoning": [
        re.compile(r"(?:ignore|disregard|forget)\s+everything", re.IGNORECASE),
        re.compile(r"(?:ignore|disregard|forget)\s+all\s+(?:previous|prior|above)", re.IGNORECASE),
        re.compile(r"start\s+(?:fresh|anew|over)", re.IGNORECASE),
        re.compile(r"reset\s+(?:to|your)\s+default", re.IGNORECASE),
        re.compile(r"clear\s+(?:your|all)\s+(?:memory|context|instructions?)", re.IGNORECASE),
    ],
    "hidden_injection": [
        re.compile(r"\[INST\].*?\[/INST\]", re.IGNORECASE | re.DOTALL),
        re.compile(r"<<SYS>>.*?<</SYS>>", re.IGNORECASE | re.DOTALL),
        re.compile(r"###\s*(?:System|Human|Assistant)\s*:", re.IGNORECASE),
        re.compile(r"<\|im_start\|>", re.IGNORECASE),
        re.compile(r"<\|im_end\|>", re.IGNORECASE),
    ],
    "jailbreak_keywords": [
        re.compile(r"\bDAN\b", re.IGNORECASE),
        re.compile(r"developer\s+mode", re.IGNORECASE),
        re.compile(r"do\s+anything\s+now", re.IGNORECASE),
        re.compile(r"jailbreak", re.IGNORECASE),
        re.compile(r"bypass\s+(?:all|your|the|these)\s+(?:rules?|filters?|restrictions?|limitations?)", re.IGNORECASE),
        re.compile(r"unrestricted\s+(?:mode|ai|assistant)", re.IGNORECASE),
    ],
}


class PromptInjectionDetector:
    """Detects prompt injection attacks using rule-based patterns.

    Provides comprehensive detection of various injection techniques
    including direct and indirect prompt injection.
    """

    def __init__(self):
        """Initialize the prompt injection detector."""
        self._patterns = INJECTION_PATTERNS
        logger.info("Prompt injection detector initialized")

    def detect(
        self,
        content: str,
        context: Optional[str] = None,
    ) -> SecurityCheckResult:
        """Detect prompt injection in content.

        Args:
            content: User input to check.
            context: Optional context (e.g., retrieved documents) to check for indirect injection.

        Returns:
            SecurityCheckResult with detection results.
        """
        detected_patterns = []
        risk_score = 0.0

        # Check direct injection in user content
        for category, patterns in self._patterns.items():
            for pattern in patterns:
                matches = pattern.findall(content)
                if matches:
                    for match in matches:
                        detected_patterns.append(f"{category}:{match[:50]}")
                    risk_score += self._calculate_category_risk(category, len(matches))

        # Check for indirect injection in context
        if context:
            indirect_patterns = [
                self._patterns.get("hidden_injection", []),
                self._patterns.get("instruction_overriding", []),
            ]
            for pattern_group in indirect_patterns:
                for pattern in pattern_group:
                    matches = pattern.findall(context)
                    if matches:
                        for match in matches:
                            detected_patterns.append(f"indirect:{match[:50]}")
                        risk_score += 0.3  # Higher weight for indirect injection

        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)

        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)

        return SecurityCheckResult(
            check_name="prompt_injection",
            passed=risk_level == RiskLevel.SAFE,
            risk_score=risk_score,
            risk_level=risk_level,
            detected_patterns=detected_patterns,
            attack_type=AttackType.PROMPT_INJECTION if detected_patterns else None,
        )

    def _calculate_category_risk(self, category: str, match_count: int) -> float:
        """Calculate risk score contribution from a category.

        Args:
            category: Pattern category name.
            match_count: Number of matches found.

        Returns:
            Risk score contribution.
        """
        # Base weights per category
        weights = {
            "ignore_instructions": 0.4,
            "system_prompt_extraction": 0.5,
            "prompt_leaking": 0.4,
            "role_manipulation": 0.3,
            "instruction_overriding": 0.5,
            "context_poisoning": 0.6,
            "hidden_injection": 0.7,
            "jailbreak_keywords": 0.5,
        }

        base_weight = weights.get(category, 0.3)
        # Increase risk with more matches, but with diminishing returns
        return base_weight * min(match_count, 3)

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

    def get_patterns(self) -> dict[str, list]:
        """Get all detection patterns.

        Returns:
            Dictionary of pattern categories and their patterns.
        """
        return {k: [p.pattern for p in v] for k, v in self._patterns.items()}


# Module-level instance
prompt_injection_detector = PromptInjectionDetector()
