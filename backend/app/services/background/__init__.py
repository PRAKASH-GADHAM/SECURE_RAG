"""Background processing services package.

Provides Celery-based background task processing.
"""

from app.services.background.celery_app import celery_app
from app.services.background.worker import WorkerManager, worker_manager

__all__ = [
    "celery_app",
    "WorkerManager",
    "worker_manager",
]
