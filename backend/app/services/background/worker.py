"""Worker utilities for Celery background processing.

Provides worker monitoring, health checks, and management utilities.
"""

import time
from typing import Any, Optional

from app.services.background.celery_app import celery_app
from app.utils.logging import get_logger

logger = get_logger(__name__)


class WorkerManager:
    """Manages Celery workers and monitoring."""

    def __init__(self):
        """Initialize worker manager."""
        self._start_time = time.time()
        logger.info("Worker manager initialized")

    async def get_worker_stats(self) -> dict[str, Any]:
        """Get worker statistics.

        Returns:
            Worker statistics.
        """
        try:
            inspect = celery_app.control.inspect()
            stats = inspect.stats() or {}
            active = inspect.active() or {}
            scheduled = inspect.scheduled() or {}

            return {
                "workers": len(stats),
                "stats": stats,
                "active_tasks": sum(len(tasks) for tasks in active.values()),
                "scheduled_tasks": sum(len(tasks) for tasks in scheduled.values()),
                "uptime_seconds": int(time.time() - self._start_time),
            }
        except Exception as e:
            logger.error(f"Failed to get worker stats: {e}")
            return {
                "workers": 0,
                "stats": {},
                "active_tasks": 0,
                "scheduled_tasks": 0,
                "error": str(e),
            }

    async def get_queue_length(self) -> dict[str, int]:
        """Get queue lengths.

        Returns:
            Dictionary of queue names to lengths.
        """
        try:
            inspect = celery_app.control.inspect()
            active = inspect.active() or {}
            scheduled = inspect.scheduled() or {}

            return {
                "active": sum(len(tasks) for tasks in active.values()),
                "scheduled": sum(len(tasks) for tasks in scheduled.values()),
            }
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return {"active": 0, "scheduled": 0}

    async def health_check(self) -> dict[str, Any]:
        """Check worker health.

        Returns:
            Health status.
        """
        try:
            inspect = celery_app.control.inspect()
            ping = inspect.ping()

            if ping:
                return {
                    "status": "healthy",
                    "workers": len(ping),
                    "responsive": True,
                }
            else:
                return {
                    "status": "unhealthy",
                    "workers": 0,
                    "responsive": False,
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "responsive": False,
            }

    async def purge_queue(self, queue_name: str) -> bool:
        """Purge all tasks from a queue.

        Args:
            queue_name: Name of queue to purge.

        Returns:
            True if successful.
        """
        try:
            celery_app.control.purge()
            logger.info(f"Purged queue: {queue_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to purge queue: {e}")
            return False

    async def revoke_task(
        self,
        task_id: str,
        terminate: bool = False,
    ) -> bool:
        """Revoke a running task.

        Args:
            task_id: Task ID to revoke.
            terminate: Whether to terminate the task.

        Returns:
            True if successful.
        """
        try:
            celery_app.control.revoke(task_id, terminate=terminate)
            logger.info(f"Revoked task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke task: {e}")
            return False


# Module-level instance
worker_manager = WorkerManager()
