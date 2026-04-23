"""Scaffolding utilities."""

import re
from pathlib import Path

from mcp_server.core.exceptions import ExecutionError, ValidationError


def validate_pascal_case(name: str) -> None:
    """Validate name is PascalCase.

    Args:
        name: Name to validate

    Raises:
        ValidationError: If not PascalCase
    """
    if not re.match(r"^[A-Z][a-zA-Z0-9]*$", name):
        raise ValidationError(f"Invalid name: {name}. Must be PascalCase.")


def write_scaffold_file(
    path: str,
    content: str,
    overwrite: bool = False,
    workspace_root: Path | str | None = None,
) -> None:
    """Write generated content to a file in the workspace.

    Args:
        path: Relative path within workspace
        content: Content to write
        overwrite: Whether to overwrite existing files
        workspace_root: Injected workspace root from composition root or caller

    Raises:
        ExecutionError: If file exists and overwrite=False
    """
    root = Path(workspace_root or Path.cwd()).resolve()
    full_path = root / path
    if full_path.exists() and not overwrite:
        raise ExecutionError(
            f"File exists: {path}. Use overwrite=True to replace.",
        )

    full_path.parent.mkdir(parents=True, exist_ok=True)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
