"""Tests for logging utilities.

Covers JSONFormatter, ConsoleFormatter, setup_logging, and logger retrieval functions.
"""

import json
import logging

import pytest

from app.utils.logging import (
    ConsoleFormatter,
    JSONFormatter,
    get_audit_logger,
    get_logger,
    get_security_logger,
    get_worker_logger,
    setup_logging,
)


class TestJSONFormatter:
    """Tests for JSONFormatter."""

    def test_produces_valid_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="test message", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "test message"
        assert "timestamp" in parsed

    def test_includes_logger_name(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="app.core", level=logging.DEBUG, pathname="test.py",
            lineno=1, msg="debug msg", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["logger"] == "app.core"

    def test_includes_module_and_function(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="mod.py",
            lineno=10, msg="warn", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "module" in parsed
        assert "function" in parsed
        assert "line" in parsed

    def test_includes_exception_info(self):
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="error occurred", args=(), exc_info=exc_info,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert parsed["exception"]["message"] == "test error"

    def test_includes_request_id(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="msg", args=(), exc_info=None,
        )
        record.request_id = "req-123"
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["request_id"] == "req-123"

    def test_includes_user_id(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="msg", args=(), exc_info=None,
        )
        record.user_id = "user-456"
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["user_id"] == "user-456"

    def test_includes_extra_data(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="msg", args=(), exc_info=None,
        )
        record.extra_data = {"key": "value"}
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["extra"] == {"key": "value"}


class TestConsoleFormatter:
    """Tests for ConsoleFormatter."""

    def test_produces_output_with_level(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test.module", level=logging.WARNING, pathname="test.py",
            lineno=1, msg="warning message", args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert "WARNING" in output
        assert "warning message" in output

    def test_includes_logger_name(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="app.core", level=logging.INFO, pathname="test.py",
            lineno=1, msg="info msg", args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert "app.core" in output

    def test_contains_color_codes(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="error", args=(), exc_info=None,
        )
        output = formatter.format(record)
        # RED color for ERROR
        assert "\033[31m" in output
        assert "\033[0m" in output

    def test_debug_uses_cyan(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test", level=logging.DEBUG, pathname="test.py",
            lineno=1, msg="debug", args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert "\033[36m" in output

    def test_info_uses_green(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="info", args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert "\033[32m" in output

    def test_warning_uses_yellow(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="test.py",
            lineno=1, msg="warn", args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert "\033[33m" in output


class TestSetupLogging:
    """Tests for setup_logging."""

    def test_configures_root_logger_level(self):
        setup_logging("DEBUG", json_output=False)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_configures_warning_level(self):
        setup_logging("WARNING", json_output=False)
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_has_handler_after_setup(self):
        setup_logging("INFO", json_output=False)
        root = logging.getLogger()
        assert len(root.handlers) >= 1

    def test_suppresses_noisy_loggers(self):
        setup_logging("INFO", json_output=False)
        uvicorn_access = logging.getLogger("uvicorn.access")
        assert uvicorn_access.level == logging.WARNING


class TestGetLogger:
    """Tests for get_logger."""

    def test_returns_named_logger(self):
        logger = get_logger("test.module")
        assert logger.name == "test.module"
        assert isinstance(logger, logging.Logger)

    def test_returns_same_instance(self):
        logger1 = get_logger("test.same")
        logger2 = get_logger("test.same")
        assert logger1 is logger2


class TestGetSecurityLogger:
    """Tests for get_security_logger."""

    def test_returns_security_logger(self):
        logger = get_security_logger()
        assert logger.name == "security"
        assert isinstance(logger, logging.Logger)


class TestGetAuditLogger:
    """Tests for get_audit_logger."""

    def test_returns_audit_logger(self):
        logger = get_audit_logger()
        assert logger.name == "audit"
        assert isinstance(logger, logging.Logger)


class TestGetWorkerLogger:
    """Tests for get_worker_logger."""

    def test_returns_worker_logger(self):
        logger = get_worker_logger()
        assert logger.name == "celery.worker"
        assert isinstance(logger, logging.Logger)
