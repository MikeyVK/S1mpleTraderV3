# src\copilot_orchestration\utils\_paths.py
# template=generic version=f35abd82 created=2026-03-21T12:06Z updated=
"""_paths module.

Path utilities for copilot orchestration hooks.

Provides ``find_workspace_root`` and the ``STATE_RELPATH`` constant.

@layer: Package Utilities
@dependencies: [None]
@responsibilities:
    - Locate workspace root by walking up from anchor until pyproject.toml or .git is found
    - Expose STATE_RELPATH constant for the session sub-role state file
"""

# Standard library
from pathlib import Path

STATE_RELPATH = Path(".copilot/session-sub-role.json")


def find_workspace_root(anchor: Path) -> Path:
    """Walk up from *anchor* until pyproject.toml or .git is found.

    Args:
        anchor: A file or directory inside the workspace.

    Returns:
        The directory that contains ``pyproject.toml`` or ``.git``.

    Raises:
        RuntimeError: When no sentinel is found before reaching the filesystem root.
    """
    current = anchor if anchor.is_dir() else anchor.parent
    while True:
        if (current / "pyproject.toml").exists() or (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            raise RuntimeError(
                f"Could not find workspace root from {anchor!r}: "
                "no pyproject.toml or .git sentinel found during upward traversal."
            )
        current = parent
