"""Celery worker configuration for background tasks.

Handles document processing, embedding generation, and other async operations.
"""

import os

from celery import Celery
from celery.signals import worker_ready

from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "secure_rag_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=300,  # 5 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Called when the worker is ready."""
    print("Celery worker is ready!")


# Task route configuration
celery_app.conf.task_routes = {
    "app.tasks.document.*": {"queue": "document_processing"},
    "app.tasks.embedding.*": {"queue": "embedding"},
}
