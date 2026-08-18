# mcp_server/managers/workflow_state_mutator.py
"""Coordinated workflow state mutation seam.

Provides an atomic read-mutate-write boundary for workflow state so that
command paths no longer contain stale load-modify-save windows.

@layer: Platform
@dependencies: [state_repository, threading]
@responsibilities:
    - Acquire per-state-file in-process lock before reading mutable state
    - Load fresh workflow state (or bootstrap for initialize_branch)
    - Invoke supplied mutation callback against loaded BranchState
    - Validate branch identity on the result
    - Persist through IStateRepository.save()
    - Raise StateMutationConflictError on lock timeout, branch mismatch, or
      unrecoverable invalid state
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from mcp_server.core.exceptions import StateNotFoundError
from mcp_server.managers.state_repository import BranchState

if TYPE_CHECKING:
    from mcp_server.core.interfaces import IStateRepository

logger = logging.getLogger(__name__)

_LOCK_TIMEOUT_SECONDS: float = 5.0


class StateMutationConflictError(Exception):
    """Raised when a coordinated workflow state mutation cannot complete safely.

    Carries both a diagnostic message (suitable for ToolResult.error) and a
    recovery hint (suitable for RecoveryNote).
    """

    def __init__(self, diagnostic: str, recovery: str) -> None:
        super().__init__(diagnostic)
        self.diagnostic = diagnostic
        self.recovery = recovery


class WorkflowStateMutator:
    """Atomic workflow-state mutation coordinator.

    Implements IWorkflowStateMutator: acquires a per-state-file in-process
    lock, loads the freshest state, invokes the supplied callback, validates
    branch identity, and persists via the injected IStateRepository.
    """

    def __init__(
        self,
        state_repository: IStateRepository,
    ) -> None:
        self._state_repository = state_repository
        self._lock = threading.Lock()

    def apply(
        self,
        branch: str,
        mutate: Callable[[BranchState], BranchState],
    ) -> None:
        """Apply a mutation to the workflow state for *branch* atomically.

        Steps:
        1. Acquire the in-process lock (timeout = 5 s).
        2. Load the freshest BranchState for *branch*.
        3. Call ``mutate(state)`` to obtain the updated state.
        4. Verify that ``updated.branch == branch``.
        5. Persist via ``IStateRepository.save(updated)``.
        6. Release the lock.

        Raises:
            StateMutationConflictError: on lock timeout, branch mismatch, or
                unrecoverable state.
        """
        acquired = self._lock.acquire(timeout=_LOCK_TIMEOUT_SECONDS)
        if not acquired:
            raise StateMutationConflictError(
                f"Lock timeout acquiring mutation lock for branch '{branch}'.",
                (
                    "Another operation is holding the workflow state lock. "
                    "Retry after the current operation completes."
                ),
            )
        try:
            state = self._load_or_bootstrap(branch)
            updated = mutate(state)
            if updated.branch != branch:
                raise StateMutationConflictError(
                    (
                        f"Mutation returned state with branch '{updated.branch}' "
                        f"but expected '{branch}'."
                    ),
                    (
                        "Ensure the mutation callback preserves branch identity. "
                        "Do not change the 'branch' field inside the callback."
                    ),
                )
            self._state_repository.save(updated)
        finally:
            self._lock.release()

    def _load_or_bootstrap(self, branch: str) -> BranchState:
        """Load current state; use reconstructor or bootstrap for fresh branches."""
        try:
            return self._state_repository.load(branch)
        except (KeyError, FileNotFoundError, OSError, StateNotFoundError):
            pass

        # Bootstrap case: fresh branch being initialized — provide minimal placeholder.
        # initialize_branch callbacks ignore this completely and create a fresh BranchState.
        return BranchState(
            branch=branch,
            workflow_name="",
            current_phase="",
        )
