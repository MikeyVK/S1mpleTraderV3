"""Tests for C_CYCLE_ORCHESTRATION behavior (Issue #257 Cycle 4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.core.interfaces import GateReport, GateViolation
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.state_repository import InMemoryStateRepository
from tests.mcp_server.test_support import make_phase_state_engine, make_project_manager


class BlockingCycleGateRunner:
    """Gate runner fake that blocks normal cycle transitions."""

    def __init__(self) -> None:
        self.enforce_calls: list[tuple[str, str, int | None]] = []

    def enforce(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[object] | None = None,
    ) -> GateReport:
        del checks
        self.enforce_calls.append((workflow_name, phase, cycle_number))
        report = GateReport(
            passing=(),
            blocking=("cycle-docs",),
            details={"cycle-docs": "missing cycle transition evidence"},
        )
        raise GateViolation("missing cycle transition evidence", report)

    def inspect(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[object] | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number, checks
        return GateReport()


class ReportingCycleGateRunner:
    """Gate runner fake that reports force-transition inspection results."""

    def __init__(self) -> None:
        self.inspect_calls: list[tuple[str, str, int | None]] = []

    def enforce(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[object] | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number, checks
        return GateReport()

    def inspect(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[object] | None = None,
    ) -> GateReport:
        del checks
        self.inspect_calls.append((workflow_name, phase, cycle_number))
        return GateReport(
            passing=("cycle-docs",),
            blocking=("cycle-checklist",),
            details={"cycle-checklist": "missing force-transition checklist"},
        )


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Temporary workspace root for cycle-orchestration tests."""
    return tmp_path


@pytest.fixture
def project_manager(workspace_root: Path) -> ProjectManager:
    """ProjectManager bound to the temp workspace."""
    return make_project_manager(workspace_root)


def _create_cycle_engine(
    workspace_root: Path,
    project_manager: ProjectManager,
    gate_runner: object,
) -> tuple[object, str]:
    """Create one implementation-phase branch ready for cycle transitions."""
    issue_number = 257
    branch = "feature/257-cycle-orchestration"
    repository = InMemoryStateRepository()

    project_manager.initialize_project(
        issue_number=issue_number,
        issue_title="Cycle orchestration",
        workflow_name="feature",
    )
    project_manager.save_planning_deliverables(
        issue_number,
        {
            "tdd_cycles": {
                "total": 4,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": "Gate API",
                        "deliverables": ["c1"],
                        "exit_criteria": "gate runner ready",
                    },
                    {
                        "cycle_number": 2,
                        "name": "Gate wiring",
                        "deliverables": ["c2"],
                        "exit_criteria": "phase transitions delegated",
                    },
                    {
                        "cycle_number": 3,
                        "name": "State recovery",
                        "deliverables": ["c3"],
                        "exit_criteria": "get_state is pure",
                    },
                    {
                        "cycle_number": 4,
                        "name": "Cycle orchestration",
                        "deliverables": ["c4"],
                        "exit_criteria": "cycle tools are thin",
                    },
                ],
            }
        },
    )
    engine = make_phase_state_engine(
        workspace_root,
        project_manager=project_manager,
        state_repository=repository,
        workflow_gate_runner=gate_runner,
    )
    engine.initialize_branch(
        branch=branch,
        issue_number=issue_number,
        initial_phase="implementation",
    )
    engine.on_enter_implementation_phase(branch, issue_number)
    return engine, branch


def test_transition_cycle_raises_when_gate_blocks(
    workspace_root: Path,
    project_manager: ProjectManager,
) -> None:
    """transition_cycle() must use shared gate enforcement before persisting state."""
    gate_runner = BlockingCycleGateRunner()
    engine, branch = _create_cycle_engine(
        workspace_root,
        project_manager,
        gate_runner=gate_runner,
    )

    with pytest.raises(GateViolation, match="missing cycle transition evidence"):
        engine.transition_cycle(branch=branch, to_cycle=2)

    state = engine.get_state(branch)
    assert state.current_cycle == 1
    assert gate_runner.enforce_calls == [("feature", "implementation", 1)]


def test_force_cycle_transition_returns_gate_inspection_report(
    workspace_root: Path,
    project_manager: ProjectManager,
) -> None:
    """force_cycle_transition() must return shared gate inspection details."""
    gate_runner = ReportingCycleGateRunner()
    engine, branch = _create_cycle_engine(
        workspace_root,
        project_manager,
        gate_runner=gate_runner,
    )

    result = engine.force_cycle_transition(
        branch=branch,
        to_cycle=3,
        skip_reason="audited forward skip",
        human_approval="Verifier approved on 2026-04-04",
    )

    state = engine.get_state(branch)
    history_entry = state.cycle_history[-1]

    assert result["success"] is True
    assert result["from_cycle"] == 1
    assert result["to_cycle"] == 3
    assert result["skipped_gates"] == ["cycle-checklist"]
    assert result["passing_gates"] == ["cycle-docs"]
    assert result["gate_report"] == {
        "passing": ["cycle-docs"],
        "blocking": ["cycle-checklist"],
        "details": {"cycle-checklist": "missing force-transition checklist"},
    }
    assert gate_runner.inspect_calls == [("feature", "implementation", 1)]
    assert state.current_cycle == 3
    assert state.last_cycle == 1
    assert history_entry["forced"] is True
    assert history_entry["skipped_cycles"] == [2]
