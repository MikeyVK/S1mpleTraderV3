# c:\temp\pgmcp\mcp_server\core\interfaces\workflow.py
# template=interface version=3fb28c28 created=2026-06-20T18:33:02Z updated=
"""IWorkflowStateMutator module.

Command-side seam for coordinated workflow state writes.

@layer: Backend (Contracts)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from mcp_server.managers.state_repository import BranchState


@runtime_checkable
class IWorkflowStateMutator(Protocol):
    """Command-side seam for coordinated workflow state writes.

    All workflow state mutations must route through this interface so that
    concurrent write paths share one coordinated lock boundary.
    """

    def apply(
        self,
        branch: str,
        mutate: Callable[[BranchState], BranchState],
    ) -> None:
        """Apply *mutate* to the current BranchState for *branch* atomically.

        Raises:
            StateMutationConflictError: on lock timeout, branch mismatch, or
                unrecoverable state.
        """
        raise NotImplementedError
