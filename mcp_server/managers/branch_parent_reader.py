from __future__ import annotations

from mcp_server.core.exceptions import StateNotFoundError
from mcp_server.core.interfaces import IStateReader
from mcp_server.schemas import GitConfig


class BranchStateParentReader:
    """Read parent branch for a branch from persisted state with identity validation."""

    def __init__(
        self,
        state_reader: IStateReader,
        git_config: GitConfig,
    ) -> None:
        self._state_reader = state_reader
        self._git_config = git_config

    def get_parent_branch(self, branch: str) -> str | None:
        """Return parent branch if state's issue matches branch's issue; None otherwise.

        Identity validation prevents stale parent_branch leakage across issues.

        Returns:
            Parent branch string, or None if state is absent, issue mismatches,
            or the parent_branch field itself is None.
        """
        try:
            state = self._state_reader.load(branch)
        except StateNotFoundError:
            return None

        extracted_issue = self._git_config.extract_issue_number(branch)

        if state.issue_number != extracted_issue:
            return None

        return state.parent_branch
