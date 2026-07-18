"""Monitoring API endpoints.

Provides endpoints for:
- Metrics retrieval
- Evaluation results
- Benchmark results
- Dashboard data
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.monitoring.dashboard import dashboard
from app.services.monitoring.evaluator import evaluator
from app.services.monitoring.metrics import metrics_collector
from app.services.monitoring.benchmark import benchmark_runner
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """Get all collected metrics.

    Returns:
        Dictionary of all metrics.
    """
    return {
        "status": "success",
        "data": metrics_collector.get_all_metrics(),
    }


@router.get("/metrics/latency")
async def get_latency_metrics() -> dict[str, Any]:
    """Get latency metrics for all components.

    Returns:
        Latency metrics.
    """
    return {
        "status": "success",
        "data": metrics_collector.get_all_latency_metrics(),
    }


@router.get("/metrics/{component}")
async def get_component_metrics(component: str) -> dict[str, Any]:
    """Get metrics for a specific component.

    Args:
        component: Component name.

    Returns:
        Component metrics.
    """
    metrics = metrics_collector.get_latency_metrics(component)
    if not metrics:
        return {
            "status": "success",
            "data": {"component": component, "message": "No metrics available"},
        }

    return {
        "status": "success",
        "data": metrics,
    }


@router.get("/evaluation")
async def get_evaluation() -> dict[str, Any]:
    """Get latest evaluation results.

    Returns:
        Evaluation results.
    """
    return {
        "status": "success",
        "data": {
            "message": "Evaluation requires specific inputs",
            "endpoints": {
                "retrieval": "/api/v1/monitoring/evaluation/retrieval",
                "reranking": "/api/v1/monitoring/evaluation/reranking",
                "hallucination": "/api/v1/monitoring/evaluation/hallucination",
                "citation": "/api/v1/monitoring/evaluation/citation",
            },
        },
    }


@router.post("/evaluation/retrieval")
async def evaluate_retrieval(
    retrieved: list[str],
    relevant: list[str],
    k: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    """Evaluate retrieval quality.

    Args:
        retrieved: Retrieved document IDs.
        relevant: Relevant document IDs.
        k: Top-K value.

    Returns:
        Retrieval metrics.
    """
    try:
        metrics = evaluator.evaluate_retrieval(retrieved, relevant, k)
        return {
            "status": "success",
            "data": metrics,
        }
    except Exception as e:
        logger.error(f"Retrieval evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluation/reranking")
async def evaluate_reranking(
    pre_ranked: list[str],
    post_ranked: list[str],
    relevant: list[str],
    k: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    """Evaluate reranking effectiveness.

    Args:
        pre_ranked: Document IDs before reranking.
        post_ranked: Document IDs after reranking.
        relevant: Relevant document IDs.
        k: Top-K value.

    Returns:
        Reranking metrics.
    """
    try:
        metrics = evaluator.evaluate_reranking(pre_ranked, post_ranked, relevant, k)
        return {
            "status": "success",
            "data": metrics,
        }
    except Exception as e:
        logger.error(f"Reranking evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluation/hallucination")
async def evaluate_hallucination(
    response: str,
    context: str,
) -> dict[str, Any]:
    """Evaluate hallucination.

    Args:
        response: Generated response.
        context: Source context.

    Returns:
        Hallucination metrics.
    """
    try:
        metrics = evaluator.evaluate_hallucination(response, context)
        return {
            "status": "success",
            "data": metrics,
        }
    except Exception as e:
        logger.error(f"Hallucination evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluation/citation")
async def evaluate_citation(
    statements: list[str],
    citations: list[str],
    valid_sources: list[str],
) -> dict[str, Any]:
    """Evaluate citation quality.

    Args:
        statements: Statements in response.
        citations: Citations in response.
        valid_sources: Valid source references.

    Returns:
        Citation metrics.
    """
    try:
        metrics = evaluator.evaluate_citation(statements, citations, valid_sources)
        return {
            "status": "success",
            "data": metrics,
        }
    except Exception as e:
        logger.error(f"Citation evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/benchmark")
async def get_benchmarks() -> dict[str, Any]:
    """Get all benchmark results.

    Returns:
        Benchmark results.
    """
    return {
        "status": "success",
        "data": benchmark_runner.get_all_benchmarks(),
    }


@router.get("/benchmark/report")
async def get_benchmark_report() -> dict[str, Any]:
    """Get benchmark report.

    Returns:
        Benchmark report.
    """
    return {
        "status": "success",
        "data": {
            "report": benchmark_runner.generate_report(),
        },
    }


@router.get("/dashboard")
async def get_dashboard() -> dict[str, Any]:
    """Get dashboard metrics summary.

    Returns:
        Dashboard metrics.
    """
    return {
        "status": "success",
        "data": dashboard.get_metrics_summary(),
    }


@router.get("/dashboard/latency")
async def get_latency_dashboard() -> dict[str, Any]:
    """Get latency dashboard.

    Returns:
        Latency dashboard data.
    """
    return {
        "status": "success",
        "data": dashboard.get_latency_dashboard(),
    }


@router.get("/dashboard/performance")
async def get_performance_dashboard() -> dict[str, Any]:
    """Get performance dashboard.

    Returns:
        Performance dashboard data.
    """
    return {
        "status": "success",
        "data": dashboard.get_performance_dashboard(),
    }


@router.post("/reset")
async def reset_metrics() -> dict[str, Any]:
    """Reset all metrics.

    Returns:
        Success message.
    """
    metrics_collector.reset()
    benchmark_runner.clear()
    return {
        "status": "success",
        "message": "Metrics reset successfully",
    }
