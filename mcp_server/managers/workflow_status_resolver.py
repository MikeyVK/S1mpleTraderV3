# mcp_server/managers/workflow_status_resolver.py
# template=generic version=f35abd82 created=2026-03-23T00:00Z updated=
"""WorkflowStatusResolver — read-only resolver for current branch workflow status."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mcp_server.core.exceptions import StateNotFoundError
from mcp_server.state.workflow_status import WorkflowStatusDTO

if TYPE_CHECKING:
    from mcp_server.core.commit_phase_detector import CommitPhaseDetector
    from mcp_server.core.interfaces import IGitContextReader, IStateReader

logger = logging.getLogger(__name__)


class WorkflowStatusResolver:
    """Resolve current-branch workflow status from persisted state.

    state.json is the primary and only source of truth. If state.json is absent,
    StateNotFoundError is raised. If state.json exists but belongs to a different
    branch, StateBranchMismatchError is raised (propagated from BranchValidatedStateReader).
    """

    def __init__(
        self,
        git_context_reader: IGitContextReader,
        state_reader: IStateReader,
        commit_phase_detector: CommitPhaseDetector,
    ) -> None:
        self._git = git_context_reader
        self._state = state_reader
        self._detector = commit_phase_detector

    def resolve_current(self) -> WorkflowStatusDTO:
        """Resolve workflow status for the current branch from state.json.

        Raises:
            StateNotFoundError: state.json does not exist for this branch.
            StateBranchMismatchError: state.json exists but belongs to a different branch.
        """
        branch = self._git.get_current_branch()

        try:
            branch_state = self._state.load(branch)
        except StateNotFoundError:
            raise
        except (KeyError, FileNotFoundError) as exc:
            raise StateNotFoundError(branch) from exc
        # StateBranchMismatchError propagates unchanged from BranchValidatedStateReader

        return WorkflowStatusDTO(
            current_phase=branch_state.current_phase,
            sub_phase=branch_state.current_sub_phase,
            current_cycle=branch_state.current_cycle,
            phase_source="state.json",
            phase_confidence="high",
        )
