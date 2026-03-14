"""Structured logging for the MCP server."""
import json
import logging
import sys
from pathlib import Path
from typing import Any


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


def setup_logging(log_level: str = "INFO", audit_log: str = ".logs/mcp_audit.log") -> None:
    """Configure logging.

    Args:
        log_level: Log level string (DEBUG, INFO, WARNING, ERROR). Defaults to "INFO".
        audit_log: Path to audit log file. Defaults to ".logs/mcp_audit.log".
    """
    logger = logging.getLogger("mcp_server")
    logger.setLevel(log_level)

    # Console handler
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)

    # Audit log file handler if configured
    if audit_log:
        log_path = Path(audit_log)
        try:
            # Ensure the parent directory exists (common failure on fresh checkouts)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(str(log_path))
            file_handler.setFormatter(StructuredFormatter())
            logger.addHandler(file_handler)
        except OSError as exc:
            # Fallback if file cannot be opened; still keep stderr logging.
            logger.warning(
                "Failed to configure audit log file: %s",
                exc,
                exc_info=True,
                extra={"props": {"audit_log": str(log_path)}},
            )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(f"mcp_server.{name}")
