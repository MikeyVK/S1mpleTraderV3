# c:\temp\pgmcp\mcp_server\core\interfaces\state.py
# template=interface version=3fb28c28 created=2026-06-20T18:28:18Z updated=
"""IStateReader module.

Read-only access to persisted branch state.

@layer: Backend (Contracts)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from mcp_server.managers.state_repository import BranchState


class IStateReader(Protocol):
    """Read-only access to persisted branch state."""

    def load(self, branch: str) -> BranchState:
        raise NotImplementedError


class IStateRepository(IStateReader, Protocol):
    """Read-write access to persisted branch state."""

    def save(self, state: BranchState) -> None:
        raise NotImplementedError
