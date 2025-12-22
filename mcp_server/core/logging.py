"""Structured logging for the MCP server."""
import json
import logging
import sys
from typing import Any

from mcp_server.config.settings import settings


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "props"):
            log_data.update(record.props)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging() -> None:
    """Configure logging based on settings."""
    logger = logging.getLogger("mcp_server")
    logger.setLevel(settings.logging.level)

    # Console handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)

    # Audit log file handler if configured
    if settings.logging.audit_log:
        try:
            file_handler = logging.FileHandler(
                settings.logging.audit_log
            )
            file_handler.setFormatter(StructuredFormatter())
            logger.addHandler(file_handler)
        except OSError:
            # Fallback if file cannot be opened
            pass


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(f"mcp_server.{name}")
