# mcp_server/config/label_startup.py
"""
Label configuration startup validation.

Provides non-blocking validation of labels.yaml during server initialization
to catch configuration errors early without blocking server startup.

@layer: Backend (Config)
@dependencies: [logging, pathlib, mcp_server.config.label_config]
@responsibilities:
    - Validate labels.yaml at server startup
    - Log validation results (info/warning/error)
    - Non-blocking validation (never raises exceptions)
    - Report configuration issues early
"""

# Standard library
import logging
from pathlib import Path

# Project modules
from mcp_server.config.label_config import LabelConfig

logger = logging.getLogger(__name__)


def validate_label_config_on_startup(path: Path | None = None) -> None:
    """
    Validate label configuration at server startup.

    Attempts to load labels.yaml and logs the result without raising exceptions.
    This allows the server to start even if label configuration is invalid,
    while alerting operators to configuration issues.

    Args:
        path: Path to labels.yaml (defaults to .st3/labels.yaml)

    Returns:
        None

    Logs:
        INFO: Successfully loaded configuration
        WARNING: File not found
        ERROR: YAML syntax error or validation error
    """
    if path is None:
        path = Path(".st3/labels.yaml")

    try:
        # Reset singleton to force fresh load
        LabelConfig._instance = None  # pylint: disable=protected-access

        # Attempt to load configuration
        config = LabelConfig.load(path)

        # Success - log info
        label_count = len(config.labels)
        logger.info(
            "Successfully loaded label configuration from %s (%d labels defined)",
            path,
            label_count
        )

    except FileNotFoundError:
        # Missing file - log warning
        logger.warning(
            "Label configuration file not found: %s. "
            "Labels will not be validated during operations.",
            path
        )

    except Exception as e:  # pylint: disable=broad-except
        # Any other error (YAML syntax, validation) - log error
        logger.error(
            "Failed to load label configuration from %s: %s",
            path,
            str(e)
        )
