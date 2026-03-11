"""
Configuration utilities for scaffolding system.

Provides centralized template root resolution with fail-fast behavior.
"""

import os
from pathlib import Path


def get_template_root() -> Path:
    """
    Get template root directory.

    Resolution order:
    1. TEMPLATE_ROOT environment variable (if set)
    2. .st3/templates/ in current workspace (workspace-local, takes priority over package)
    3. mcp_server/scaffolding/templates/ bundled in installed package

    Raises:
        FileNotFoundError: If no valid template root is found

    Returns:
        Absolute path to template root directory
    """
    # 1. Check environment variable first
    env_path = os.getenv("TEMPLATE_ROOT")
    if env_path:
        template_root = Path(env_path)
        if not template_root.exists():
            raise FileNotFoundError(
                f"Template root from TEMPLATE_ROOT env var does not exist: {template_root}"
            )
        return template_root.resolve()

    # 2. Workspace .st3/templates/ (workspace-local override)
    workspace_root = Path(".st3/templates")
    if workspace_root.exists():
        return workspace_root.resolve()

    # 3. Package-bundled templates (installed via wheel)
    package_root = Path(__file__).parent.parent / "scaffolding" / "templates"
    if package_root.exists():
        return package_root.resolve()

    raise FileNotFoundError(
        "Template root not found. Expected one of:\n"
        "  - TEMPLATE_ROOT environment variable\n"
        "  - .st3/templates/ in workspace\n"
        "  - mcp_server/scaffolding/templates/ in installed package"
    )
