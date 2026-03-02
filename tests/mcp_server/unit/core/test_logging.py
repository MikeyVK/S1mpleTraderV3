"""Tests for structured logging."""

from __future__ import annotations

import contextlib
import json
import logging
from pathlib import Path

import pytest

from mcp_server.core.logging import StructuredFormatter, get_logger, setup_logging


def _reset_mcp_server_logger() -> None:
    logger = logging.getLogger("mcp_server")
    for handler in list(logger.handlers):
        with contextlib.suppress(OSError):
            handler.close()
    logger.handlers.clear()


def _flush_mcp_server_logger() -> None:
    logger = logging.getLogger("mcp_server")
    for handler in logger.handlers:
        flush = getattr(handler, "flush", None)
        if callable(flush):
            flush()


def test_structured_formatter() -> None:
    """StructuredFormatter produces valid JSON with props."""
    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.props = {"key": "value"}

    log_output = formatter.format(record)
    data = json.loads(log_output)

    assert data["message"] == "Test message"
    assert data["level"] == "INFO"
    assert data["key"] == "value"


def test_get_logger() -> None:
    """get_logger returns logger with correct name prefix."""
    logger = get_logger("test")
    assert logger.name == "mcp_server.test"


def test_setup_logging_writes_audit_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """setup_logging writes audit log file when parent exists."""
    _reset_mcp_server_logger()

    log_file = tmp_path / "audit.log"
    monkeypatch.setattr(
        "mcp_server.config.settings.settings.logging.audit_log",
        str(log_file),
    )

    setup_logging()

    logger = get_logger("test")
    logger.info("Test audit")
    _flush_mcp_server_logger()

    assert log_file.exists()
    assert "Test audit" in log_file.read_text(encoding="utf-8")


def test_setup_logging_creates_parent_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """setup_logging creates missing parent directories for audit log."""
    _reset_mcp_server_logger()

    log_file = tmp_path / "nested" / "audit.log"
    assert not log_file.parent.exists()

    monkeypatch.setattr(
        "mcp_server.config.settings.settings.logging.audit_log",
        str(log_file),
    )

    setup_logging()

    logger = get_logger("test")
    logger.info("Test nested audit")
    _flush_mcp_server_logger()

    assert log_file.exists()
    assert "Test nested audit" in log_file.read_text(encoding="utf-8")
