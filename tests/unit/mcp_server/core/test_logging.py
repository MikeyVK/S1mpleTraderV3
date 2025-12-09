"""Tests for structured logging."""
import json
import logging
from mcp_server.core.logging import StructuredFormatter, get_logger, setup_logging

def test_structured_formatter():
    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="Test message", args=(), exc_info=None
    )
    record.props = {"key": "value"} # type: ignore

    log_output = formatter.format(record)
    data = json.loads(log_output)

    assert data["message"] == "Test message"
    assert data["level"] == "INFO"
    assert data["key"] == "value"

def test_get_logger():
    logger = get_logger("test")
    assert logger.name == "mcp_server.test"

def test_setup_logging(tmp_path, monkeypatch):
    # Mock settings
    log_file = tmp_path / "audit.log"
    monkeypatch.setattr("mcp_server.config.settings.settings.logging.audit_log", str(log_file))

    setup_logging()

    logger = get_logger("test")
    logger.info("Test audit")

    # Verify file content
    assert log_file.exists()
    content = log_file.read_text()
    assert "Test audit" in content
