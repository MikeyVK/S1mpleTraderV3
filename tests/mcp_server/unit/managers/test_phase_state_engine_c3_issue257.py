"""Tests for C_STATE_RECOVERY behavior (Issue #257 Cycle 3).

Cycle 3 goals covered here:
- transition() reconstructs missing state through IStateReconstructor.
- reconstructed state is saved before transition flow continues.
- force_transition() reconstructs missing state through the same recovery path.
- get_state() is a pure query and does not reconstruct or persist on failure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server.core.interfaces import GateReport
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.state_repository import BranchState
from tests.mcp_server.test_support import make_phase_state_engine, make_project_manager


class MissingThenPersistingRepository:
    """Repository that simulates one missing-state load until a save happens."""

    def __init__(self) -> None:
        self._states: dict[str, BranchState] = {}
        self.save_count = 0

    def load(self, branch: str) -> BranchState:
        if branch not in self._states:
            raise FileNotFoundError(branch)
        return self._states[branch]

    def save(self, state: BranchState) -> None:
        self.save_count += 1
        self._states[state.branch] = state


class RaisingRepository:
    """Repository that always raises on load and tracks whether save was attempted."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.saved_states: list[BranchState] = []

    def load(self, branch: str) -> BranchState:
        raise self._exc

    def save(self, state: BranchState) -> None:
        self.saved_states.append(state)


class PassingGateRunner:
    """Gate runner fake that allows every transition."""

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
        del workflow_name, phase, cycle_number, checks
        return GateReport()


class ReportingGateRunner(PassingGateRunner):
    """Gate runner fake that reports forced-transition audit information."""

    def inspect(
        self,
        workflow_name: str,
        phase: str,
        cycle_number: int | None = None,
        checks: list[object] | None = None,
    ) -> GateReport:
        del workflow_name, phase, cycle_number, checks
        return GateReport(
            passing=("design-doc",),
            blocking=("planning-doc",),
            details={"planning-doc": "missing planning document"},
        )


class FixedStateReconstructor:
    """State reconstructor fake that returns one prebuilt BranchState."""

    def __init__(self, state: BranchState) -> None:
        self._state = state

    def reconstruct(self, branch: str) -> BranchState:
        return self._state if self._state.branch == branch else self._state.with_updates(branch=branch)


