"""Scaffolding utilities."""
import re
from pathlib import Path

from mcp_server.config.settings import settings
from mcp_server.core.exceptions import ExecutionError, ValidationError


def validate_pascal_case(name: str) -> None:
    """Validate name is PascalCase.

    Args:
        name: Name to validate

    Raises:
        ValidationError: If not PascalCase
    """
    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
        raise ValidationError(
            f"Invalid name: {name}. Must be PascalCase.",
            hints=["Use PascalCase like 'OrderState' or 'ConfigDTO'"]
        )


def write_scaffold_file(path: str, content: str, overwrite: bool = False) -> None:
    """Write generated content to a file in the workspace.

    Args:
        path: Relative path within workspace
        content: Content to write
        overwrite: Whether to overwrite existing files

    Raises:
        ExecutionError: If file exists and overwrite=False
    """
    full_path = Path(settings.server.workspace_root) / path

    if full_path.exists() and not overwrite:
        raise ExecutionError(
            f"File exists: {path}. Use overwrite=True to replace.",
            recovery=["Set overwrite=True or choose a different path"]
        )

    full_path.parent.mkdir(parents=True, exist_ok=True)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
