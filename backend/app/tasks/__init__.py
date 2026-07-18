"""Celery tasks package.

This package contains Celery task definitions for background processing.
"""

from app.tasks.document_tasks import process_document_task, delete_document_vectors_task

__all__ = [
    "process_document_task",
    "delete_document_vectors_task",
]
