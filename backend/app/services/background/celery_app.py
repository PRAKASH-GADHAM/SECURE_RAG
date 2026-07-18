"""Celery application configuration.

Configures Celery for background task processing with:
- Redis broker
- Exponential backoff retry
- Task routing
- Worker settings
"""

from celery import Celery

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def create_celery_app() -> Celery:
    """Create and configure Celery application.

    Returns:
        Configured Celery instance.
    """
    app = Celery(
        "secure_rag",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    # Configure Celery
    app.conf.update(
        # Serialization
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

        # Timezone
        timezone="UTC",
        enable_utc=True,

        # Task settings
        task_track_started=True,
        task_time_limit=300,  # 5 minutes
        task_soft_time_limit=240,  # 4 minutes

        # Retry settings
        task_default_retry_delay=60,
        task_max_retries=3,

        # Worker settings
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        worker_max_memory_per_child=200000,  # 200MB

        # Result settings
        result_expires=3600,  # 1 hour

        # Beat settings (for periodic tasks)
        beat_schedule={},

        # Task routes
        task_routes={
            "app.services.background.tasks.process_document": {"queue": "document"},
            "app.services.background.tasks.generate_embeddings": {"queue": "embedding"},
            "app.services.background.tasks.index_document": {"queue": "indexing"},
        },
    )

    # Auto-discover tasks
    app.autodiscover_tasks(["app.services.background"])

    logger.info("Celery app configured")
    return app


# Create Celery instance
celery_app = create_celery_app()
