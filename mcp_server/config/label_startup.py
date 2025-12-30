"""
Label configuration startup validation.

Validates labels.yaml at MCP server startup for early problem detection.

@layer: Backend (Config)
@dependencies: [logging, mcp_server.config.label_config]
@responsibilities:
    - Load labels.yaml at startup
    - Log warnings for missing/invalid config
    - Non-blocking validation (server starts anyway)
"""

# Standard library
import logging

# Local
from mcp_server.config.label_config import LabelConfig


logger = logging.getLogger(__name__)


def validate_label_config_on_startup(config_path: str | None = None) -> None:
    """
    Validate labels.yaml at server startup.
    
    Args:
        config_path: Optional path to labels.yaml (for testing)
    
    Logs warnings but does NOT block startup.
    Tools will validate at operation time.
    """
    from pathlib import Path
    
    try:
        path = Path(config_path) if config_path else None
        label_config = LabelConfig.load(path)
        logger.info("Loaded labels.yaml: %d labels", len(label_config.labels))
        
    except FileNotFoundError:
        logger.warning(
            "labels.yaml not found at .st3/labels.yaml. "
            "Label validation will fail until file is created."
        )
    except ValueError as e:
        logger.error(
            "Invalid labels.yaml configuration: %s. "
            "Fix configuration before using label tools.", e
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(
            "Unexpected error loading labels.yaml: %s. "
            "Label tools may not function correctly.", e
        )
