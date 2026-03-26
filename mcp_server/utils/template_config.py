# mcp_server/utils/template_config.py
"""
Template root resolution utilities.

Provides centralized fail-fast resolution for scaffold template directories
across workspace-local and package-bundled template sources.

@layer: Backend (Utils)
@dependencies: [os, pathlib]
@responsibilities:
    - Resolve template root from environment overrides
    - Prefer workspace-local templates over bundled package templates
    - Fail fast when no valid template root exists
"""

# Standard library
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
    env_path = os.getenv("TEMPLATE_ROOT")
    if env_path:
        template_root = Path(env_path)
        if not template_root.exists():
            raise FileNotFoundError(
                f"Template root from TEMPLATE_ROOT env var does not exist: {template_root}"
            )
        return template_root.resolve()

    workspace_root = Path(".st3/templates")
    if workspace_root.exists():
        return workspace_root.resolve()

    package_root = Path(__file__).parent.parent / "scaffolding" / "templates"
    if package_root.exists():
        return package_root.resolve()

    raise FileNotFoundError(
        "Template root not found. Expected one of:\n"
        "  - TEMPLATE_ROOT environment variable\n"
        "  - .st3/templates/ in workspace\n"
        "  - mcp_server/scaffolding/templates/ in installed package"
    )
