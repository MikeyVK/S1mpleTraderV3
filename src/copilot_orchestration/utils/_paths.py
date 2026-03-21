# src\copilot_orchestration\utils\_paths.py
# template=generic version=f35abd82 created=2026-03-21T12:06Z updated=
"""_paths module.

Path utilities for copilot orchestration hooks.

Provides ``find_workspace_root`` and ``state_path_for_role``.

@layer: Package Utilities
@dependencies: [None]
@responsibilities:
    - Locate workspace root by walking up from anchor until pyproject.toml or .git is found
    - Expose state_path_for_role(role) to return role-scoped session state file path
"""

# Standard library
from pathlib import Path


def state_path_for_role(role: str) -> Path:
    """Return the role-scoped session sub-role state file path (relative to workspace root).

    Args:
        role: The agent role identifier (e.g. 'imp', 'qa').

    Returns:
        Relative Path to ``.copilot/session-sub-role-{role}.json``.
    """
    return Path(f".copilot/session-sub-role-{role}.json")


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
