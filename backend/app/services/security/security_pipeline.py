"""Security pipeline orchestrator.

Orchestrates all security checks and makes final decisions.
This is the only interface the RAG service should call.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.config import get_settings
from app.services.security.input_validator import input_validator
from app.services.security.jailbreak_detector import jailbreak_detector
from app.services.security.prompt_classifier import prompt_classifier
from app.services.security.prompt_injection import prompt_injection_detector
from app.services.security.security_models import (
    AttackType,
    RiskLevel,
    SecurityAction,
    SecurityAnalysisResult,
    SecurityAuditLog,
    SecurityCheckResult,
    SecurityMetrics,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SecurityPipeline:
    """Orchestrates all security checks and makes final decisions.

    This is the single interface that the RAG service should call.
    """

    def __init__(self):
        """Initialize the security pipeline."""
        self._metrics = SecurityMetrics()
        self._audit_logs: list[SecurityAuditLog] = []
        self._max_audit_logs = 10000  # Keep last N logs in memory

        # Load configuration
        self._injection_enabled = getattr(settings, "PROMPT_INJECTION_ENABLED", True)
        self._jailbreak_enabled = getattr(settings, "JAILBREAK_DETECTION_ENABLED", True)
        self._risk_threshold = getattr(settings, "SECURITY_RISK_THRESHOLD", 0.5)
        self._block_high_risk = getattr(settings, "BLOCK_HIGH_RISK", True)
        self._allow_admin_bypass = getattr(settings, "ALLOW_ADMIN_BYPASS", False)

        logger.info(
            "Security pipeline initialized",
            injection_enabled=self._injection_enabled,
            jailbreak_enabled=self._jailbreak_enabled,
            risk_threshold=self._risk_threshold,
            block_high_risk=self._block_high_risk,
        )

    def analyze(
        self,
        content: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        context: Optional[str] = None,
        conversation_length: Optional[int] = None,
        is_admin: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> SecurityAnalysisResult:
        """Analyze content through the full security pipeline.

        Args:
            content: User input to analyze.
            user_id: Optional user ID for audit logging.
            request_id: Optional request ID for tracking.
            context: Optional context (retrieved documents).
            conversation_length: Optional total conversation length.
            is_admin: Whether the user is an admin (may bypass if configured).
            metadata: Optional additional metadata.

        Returns:
            SecurityAnalysisResult with full analysis.
        """
        if request_id is None:
            request_id = str(uuid.uuid4())

        # Check admin bypass
        if is_admin and self._allow_admin_bypass:
            logger.info("Admin bypass enabled, skipping security checks", user_id=user_id)
            return SecurityAnalysisResult(
                request_id=request_id,
                user_id=user_id,
                risk_score=0.0,
                risk_level=RiskLevel.SAFE,
                recommended_action=SecurityAction.ALLOW,
                metadata={"admin_bypass": True},
            )

        checks_passed = []
        checks_failed = []
        all_patterns = []
        all_attack_types = []
        max_risk_score = 0.0

        # Run input validation (always enabled)
        validation_result = input_validator.validate(content, conversation_length)
        self._process_check_result(
            validation_result,
            checks_passed,
            checks_failed,
            all_patterns,
            all_attack_types,
        )
        max_risk_score = max(max_risk_score, validation_result.risk_score)

        # Run prompt injection detection
        if self._injection_enabled:
            injection_result = prompt_injection_detector.detect(content, context)
            self._process_check_result(
                injection_result,
                checks_passed,
                checks_failed,
                all_patterns,
                all_attack_types,
            )
            max_risk_score = max(max_risk_score, injection_result.risk_score)

        # Run jailbreak detection
        if self._jailbreak_enabled:
            jailbreak_result = jailbreak_detector.detect(content)
            self._process_check_result(
                jailbreak_result,
                checks_passed,
                checks_failed,
                all_patterns,
                all_attack_types,
            )
            max_risk_score = max(max_risk_score, jailbreak_result.risk_score)

        # Run prompt classification
        classification_result = prompt_classifier.classify(content, context)
        self._process_check_result(
            classification_result,
            checks_passed,
            checks_failed,
            all_patterns,
            all_attack_types,
        )
        max_risk_score = max(max_risk_score, classification_result.risk_score)

        # Calculate overall risk score (weighted average)
        overall_risk_score = self._calculate_overall_risk(
            validation_result.risk_score,
            injection_result.risk_score if self._injection_enabled else 0.0,
            jailbreak_result.risk_score if self._jailbreak_enabled else 0.0,
            classification_result.risk_score,
        )

        # Determine overall risk level
        overall_risk_level = self._determine_overall_risk_level(overall_risk_score)

        # Determine recommended action
        recommended_action = self._determine_action(overall_risk_level)

        # Create result
        result = SecurityAnalysisResult(
            request_id=request_id,
            user_id=user_id,
            risk_score=overall_risk_score,
            risk_level=overall_risk_level,
            detected_patterns=all_patterns,
            attack_types=list(set(all_attack_types)),
            recommended_action=recommended_action,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            metadata=metadata or {},
        )

        # Update metrics
        self._update_metrics(result)

        # Create audit log (never log the original prompt)
        audit_log = SecurityAuditLog(
            request_id=request_id,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            risk_score=overall_risk_score,
            risk_level=overall_risk_level.value,
            detected_patterns=all_patterns,
            action_taken=recommended_action.value,
            attack_types=[at.value for at in all_attack_types],
        )
        self._add_audit_log(audit_log)

        return result

    def _process_check_result(
        self,
        result: SecurityCheckResult,
        checks_passed: list[str],
        checks_failed: list[str],
        all_patterns: list[str],
        all_attack_types: list[AttackType],
    ) -> None:
        """Process a single check result.

        Args:
            result: Check result to process.
            checks_passed: List to append passed checks to.
            checks_failed: List to append failed checks to.
            all_patterns: List to append detected patterns to.
            all_attack_types: List to append attack types to.
        """
        if result.passed:
            checks_passed.append(result.check_name)
        else:
            checks_failed.append(result.check_name)

        all_patterns.extend(result.detected_patterns)
        if result.attack_type:
            all_attack_types.append(result.attack_type)

    def _calculate_overall_risk(
        self,
        validation_risk: float,
        injection_risk: float,
        jailbreak_risk: float,
        classification_risk: float,
    ) -> float:
        """Calculate overall risk score.

        Args:
            validation_risk: Risk from input validation.
            injection_risk: Risk from injection detection.
            jailbreak_risk: Risk from jailbreak detection.
            classification_risk: Risk from prompt classification.

        Returns:
            Overall risk score (0.0 to 1.0).
        """
        # Weighted average with emphasis on injection and jailbreak
        weights = {
            "validation": 0.15,
            "injection": 0.35,
            "jailbreak": 0.35,
            "classification": 0.15,
        }

        overall = (
            validation_risk * weights["validation"]
            + injection_risk * weights["injection"]
            + jailbreak_risk * weights["jailbreak"]
            + classification_risk * weights["classification"]
        )

        return min(overall, 1.0)

    def _determine_overall_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine overall risk level.

        Args:
            risk_score: Overall risk score.

        Returns:
            RiskLevel classification.
        """
        if risk_score >= self._risk_threshold * 1.5:
            return RiskLevel.BLOCKED
        elif risk_score >= self._risk_threshold * 0.7:
            return RiskLevel.SUSPICIOUS
        else:
            return RiskLevel.SAFE

    def _determine_action(self, risk_level: RiskLevel) -> SecurityAction:
        """Determine action based on risk level.

        Args:
            risk_level: Overall risk level.

        Returns:
            SecurityAction to take.
        """
        if risk_level == RiskLevel.BLOCKED:
            if self._block_high_risk:
                return SecurityAction.BLOCK
            else:
                return SecurityAction.LOG
        elif risk_level == RiskLevel.SUSPICIOUS:
            return SecurityAction.SANITIZE
        else:
            return SecurityAction.ALLOW

    def _update_metrics(self, result: SecurityAnalysisResult) -> None:
        """Update security metrics.

        Args:
            result: Analysis result to use for metrics.
        """
        self._metrics.total_requests += 1

        if result.risk_level == RiskLevel.BLOCKED:
            self._metrics.blocked_requests += 1
        elif result.risk_level == RiskLevel.SUSPICIOUS:
            self._metrics.flagged_requests += 1
        else:
            self._metrics.safe_requests += 1

        # Update average risk score
        total = self._metrics.total_requests
        current_avg = self._metrics.average_risk_score
        self._metrics.average_risk_score = (
            (current_avg * (total - 1) + result.risk_score) / total
        )

        # Update attack types
        for attack_type in result.attack_types:
            type_name = attack_type.value
            if type_name not in self._metrics.attack_types_detected:
                self._metrics.attack_types_detected[type_name] = 0
            self._metrics.attack_types_detected[type_name] += 1

    def _add_audit_log(self, log: SecurityAuditLog) -> None:
        """Add audit log to memory buffer.

        Args:
            log: Audit log to add.
        """
        self._audit_logs.append(log)

        # Keep only last N logs
        if len(self._audit_logs) > self._max_audit_logs:
            self._audit_logs = self._audit_logs[-self._max_audit_logs:]

    def get_metrics(self) -> SecurityMetrics:
        """Get current security metrics.

        Returns:
            Current SecurityMetrics.
        """
        return self._metrics

    def get_audit_logs(
        self,
        limit: int = 100,
        risk_level: Optional[str] = None,
    ) -> list[SecurityAuditLog]:
        """Get recent audit logs.

        Args:
            limit: Maximum number of logs to return.
            risk_level: Optional filter by risk level.

        Returns:
            List of SecurityAuditLog entries.
        """
        logs = self._audit_logs

        if risk_level:
            logs = [log for log in logs if log.risk_level == risk_level]

        return logs[-limit:]

    def get_statistics(self) -> dict[str, Any]:
        """Get security statistics.

        Returns:
            Dictionary with security statistics.
        """
        return {
            "metrics": {
                "total_requests": self._metrics.total_requests,
                "blocked_requests": self._metrics.blocked_requests,
                "flagged_requests": self._metrics.flagged_requests,
                "safe_requests": self._metrics.safe_requests,
                "average_risk_score": round(self._metrics.average_risk_score, 4),
                "attack_types_detected": self._metrics.attack_types_detected,
            },
            "configuration": {
                "injection_enabled": self._injection_enabled,
                "jailbreak_enabled": self._jailbreak_enabled,
                "risk_threshold": self._risk_threshold,
                "block_high_risk": self._block_high_risk,
                "allow_admin_bypass": self._allow_admin_bypass,
            },
            "audit_log_count": len(self._audit_logs),
        }


# Module-level instance
security_pipeline = SecurityPipeline()
