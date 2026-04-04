# mcp_server\core\interfaces\__init__.py
# template=generic version=f35abd82 created=2026-03-12T15:02Z updated=
"""Protocol interfaces for workflow state and gate orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from mcp_server.config.schemas.phase_contracts_config import CheckSpec
    from mcp_server.managers.state_repository import BranchState


@dataclass(frozen=True)
class GateReport:
    """Result of one gate evaluation pass."""

    passing: tuple[str, ...] = ()
    blocking: tuple[str, ...] = ()
    details: dict[str, str] = field(default_factory=dict)


class GateViolation(ValueError):  # noqa: N818
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
