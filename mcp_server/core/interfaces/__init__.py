# mcp_server\core\interfaces\__init__.py
# template=generic version=f35abd82 created=2026-03-12T15:02Z updated=
"""Protocol interfaces for state access."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from mcp_server.managers.state_repository import BranchState


class IStateReader(Protocol):
    """Read-only access to persisted branch state."""

    def load(self, branch: str) -> BranchState:
        """Load state for a branch."""
        ...


class IStateRepository(IStateReader, Protocol):
    """Read-write access to persisted branch state."""

    def save(self, state: BranchState) -> None:
        """Persist branch state."""
        ...
