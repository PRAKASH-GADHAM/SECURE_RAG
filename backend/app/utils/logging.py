"""Structured JSON logging configuration.

Provides consistent logging across the application with JSON formatting.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any


class JSONFormatter(logging.Formatter):
    """Custom JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: The log record.

        Returns:
            JSON formatted log string.
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data

        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Console formatter for development with colored output."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output.

        Args:
            record: The log record.

        Returns:
            Colored log string.
        """
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"{color}[{timestamp}] {record.levelname:8s}{self.RESET} "
            f"{record.name}: {record.getMessage()}"
        )


def setup_logging(log_level: str = "INFO", json_output: bool = False, log_dir: str = "./logs") -> None:
    """Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: Whether to use JSON formatting.
        log_dir: Directory for log files.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    if json_output:
        os.makedirs(log_dir, exist_ok=True)

        app_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        app_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(app_handler)

        security_handler = RotatingFileHandler(
            os.path.join(log_dir, "security.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        security_handler.setFormatter(JSONFormatter())
        security_logger = logging.getLogger("security")
        security_logger.addHandler(security_handler)
        security_logger.setLevel(level)
        security_logger.propagate = False

        audit_handler = RotatingFileHandler(
            os.path.join(log_dir, "audit.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        audit_handler.setFormatter(JSONFormatter())
        audit_logger = logging.getLogger("audit")
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(level)
        audit_logger.propagate = False

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance.

    Args:
        name: Logger name (typically module name).

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


def get_security_logger() -> logging.Logger:
    return logging.getLogger("security")


def get_audit_logger() -> logging.Logger:
    return logging.getLogger("audit")


def get_worker_logger() -> logging.Logger:
    return logging.getLogger("celery.worker")
