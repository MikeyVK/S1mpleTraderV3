# tests/mcp_server/unit/managers/test_phase_state_engine_c4_issue257.py
"""Tests for C_CYCLE_ORCHESTRATION behavior (Issue #257 Cycle 4).

@layer: Tests (Unit)
@dependencies: [pytest, tests.mcp_server.test_support, mcp_server.managers.phase_state_engine]
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.core.interfaces import GateReport, GateViolation
from mcp_server.managers.phase_contract_resolver import PhaseContractResolver
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.state_repository import InMemoryStateRepository
from tests.mcp_server.test_support import (
    make_phase_config_context,
    make_phase_state_engine,
    make_project_manager,
)


class BlockingCycleGateRunner:
    """Gate runner fake that blocks normal cycle transitions."""

    def __init__(self) -> None:
        self.enforce_calls: list[tuple[str, str, int | None]] = []

    def is_cycle_based_phase(self, workflow_name: str, phase: str) -> bool:
        del workflow_name
        return phase == "implementation"

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

    def is_cycle_based_phase(self, workflow_name: str, phase: str) -> bool:
        del workflow_name
        return phase == "implementation"

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


class ConfigAwareCycleGateRunner:
    """Gate runner fake that delegates cycle-based phase lookup to config."""

    def __init__(self, resolver: PhaseContractResolver) -> None:
        self._resolver = resolver
        self.enforce_calls: list[tuple[str, str, int | None]] = []
        self.inspect_calls: list[tuple[str, str, int | None]] = []

    def enforce(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[object] | None = None,
    ) -> GateReport:
        del checks
        self.enforce_calls.append((workflow_name, phase, cycle_number))
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
        return GateReport()

    def is_cycle_based_phase(self, workflow_name: str, phase: str) -> bool:
        return self._resolver.is_cycle_based_phase(workflow_name, phase)


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


def _write_cycle_based_tdd_configs(workspace_root: Path) -> None:
    """Write a minimal workflow where tdd, not implementation, is cycle-based."""
    config_dir = workspace_root / ".st3" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "workflows.yaml").write_text(
        (
            "version: '1'\n"
            "workflows:\n"
            "  feature:\n"
            "    name: feature\n"
            "    phases: [planning, tdd, documentation]\n"
        ),
        encoding="utf-8",
    )
    (config_dir / "workphases.yaml").write_text(
        (
            "version: '1'\n"
            "phases:\n"
            "  planning:\n"
            "    display_name: Planning\n"
            "  tdd:\n"
            "    display_name: TDD\n"
            "    subphases: [red, green, refactor]\n"
            "  documentation:\n"
            "    display_name: Documentation\n"
        ),
        encoding="utf-8",
    )
    (config_dir / "phase_contracts.yaml").write_text(
        (
            "workflows:\n"
            "  feature:\n"
            "    planning: {}\n"
            "    tdd:\n"
            "      cycle_based: true\n"
            "      subphases: [red, green, refactor]\n"
            "      commit_type_map:\n"
            "        red: test\n"
            "        green: feat\n"
            "        refactor: refactor\n"
            "    documentation: {}\n"
        ),
        encoding="utf-8",
    )


def _create_config_driven_cycle_engine(
    workspace_root: Path,
    initial_phase: str,
) -> tuple[object, str, ConfigAwareCycleGateRunner]:
    """Create one branch using local phase_contracts cycle_based config."""
    issue_number = 257
    branch = f"feature/257-{initial_phase}-cycle-based"
    repository = InMemoryStateRepository()

    _write_cycle_based_tdd_configs(workspace_root)
    project_manager = make_project_manager(workspace_root)
    project_manager.initialize_project(
        issue_number=issue_number,
        issue_title="Config-driven cycle phase",
        workflow_name="feature",
    )
    project_manager.save_planning_deliverables(
        issue_number,
        {
            "tdd_cycles": {
                "total": 2,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": "Cycle 1",
                        "deliverables": ["c1"],
                        "exit_criteria": "first cycle ready",
                    },
                    {
                        "cycle_number": 2,
                        "name": "Cycle 2",
                        "deliverables": ["c2"],
                        "exit_criteria": "second cycle ready",
                    },
                ],
            }
        },
    )
    gate_runner = ConfigAwareCycleGateRunner(
        PhaseContractResolver(make_phase_config_context(workspace_root, issue_number=issue_number))
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
        initial_phase=initial_phase,
    )
    state = engine.get_state(branch)
    repository.save(state.with_updates(current_cycle=1, last_cycle=0))
    return engine, branch, gate_runner


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


def test_cycle_transition_is_allowed_in_any_cycle_based_phase(workspace_root: Path) -> None:
    """Cycle transitions should follow cycle_based config instead of phase name."""
    engine, branch, gate_runner = _create_config_driven_cycle_engine(
        workspace_root,
        initial_phase="tdd",
    )

    result = engine.transition_cycle(branch=branch, to_cycle=2)

    state = engine.get_state(branch)
    assert result["success"] is True
    assert result["from_cycle"] == 1
    assert result["to_cycle"] == 2
    assert gate_runner.enforce_calls == [("feature", "tdd", 1)]
    assert state.current_cycle == 2


def test_cycle_transition_is_blocked_in_non_cycle_based_phase(workspace_root: Path) -> None:
    """Cycle transitions should fail generically outside cycle_based phases."""
    engine, branch, gate_runner = _create_config_driven_cycle_engine(
        workspace_root,
        initial_phase="planning",
    )

    with pytest.raises(ValueError, match="cycle-based") as exc_info:
        engine.transition_cycle(branch=branch, to_cycle=2)

    assert "implementation" not in str(exc_info.value)
    assert gate_runner.enforce_calls == []