class ExplodingStateReconstructor:
    """State reconstructor fake that must never be used in pure-query tests."""

    def reconstruct(self, branch: str) -> BranchState:
        raise AssertionError(f"reconstruct should not be called in this test: {branch}")


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Temporary workspace root for cycle-3 recovery tests."""
    return tmp_path


@pytest.fixture
def project_manager(workspace_root: Path) -> ProjectManager:
    """Project manager bound to the temp workspace."""
    return make_project_manager(workspace_root)


def _make_branch_state(
    project_manager: ProjectManager,
    branch: str,
    issue_number: int,
    current_phase: str,
    current_cycle: int | None = None,
) -> BranchState:
    """Build one reconstructed state payload for the active issue."""
    project = project_manager.get_project_plan(issue_number)
    assert project is not None
    return BranchState(
        branch=branch,
        issue_number=issue_number,
        workflow_name=project["workflow_name"],
        current_phase=current_phase,
        current_cycle=current_cycle,
        last_cycle=None,
        cycle_history=[],
        required_phases=project.get("required_phases", []),
        execution_mode=project.get("execution_mode", "normal"),
        issue_title=project.get("issue_title"),
        parent_branch=project.get("parent_branch"),
        created_at="2026-04-04T00:00:00+00:00",
        transitions=[],
        reconstructed=True,
    )


def test_transition_reconstructs_state_via_state_reconstructor_when_load_fails(
    workspace_root: Path,
    project_manager: ProjectManager,
) -> None:
    """transition() must recover missing state through the injected reconstructor."""
    branch = "feature/257-c3-transition"
    project_manager.initialize_project(
        issue_number=257,
        issue_title="Cycle 3 transition recovery",
        workflow_name="feature",
    )
    repository = MissingThenPersistingRepository()
    engine = make_phase_state_engine(
        workspace_root,
        project_manager=project_manager,
        state_repository=repository,
        workflow_gate_runner=PassingGateRunner(),
        state_reconstructor=FixedStateReconstructor(
            _make_branch_state(project_manager, branch, 257, current_phase="research")
        ),
    )

    result = engine.transition(branch=branch, to_phase="planning")

    assert result == {"success": True, "from_phase": "research", "to_phase": "planning"}
    assert repository.load(branch).current_phase == "planning"



def test_transition_saves_reconstructed_state_before_continuing(
    workspace_root: Path,
    project_manager: ProjectManager,
) -> None:
    """transition() must save reconstructed implementation state before exit-hook logic runs."""
    branch = "feature/257-c3-save-before-continue"
    project_manager.initialize_project(
        issue_number=257,
        issue_title="Cycle 3 save before continue",
        workflow_name="feature",
    )
    repository = MissingThenPersistingRepository()
    engine = make_phase_state_engine(
        workspace_root,
        project_manager=project_manager,
        state_repository=repository,
        workflow_gate_runner=PassingGateRunner(),
        state_reconstructor=FixedStateReconstructor(
            _make_branch_state(
                project_manager,
                branch,
                257,
                current_phase="implementation",
                current_cycle=2,
            )
        ),
    )

    result = engine.transition(branch=branch, to_phase="validation")
    recovered_state = repository.load(branch)

    assert result == {"success": True, "from_phase": "implementation", "to_phase": "validation"}
    assert repository.save_count >= 2
    assert recovered_state.last_cycle == 2
    assert recovered_state.current_cycle is None
    assert recovered_state.current_phase == "validation"



def test_force_transition_loads_state_or_reconstructs_when_missing(
    workspace_root: Path,
    project_manager: ProjectManager,
) -> None:
    """force_transition() must use the same recovery path when branch state is missing."""
    branch = "feature/257-c3-force"
    project_manager.initialize_project(
        issue_number=257,
        issue_title="Cycle 3 force recovery",
        workflow_name="feature",
    )
    repository = MissingThenPersistingRepository()
    engine = make_phase_state_engine(
        workspace_root,
        project_manager=project_manager,
        state_repository=repository,
        workflow_gate_runner=ReportingGateRunner(),
        state_reconstructor=FixedStateReconstructor(
            _make_branch_state(project_manager, branch, 257, current_phase="planning")
        ),
    )

    result = engine.force_transition(
        branch=branch,
        to_phase="design",
        skip_reason="audited bypass for recovery test",
        human_approval="Verifier approved on 2026-04-04",
    )

    assert result["success"] is True
    assert result["from_phase"] == "planning"
    assert result["to_phase"] == "design"
    assert result["skipped_gates"] == ["planning-doc"]
    assert result["passing_gates"] == ["design-doc"]
    assert repository.load(branch).current_phase == "design"



def test_get_state_does_not_reconstruct_or_save_on_load_failure(
    workspace_root: Path,
    project_manager: ProjectManager,
) -> None:
    """get_state() must not reconstruct or persist when the repository load fails."""
    project_manager.initialize_project(
        issue_number=257,
        issue_title="Cycle 3 pure query",
        workflow_name="feature",
    )
    repository = RaisingRepository(FileNotFoundError("missing state"))
    engine = make_phase_state_engine(
        workspace_root,
        project_manager=project_manager,
        state_repository=repository,
        workflow_gate_runner=PassingGateRunner(),
        state_reconstructor=ExplodingStateReconstructor(),
    )

    with pytest.raises(FileNotFoundError, match="missing state"):
        engine.get_state("feature/257-c3-pure-query")

    assert repository.saved_states == []



def test_get_state_raises_when_repository_load_fails(
    workspace_root: Path,
    project_manager: ProjectManager,
) -> None:
    """get_state() must surface repository errors as a pure query API."""
    project_manager.initialize_project(
        issue_number=257,
        issue_title="Cycle 3 repository failure",
        workflow_name="feature",
    )
    repository = RaisingRepository(OSError("disk failure"))
    engine = make_phase_state_engine(
        workspace_root,
        project_manager=project_manager,
        state_repository=repository,
        workflow_gate_runner=PassingGateRunner(),
        state_reconstructor=ExplodingStateReconstructor(),
    )

    with pytest.raises(OSError, match="disk failure"):
        engine.get_state("feature/257-c3-io-error")

    assert repository.saved_states == []
