# mcp_server\core\interfaces\__init__.py
# template=generic version=f35abd82 created=2026-03-12T15:02Z updated=
"""Protocol interfaces for workflow state, gate orchestration, and PR status."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from mcp_server.config.schemas.phase_contracts_config import CheckSpec
    from mcp_server.managers.state_repository import BranchState


class PRStatus(Enum):
    """Lifecycle status of the PR on the current branch."""

    OPEN = "open"
    ABSENT = "absent"


@runtime_checkable
class IPRStatusReader(Protocol):
    """Read the cached PR status for a branch."""

    def get_pr_status(self, branch: str) -> PRStatus:
        """Return the current PR status for *branch*."""
        ...


@runtime_checkable
class IPRStatusWriter(Protocol):
    """Write the PR status for a branch into the cache."""

    def set_pr_status(self, branch: str, status: PRStatus) -> None:
        """Persist *status* for *branch* in the session cache."""
        ...


@dataclass(frozen=True)
class GateReport:
    """Result of one gate evaluation pass."""

    passing: tuple[str, ...] = ()
    blocking: tuple[str, ...] = ()
    details: dict[str, str] = field(default_factory=dict)


class GateViolation(ValueError):  # noqa: N818 - domain event name, not a technical error type
    """Raised when enforce mode encounters a blocking gate."""

    def __init__(self, message: str, report: GateReport) -> None:
        super().__init__(message)
        self.report = report


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


class IStateReconstructor(Protocol):
    """Reconstruct missing or invalid branch state for one branch."""

    def reconstruct(self, branch: str) -> BranchState:
        """Reconstruct state for one branch."""
        ...


class IWorkflowGateRunner(Protocol):
    """Evaluate resolved workflow gate checks in enforce or inspect mode."""

    def enforce(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[CheckSpec] | None = None,
    ) -> GateReport:
        """Run blocking gate evaluation."""
        ...

    def inspect(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[CheckSpec] | None = None,
    ) -> GateReport:
        """Run non-blocking gate inspection."""
        ...

    def is_cycle_based_phase(self, workflow_name: str, phase: str) -> bool:
        """Report whether the requested workflow phase supports TDD cycles."""
        ...
