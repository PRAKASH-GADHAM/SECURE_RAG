"""Security API endpoints.

Provides endpoints for security analysis and statistics.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.security.security_models import RiskLevel, SecurityAction
from app.services.security.security_pipeline import security_pipeline
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/security", tags=["security"])


class SecurityAnalyzeRequest(BaseModel):
    """Request model for security analysis."""

    content: str = Field(..., min_length=1, max_length=100000)
    context: str | None = None
    conversation_length: int | None = None


class SecurityAnalyzeResponse(BaseModel):
    """Response model for security analysis."""

    request_id: str
    risk_score: float
    risk_level: str
    detected_patterns: list[str]
    attack_types: list[str]
    recommended_action: str
    checks_passed: list[str]
    checks_failed: list[str]


class SecurityStatisticsResponse(BaseModel):
    """Response model for security statistics."""

    metrics: dict
    configuration: dict
    audit_log_count: int


class AuditLogEntry(BaseModel):
    """Audit log entry model."""

    request_id: str
    user_id: str | None
    timestamp: str
    risk_score: float
    risk_level: str
    detected_patterns: list[str]
    action_taken: str
    attack_types: list[str]


@router.post(
    "/analyze",
    response_model=SecurityAnalyzeResponse,
    summary="Analyze content for security threats",
    description="Analyze user input for prompt injection, jailbreak attempts, and other security threats.",
)
async def analyze_content(
    request: SecurityAnalyzeRequest,
    current_user: User = Depends(get_current_user),
) -> SecurityAnalyzeResponse:
    """Analyze content through the security pipeline.

    Args:
        request: Security analysis request.
        current_user: Current authenticated user.

    Returns:
        Security analysis results.
    """
    result = security_pipeline.analyze(
        content=request.content,
        user_id=str(current_user.id),
        context=request.context,
        conversation_length=request.conversation_length,
    )

    return SecurityAnalyzeResponse(
        request_id=result.request_id,
        risk_score=result.risk_score,
        risk_level=result.risk_level.value,
        detected_patterns=result.detected_patterns,
        attack_types=[at.value for at in result.attack_types],
        recommended_action=result.recommended_action.value,
        checks_passed=result.checks_passed,
        checks_failed=result.checks_failed,
    )


@router.get(
    "/statistics",
    response_model=SecurityStatisticsResponse,
    summary="Get security statistics",
    description="Get security metrics and statistics. Admin only.",
)
async def get_statistics(
    current_user: User = Depends(get_current_user),
) -> SecurityStatisticsResponse:
    """Get security statistics.

    Args:
        current_user: Current authenticated user (must be admin).

    Returns:
        Security statistics.

    Raises:
        HTTPException: If user is not admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    stats = security_pipeline.get_statistics()

    return SecurityStatisticsResponse(
        metrics=stats["metrics"],
        configuration=stats["configuration"],
        audit_log_count=stats["audit_log_count"],
    )


@router.get(
    "/audit-logs",
    response_model=list[AuditLogEntry],
    summary="Get audit logs",
    description="Get recent security audit logs. Admin only.",
)
async def get_audit_logs(
    limit: int = 100,
    risk_level: str | None = None,
    current_user: User = Depends(get_current_user),
) -> list[AuditLogEntry]:
    """Get recent audit logs.

    Args:
        limit: Maximum number of logs to return.
        risk_level: Optional filter by risk level.
        current_user: Current authenticated user (must be admin).

    Returns:
        List of audit log entries.

    Raises:
        HTTPException: If user is not admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    logs = security_pipeline.get_audit_logs(limit=limit, risk_level=risk_level)

    return [
        AuditLogEntry(
            request_id=log.request_id,
            user_id=log.user_id,
            timestamp=log.timestamp.isoformat(),
            risk_score=log.risk_score,
            risk_level=log.risk_level,
            detected_patterns=log.detected_patterns,
            action_taken=log.action_taken,
            attack_types=log.attack_types,
        )
        for log in logs
    ]
