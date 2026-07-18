"""Guardrails API endpoints.

Provides endpoints for output protection analysis and statistics.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.guardrails.guardrail_models import OutputDecision
from app.services.guardrails.output_pipeline import output_pipeline
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


class GuardrailsAnalyzeRequest(BaseModel):
    """Request model for guardrails analysis."""

    content: str = Field(..., min_length=1, max_length=100000)
    context: str | None = None


class PIIDetectionResponse(BaseModel):
    """PII detection response model."""

    detected: bool
    total_pii_count: int
    categories: list[str]


class ModerationResponse(BaseModel):
    """Moderation response model."""

    is_safe: bool
    risk_score: float
    blocked: bool
    detections_count: int


class CitationResponse(BaseModel):
    """Citation validation response model."""

    total_statements: int
    supported_claims: int
    unsupported_claims: int
    citation_coverage: float


class HallucinationResponse(BaseModel):
    """Hallucination detection response model."""

    confidence_level: str
    groundedness_score: float
    confidence_score: float
    unsupported_statements: int


class GuardrailsAnalyzeResponse(BaseModel):
    """Response model for guardrails analysis."""

    request_id: str
    decision: str
    processed_content: str
    warnings: list[str]
    pii: PIIDetectionResponse | None
    moderation: ModerationResponse | None
    citation: CitationResponse | None
    hallucination: HallucinationResponse | None


class GuardrailsStatisticsResponse(BaseModel):
    """Response model for guardrails statistics."""

    total_responses: int
    responses_blocked: int
    responses_redacted: int
    responses_warning: int
    responses_safe: int
    average_hallucination_score: float | None
    average_citation_coverage: float | None
    pii_detections: int
    moderation_detections: int


@router.post(
    "/analyze",
    response_model=GuardrailsAnalyzeResponse,
    summary="Analyze content with guardrails",
    description="Analyze LLM response through the output protection pipeline.",
)
async def analyze_content(
    request: GuardrailsAnalyzeRequest,
    current_user: User = Depends(get_current_user),
) -> GuardrailsAnalyzeResponse:
    """Analyze content through the guardrails pipeline.

    Args:
        request: Guardrails analysis request.
        current_user: Current authenticated user.

    Returns:
        Guardrails analysis results.
    """
    result = output_pipeline.analyze(
        content=request.content,
        user_id=str(current_user.id),
        context=request.context,
    )

    # Build PII response
    pii_response = None
    if result.pii_result:
        pii_response = PIIDetectionResponse(
            detected=result.pii_result.detected,
            total_pii_count=result.pii_result.total_pii_count,
            categories=[d.category.value for d in result.pii_result.detections],
        )

    # Build moderation response
    moderation_response = None
    if result.moderation_result:
        moderation_response = ModerationResponse(
            is_safe=result.moderation_result.is_safe,
            risk_score=result.moderation_result.risk_score,
            blocked=result.moderation_result.blocked,
            detections_count=len(result.moderation_result.detections),
        )

    # Build citation response
    citation_response = None
    if result.citation_result:
        citation_response = CitationResponse(
            total_statements=result.citation_result.total_statements,
            supported_claims=result.citation_result.supported_claims,
            unsupported_claims=result.citation_result.unsupported_claims,
            citation_coverage=result.citation_result.citation_coverage,
        )

    # Build hallucination response
    hallucination_response = None
    if result.hallucination_result:
        hallucination_response = HallucinationResponse(
            confidence_level=result.hallucination_result.confidence_level.value,
            groundedness_score=result.hallucination_result.groundedness_score,
            confidence_score=result.hallucination_result.confidence_score,
            unsupported_statements=result.hallucination_result.unsupported_statements,
        )

    return GuardrailsAnalyzeResponse(
        request_id=result.request_id,
        decision=result.decision.value,
        processed_content=result.processed_content,
        warnings=result.warnings,
        pii=pii_response,
        moderation=moderation_response,
        citation=citation_response,
        hallucination=hallucination_response,
    )


@router.get(
    "/statistics",
    response_model=GuardrailsStatisticsResponse,
    summary="Get guardrails statistics",
    description="Get guardrails metrics and statistics. Admin only.",
)
async def get_statistics(
    current_user: User = Depends(get_current_user),
) -> GuardrailsStatisticsResponse:
    """Get guardrails statistics.

    Args:
        current_user: Current authenticated user (must be admin).

    Returns:
        Guardrails statistics.

    Raises:
        HTTPException: If user is not admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    metrics = output_pipeline.get_metrics()

    return GuardrailsStatisticsResponse(
        total_responses=metrics.get("total_responses", 0),
        responses_blocked=metrics.get("responses_blocked", 0),
        responses_redacted=metrics.get("responses_redacted", 0),
        responses_warning=metrics.get("responses_warning", 0),
        responses_safe=metrics.get("responses_safe", 0),
        average_hallucination_score=metrics.get("average_hallucination_score"),
        average_citation_coverage=metrics.get("average_citation_coverage"),
        pii_detections=metrics.get("pii_detections", 0),
        moderation_detections=metrics.get("moderation_detections", 0),
    )
