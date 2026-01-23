"""
Configuration utilities for scaffolding system.

Provides centralized template root resolution with fail-fast behavior.
"""

import os
from pathlib import Path


def get_template_root() -> Path:
    """
    Get template root directory with fail-fast behavior.

    Resolution order:
    1. TEMPLATE_ROOT environment variable (if set)
    2. Default: mcp_server/scaffolding/templates (tier-root)

    Raises:
        FileNotFoundError: If configured path doesn't exist (fail-fast, no fallback)

    Returns:
        Absolute path to template root directory
    """
    # Check environment variable first
    env_path = os.getenv("TEMPLATE_ROOT")
    if env_path:
        template_root = Path(env_path)
        if not template_root.exists():
            raise FileNotFoundError(
                f"Template root from TEMPLATE_ROOT env var does not exist: {template_root}"
            )
        return template_root.resolve()

    # Default: tier-based template structure
    default_root = Path("mcp_server/scaffolding/templates")
    if not default_root.exists():
        raise FileNotFoundError(
            f"Default template root does not exist: {default_root}. "
            "This indicates a project structure issue."
        )
    return default_root.resolve()
