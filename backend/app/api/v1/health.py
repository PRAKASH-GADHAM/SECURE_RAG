"""Health check API endpoints.

Provides health check endpoints for system components.
"""

import time

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.dependencies import get_current_active_user
from app.models.user import User
from app.services.background.worker import worker_manager
from app.services.cache.cache_manager import cache_manager
from app.services.cache.redis_cache import redis_cache
from app.services.llm.factory import get_llm_provider
from app.services.llm_metrics import llm_metrics
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/llm")
async def llm_health_check(
    current_user: User = Depends(get_current_active_user),
):
    """Check LLM provider health.

    Returns provider status, reachability, latency, and metrics.

    Args:
        current_user: Authenticated user.

    Returns:
        LLM health check results.
    """
    try:
        provider = get_llm_provider()
        health = await provider.health_check()
        metrics = llm_metrics.get_metrics()

        return {
            "status": "healthy" if health.get("reachable") else "degraded",
            "provider": health,
            "metrics": {
                "total_requests": metrics.total_requests,
                "success_rate": round(metrics.success_rate, 2),
                "failure_rate": round(metrics.failure_rate, 2),
                "avg_latency_ms": round(metrics.avg_latency_ms, 2),
                "total_tokens_used": metrics.total_tokens_used,
            },
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": type(e).__name__,
        }


@router.get("/llm/metrics")
async def llm_metrics_endpoint(
    current_user: User = Depends(get_current_active_user),
):
    """Get LLM metrics.

    Args:
        current_user: Authenticated user.

    Returns:
        LLM metrics snapshot.
    """
    metrics = llm_metrics.get_metrics()

    return {
        "total_requests": metrics.total_requests,
        "successful_requests": metrics.successful_requests,
        "failed_requests": metrics.failed_requests,
        "timeout_count": metrics.timeout_count,
        "retry_count": metrics.retry_count,
        "total_tokens_used": metrics.total_tokens_used,
        "avg_latency_ms": round(metrics.avg_latency_ms, 2),
        "avg_streaming_latency_ms": round(metrics.avg_streaming_latency_ms, 2),
        "min_latency_ms": metrics.min_latency_ms,
        "max_latency_ms": metrics.max_latency_ms,
        "success_rate": round(metrics.success_rate, 2),
        "failure_rate": round(metrics.failure_rate, 2),
    }


@router.get("/redis")
async def redis_health_check(
    current_user: User = Depends(get_current_active_user),
):
    """Check Redis health.

    Args:
        current_user: Authenticated user.

    Returns:
        Redis health status.
    """
    health = await redis_cache.health_check()
    return health


@router.get("/cache")
async def cache_health_check(
    current_user: User = Depends(get_current_active_user),
):
    """Check cache health and metrics.

    Args:
        current_user: Authenticated user.

    Returns:
        Cache health and metrics.
    """
    metrics = cache_manager.get_metrics()
    redis_health = await redis_cache.health_check()

    return {
        "status": "healthy" if redis_health.get("status") == "healthy" else "degraded",
        "redis": redis_health,
        "metrics": metrics,
    }


@router.get("/celery")
async def celery_health_check(
    current_user: User = Depends(get_current_active_user),
):
    """Check Celery worker health.

    Args:
        current_user: Authenticated user.

    Returns:
        Celery health status.
    """
    health = await worker_manager.health_check()
    stats = await worker_manager.get_worker_stats()
    queue_length = await worker_manager.get_queue_length()

    return {
        **health,
        "stats": stats,
        "queue": queue_length,
    }


_startup_time = time.time()


@router.get("/detailed")
async def detailed_health_check():
    """Comprehensive system health check.

    Checks all system components and returns overall status.
    """
    start = time.monotonic()
    checks = {}

    # Database check
    try:
        from app.database import get_db_session
        async with get_db_session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy", "latency_ms": round((time.monotonic() - start) * 1000, 2)}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": type(e).__name__}

    db_time = time.monotonic()

    # Redis check
    try:
        redis_health = await redis_cache.health_check()
        checks["redis"] = {
            "status": redis_health.get("status", "unknown"),
            "latency_ms": round((time.monotonic() - db_time) * 1000, 2),
        }
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": type(e).__name__}

    redis_time = time.monotonic()

    # ChromaDB check
    try:
        import httpx
        settings = get_settings()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}/api/v1/heartbeat")
            checks["chromadb"] = {
                "status": "healthy" if resp.status_code == 200 else "degraded",
                "latency_ms": round((time.monotonic() - redis_time) * 1000, 2),
            }
    except Exception as e:
        checks["chromadb"] = {"status": "unhealthy", "error": type(e).__name__}

    chroma_time = time.monotonic()

    # Celery check
    try:
        celery_health = await worker_manager.health_check()
        checks["celery"] = {
            "status": celery_health.get("status", "unknown"),
            "latency_ms": round((time.monotonic() - chroma_time) * 1000, 2),
        }
    except Exception as e:
        checks["celery"] = {"status": "unhealthy", "error": type(e).__name__}

    total_ms = round((time.monotonic() - start) * 1000, 2)

    healthy_count = sum(1 for c in checks.values() if c.get("status") == "healthy")
    total_count = len(checks)

    if healthy_count == total_count:
        overall = "healthy"
    elif healthy_count > total_count / 2:
        overall = "degraded"
    else:
        overall = "unhealthy"

    settings = get_settings()
    return {
        "status": overall,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "uptime_seconds": time.time() - _startup_time,
        "total_latency_ms": total_ms,
        "services": checks,
        "summary": {
            "healthy": healthy_count,
            "unhealthy": total_count - healthy_count,
            "total": total_count,
        },
    }


@router.get("/system")
async def system_info():
    """Get system information."""
    import os
    import platform

    settings = get_settings()
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "pid": os.getpid(),
        "cpu_count": os.cpu_count(),
        "app_version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }
