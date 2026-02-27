# mcp_server/utils/path_resolver.py
# template=generic version=f35abd82 created=2026-02-27T06:08Z updated=
"""Utility for resolving mixed file/directory inputs to concrete .py file paths.

@layer: MCP Server (Utils)
@dependencies: [pathlib, logging]
@responsibilities:
    - Expand directory inputs to concrete .py files
    - Preserve explicit file inputs
    - Deduplicate resolved paths
    - Surface warnings for missing/unresolvable paths
"""

# Standard library
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_input_paths(
    paths: list[str],
    workspace_root: Path,
) -> tuple[list[str], list[str]]:
    """Resolve a list of file/directory paths to concrete .py file paths.

    Args:
        paths: Caller-supplied list of relative file or directory paths.
        workspace_root: Absolute workspace root used to resolve relative paths.

    Returns:
        A tuple of (resolved_files, warnings) where resolved_files is a sorted,
        deduplicated list of relative POSIX .py paths, and warnings is a list of
        human-readable strings for paths that could not be resolved.
    """
    resolved: set[str] = set()
    warnings: list[str] = []

    for raw in paths:
        abs_path = workspace_root / raw
        if abs_path.is_dir():
            for py_file in abs_path.rglob("*.py"):
                resolved.add(py_file.relative_to(workspace_root).as_posix())
        elif abs_path.is_file():
            resolved.add(abs_path.relative_to(workspace_root).as_posix())
        else:
            warnings.append(f"Path not found and will be skipped: {raw!r}")
            logger.warning("resolve_input_paths: path not found: %r", raw)

    return sorted(resolved), warnings
