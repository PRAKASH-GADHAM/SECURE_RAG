"""Prompt classifier for ML-based security.

Provides lightweight ML classification for prompt security analysis.
Uses a simple heuristic-based approach that can be upgraded to
full ML models when available.
"""

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


class PromptClassifier:
    """Lightweight ML-based prompt classifier.

    Uses heuristic scoring that can be upgraded to actual ML models.
    """

    # Suspicious word categories with weights
    CATEGORY_WEIGHTS = {
        "violence": {
            "words": [
                "kill", "murder", "assault", "attack", "harm", "hurt",
                "destroy", "bomb", "weapon", "gun", "knife", "explosive",
            ],
            "weight": 0.6,
        },
        "illegal_activity": {
            "words": [
                "hack", "exploit", "crack", "steal", "fraud", "scam",
                "phishing", "malware", "ransomware", "trojan", "virus",
                "pirate", "smuggle", "launder",
            ],
            "weight": 0.7,
        },
        "personal_info": {
            "words": [
                "password", "secret", "token", "key", "credential",
                "ssn", "social security", "credit card", "bank account",
                "private key", "api key", "access token",
            ],
            "weight": 0.5,
        },
        "manipulation": {
            "words": [
                "ignore", "override", "bypass", "circumvent", "evade",
                "break", "violate", "disobey", "defy", "resist",
            ],
            "weight": 0.4,
        },
        "deception": {
            "words": [
                "pretend", "fake", "false", "lie", "deceive", "trick",
                "mislead", "confuse", "manipulate", "gaslight",
            ],
            "weight": 0.3,
        },
    }

    def __init__(self):
        """Initialize the prompt classifier."""
        logger.info("Prompt classifier initialized")

    def classify(
        self,
        content: str,
        context: Optional[str] = None,
    ) -> SecurityCheckResult:
        """Classify content using heuristic scoring.

        Args:
            content: User input to classify.
            context: Optional context for analysis.

        Returns:
            SecurityCheckResult with classification results.
        """
        detected_patterns = []
        risk_score = 0.0

        # Analyze content by categories
        content_lower = content.lower()

        for category, config in self.CATEGORY_WEIGHTS.items():
            matches = [
                word for word in config["words"]
                if word in content_lower
            ]
            if matches:
                category_risk = config["weight"] * min(len(matches) / 3, 1.0)
                risk_score += category_risk
                detected_patterns.extend(
                    [f"{category}:{word}" for word in matches[:3]]
                )

        # Analyze context if provided
        if context:
            context_lower = context.lower()
            for category, config in self.CATEGORY_WEIGHTS.items():
                matches = [
                    word for word in config["words"]
                    if word in context_lower
                ]
                if matches:
                    # Context contributes less than direct content
                    risk_score += config["weight"] * 0.3 * min(len(matches) / 3, 1.0)
                    detected_patterns.extend(
                        [f"context_{category}:{word}" for word in matches[:2]]
                    )

        # Check for sentiment indicators
        sentiment_risk = self._analyze_sentiment(content)
        risk_score += sentiment_risk

        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)

        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)

        # Determine attack type
        attack_type = None
        if detected_patterns:
            if any("illegal_activity" in p for p in detected_patterns):
                attack_type = AttackType.JAILBREAK
            elif any("manipulation" in p for p in detected_patterns):
                attack_type = AttackType.PROMPT_INJECTION
            else:
                attack_type = AttackType.UNKNOWN

        return SecurityCheckResult(
            check_name="prompt_classifier",
            passed=risk_level == RiskLevel.SAFE,
            risk_score=risk_score,
            risk_level=risk_level,
            detected_patterns=detected_patterns,
            attack_type=attack_type,
        )

    def _analyze_sentiment(self, content: str) -> float:
        """Analyze content sentiment for risk indicators.

        Args:
            content: Text to analyze.

        Returns:
            Risk score from sentiment analysis.
        """
        risk_score = 0.0

        # Check for aggressive language
        aggressive_patterns = [
            "!",  # Multiple exclamation marks
            "ALL CAPS",  # Shouting
        ]

        # Count exclamation marks
        excl_count = content.count("!")
        if excl_count > 3:
            risk_score += 0.1

        # Check for all caps (excluding short words)
        words = content.split()
        if len(words) > 5:
            caps_words = sum(
                1 for w in words
                if w.isupper() and len(w) > 2
            )
            if caps_words / len(words) > 0.5:
                risk_score += 0.1

        return min(risk_score, 0.2)

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
prompt_classifier = PromptClassifier()
