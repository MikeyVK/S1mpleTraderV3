"""Tests for PhaseStateEngine gate relocation (Issue #229 Cycle 2).

GAP-01: Planning exit is silent — add on_exit_planning_phase hard gate.
GAP-02: planning_deliverables check in on_enter_tdd_phase is wrong layer —
        remove it there; gate belongs at planning exit, not TDD entry.

C2 Deliverables:
  D2.1: on_exit_planning_phase wired to WorkphasesConfig + DeliverableChecker (Option B).
  D2.2: on_enter_tdd_phase no longer raises when planning_deliverables absent.
"""

from pathlib import Path

import pytest

from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Temporary workspace root with .st3/workphases.yaml providing exit_requires."""
    st3 = tmp_path / ".st3"
    st3.mkdir()
    (st3 / "workphases.yaml").write_text(
        """
phases:
  planning:
    display_name: "Planning"
    exit_requires:
      - key: "planning_deliverables"
        description: "TDD cycle breakdown"
  tdd:
    display_name: "TDD"
    entry_expects:
      - key: "planning_deliverables"
        description: "Expected from planning"
  design:
    display_name: "Design"
"""
    )
    return tmp_path


@pytest.fixture
def project_manager(workspace_root: Path) -> ProjectManager:
    """ProjectManager bound to tmp workspace."""
    return ProjectManager(workspace_root=workspace_root)


@pytest.fixture
def engine(workspace_root: Path, project_manager: ProjectManager) -> PhaseStateEngine:
    """PhaseStateEngine bound to tmp workspace."""
    return PhaseStateEngine(workspace_root=workspace_root, project_manager=project_manager)


# ---------------------------------------------------------------------------
# C2 — on_exit_planning_phase (GAP-01)
# ---------------------------------------------------------------------------


class TestOnExitPlanningPhase:
    """on_exit_planning_phase uses WorkphasesConfig + DeliverableChecker (Option B)."""

    def test_on_exit_planning_phase_raises_when_planning_deliverables_absent(
        self,
        engine: PhaseStateEngine,
        project_manager: ProjectManager,
    ) -> None:
        """on_exit_planning_phase raises ValueError when planning_deliverables absent.

        Issue #229 C2 — GAP-01: gate must fire at planning exit, not silently pass.
        """
        project_manager.initialize_project(
            issue_number=229,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        # No planning_deliverables saved → exit_requires key missing → should raise
        with pytest.raises(ValueError, match="planning_deliverables"):
            engine.on_exit_planning_phase(branch="feature/229-test", issue_number=229)

    def test_on_exit_planning_phase_passes_when_planning_deliverables_present(
        self,
        engine: PhaseStateEngine,
        project_manager: ProjectManager,
    ) -> None:
        """on_exit_planning_phase passes silently when planning_deliverables present.

        Issue #229 C2: gate must not block valid transitions.
        """
        project_manager.initialize_project(
            issue_number=229,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        project_manager.save_planning_deliverables(
            229,
            {
                "tdd_cycles": {
                    "total": 1,
                    "cycles": [{"cycle_number": 1, "deliverables": ["D1"], "exit_criteria": "x"}],
                }
            },
        )
        # Should not raise
        engine.on_exit_planning_phase(branch="feature/229-test", issue_number=229)

    def test_on_exit_planning_phase_uses_workphases_config_for_required_keys(
        self,
        engine: PhaseStateEngine,
        project_manager: ProjectManager,
        workspace_root: Path,
    ) -> None:
        """on_exit_planning_phase reads exit_requires from workphases.yaml, not hardcoded.

        Issue #229 C2 — D2.1: gate is WorkphasesConfig-driven (Option B).
        A phase with no exit_requires in workphases.yaml must pass unconditionally.
        """
        # Write workphases.yaml WITHOUT exit_requires on planning
        (workspace_root / ".st3" / "workphases.yaml").write_text(
            "phases:\n  planning:\n    display_name: Planning\n"
        )
        project_manager.initialize_project(
            issue_number=230,
            issue_title="No planning gate",
            workflow_name="feature",
        )
        # No planning_deliverables AND no exit_requires → must NOT raise
        engine.on_exit_planning_phase(branch="feature/230-test", issue_number=230)

    def test_on_exit_planning_phase_runs_deliverable_checker_on_validates_entries(
        self,
        engine: PhaseStateEngine,
        project_manager: ProjectManager,
    ) -> None:
        """on_exit_planning_phase runs DeliverableChecker on planning_deliverables.validates.

        Issue #229 C2 — D2.1: wired to structural checker (Option B full flow).
        A validates entry that fails must propagate as DeliverableCheckError (ValueError).
        """
        project_manager.initialize_project(
            issue_number=229,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        # planning_deliverables exists but has a failing validates entry
        project_manager.save_planning_deliverables(
            229,
            {
                "tdd_cycles": {
                    "total": 1,
                    "cycles": [{"cycle_number": 1, "deliverables": ["D1"], "exit_criteria": "x"}],
                },
                "validates": [
                    {
                        "id": "gate-check",
                        "type": "file_exists",
                        "file": "nonexistent/missing.py",
                    }
                ],
            },
        )
        # DeliverableChecker must raise on the failing file_exists
        with pytest.raises(ValueError, match="gate-check"):
            engine.on_exit_planning_phase(branch="feature/229-test", issue_number=229)


# ---------------------------------------------------------------------------
# C2 — on_enter_tdd_phase no longer checks planning_deliverables (GAP-02)
# ---------------------------------------------------------------------------


class TestOnEnterTddPhaseGateRemoved:
    """on_enter_tdd_phase must not check planning_deliverables (gate moved to exit)."""

    def test_on_enter_tdd_phase_does_not_raise_when_planning_deliverables_absent(
        self,
        engine: PhaseStateEngine,
        project_manager: ProjectManager,
    ) -> None:
        """on_enter_tdd_phase no longer raises when planning_deliverables absent.

        Issue #229 C2 — GAP-02: planning gate moved to on_exit_planning_phase.
        TDD entry only initializes cycle state; it must not re-validate planning.
        """
        project_manager.initialize_project(
            issue_number=229,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        engine.initialize_branch(
            branch="feature/229-test",
            issue_number=229,
            initial_phase="tdd",
        )
        # No planning_deliverables → must NOT raise after GAP-02 fix
        engine.on_enter_tdd_phase(branch="feature/229-test", issue_number=229)

    def test_transition_from_planning_calls_exit_planning_gate(
        self,
        engine: PhaseStateEngine,
        project_manager: ProjectManager,
    ) -> None:
        """transition() from planning calls on_exit_planning_phase gate.

        Issue #229 C2: gate is wired into transition() dispatch so it cannot be
        bypassed by callers who call transition() directly.
        """
        project_manager.initialize_project(
            issue_number=229,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        engine.initialize_branch(
            branch="feature/229-test",
            issue_number=229,
            initial_phase="planning",
        )
        # No planning_deliverables → transition from planning must raise via gate
        with pytest.raises(ValueError, match="planning_deliverables"):
            engine.transition(branch="feature/229-test", to_phase="design")
