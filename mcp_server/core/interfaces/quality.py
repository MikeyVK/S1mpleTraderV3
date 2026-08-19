# c:\temp\pgmcp\mcp_server\core\interfaces\quality.py
# template=interface version=3fb28c28 created=2026-06-20T18:32:06Z updated=
"""IQualityStateRepository module.

Read/apply access to persisted quality-gate baseline state.

@layer: Backend (Contracts)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from mcp_server.state.quality_state import QualityState


@runtime_checkable
class IQualityStateRepository(Protocol):
    """Read/apply access to persisted quality-gate baseline state."""

    def load(self) -> QualityState:
        """Return current QualityState; default-construct when absent."""
        raise NotImplementedError

    def apply(self, mutate: Callable[[QualityState], QualityState]) -> None:
        """Read current state, apply mutate, and persist atomically."""
        raise NotImplementedError
