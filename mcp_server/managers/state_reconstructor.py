"""State reconstructor seam introduced for Cycle 1 dependency injection."""

from __future__ import annotations

from mcp_server.managers.state_repository import BranchState


class StateReconstructor:
    """Placeholder reconstructor until Cycle 3 extracts live recovery logic."""

    def reconstruct(self, branch: str) -> BranchState:
        msg = (
            "StateReconstructor.reconstruct() is reserved for C_STATE_RECOVERY and "
            "should not be called before recovery extraction is implemented."
        )
        raise NotImplementedError(f"{msg} Branch: {branch}")
