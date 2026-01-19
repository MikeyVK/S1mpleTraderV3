"""Scaffolding data structures.

Common data structures used across scaffolding system.
Issue #56: Unified artifact system.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScaffoldResult:
    """Result of scaffolding operation.
    
    Attributes:
        content: Rendered content of the scaffolded artifact
        file_name: Suggested filename (optional)
    """

    content: str
    file_name: str | None = None
