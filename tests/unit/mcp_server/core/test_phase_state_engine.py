"""Tests for PhaseStateEngine - Phase A.2 (RED phase)."""
from dataclasses import dataclass
from pathlib import Path

import pytest

from mcp_server.core.phase_state_engine import PhaseStateEngine


@pytest.fixture(autouse=True)
def cleanup_state_file():
    """Clean up state file before and after each test."""
    state_file = Path(".") / ".st3" / "state.json"

    # Clean before test
    if state_file.exists():
        state_file.unlink()

    yield

    # Clean after test
    if state_file.exists():
        state_file.unlink()


@dataclass
class MockProjectPlan:
    """Mock project plan for testing."""

    issue_number: int
    required_phases: list[str]
    current_phase: str


class TestPhaseStateEngineGetPhase:
    """Test PhaseStateEngine.get_phase() for retrieving current phase."""

    def test_get_phase_for_new_branch_returns_none(self):
        """Should return None for branch without state."""
        engine = PhaseStateEngine(workspace_root=Path("."))
        phase = engine.get_phase("feature/unknown-branch")
        assert phase is None

    def test_get_phase_returns_current_phase(self):
        """Should return current phase for tracked branch."""
        engine = PhaseStateEngine(workspace_root=Path("."))
        # Setup: initialize branch with phase
        engine.initialize_branch("feature/31-test", "discovery", issue_number=31)

        phase = engine.get_phase("feature/31-test")

        assert phase == "discovery"

    def test_get_phase_after_transition(self):
        """Should return updated phase after transition."""
        engine = PhaseStateEngine(workspace_root=Path("."))
        engine.initialize_branch("feature/31-test", "discovery", issue_number=31)
        engine.transition("feature/31-test", "discovery", "planning")

        phase = engine.get_phase("feature/31-test")

        assert phase == "planning"


class TestPhaseStateEngineInitializeBranch:
    """Test PhaseStateEngine.initialize_branch() for new branches."""

    def test_initialize_branch_creates_state(self):
        """Should create initial state for new branch."""
        engine = PhaseStateEngine(workspace_root=Path("."))

        result = engine.initialize_branch(
            "feature/31-test", "discovery", issue_number=31
        )

        assert result is True
        assert engine.get_phase("feature/31-test") == "discovery"

    def test_initialize_branch_stores_issue_mapping(self):
        """Should store branch->issue mapping."""
        engine = PhaseStateEngine(workspace_root=Path("."))

        engine.initialize_branch("feature/31-test", "discovery", issue_number=31)

        issue_num = engine.get_issue_for_branch("feature/31-test")
        assert issue_num == 31

    def test_initialize_branch_fails_if_already_exists(self):
        """Should fail if branch already initialized."""
        engine = PhaseStateEngine(workspace_root=Path("."))
        engine.initialize_branch("feature/31-test", "discovery", issue_number=31)

        result = engine.initialize_branch(
            "feature/31-test", "planning", issue_number=31
        )

        assert result is False


class TestPhaseStateEngineTransition:
    """Test PhaseStateEngine.transition() for phase changes."""

    def test_transition_valid_phase_change(self):
        """Should allow valid phase transition."""
        engine = PhaseStateEngine(workspace_root=Path("."))
        engine.initialize_branch("feature/31-test", "discovery", issue_number=31)

        result = engine.transition("feature/31-test", "discovery", "planning")

        assert result.success is True
        assert result.new_phase == "planning"
        assert engine.get_phase("feature/31-test") == "planning"

    def test_transition_records_history(self):
        """Should record transition in history."""
        engine = PhaseStateEngine(workspace_root=Path("."))
        engine.initialize_branch("feature/31-test", "discovery", issue_number=31)

        engine.transition("feature/31-test", "discovery", "planning")

        history = engine.get_transition_history("feature/31-test")
        assert len(history) >= 1
        assert history[-1]["from_phase"] == "discovery"
        assert history[-1]["to_phase"] == "planning"

    def test_transition_with_wrong_from_phase_fails(self):
        """Should fail if from_phase doesn't match current."""
        engine = PhaseStateEngine(workspace_root=Path("."))
        engine.initialize_branch("feature/31-test", "discovery", issue_number=31)

        result = engine.transition("feature/31-test", "planning", "design")

        assert result.success is False
        assert "Phase mismatch" in result.reason

    def test_transition_for_unknown_branch_fails(self):
        """Should fail for branch without state."""
        engine = PhaseStateEngine(workspace_root=Path("."))

        result = engine.transition("feature/unknown", "discovery", "planning")

        assert result.success is False
        assert "not initialized" in result.reason.lower()

    def test_transition_with_human_approval(self):
        """Should record human approval for transitions."""
        engine = PhaseStateEngine(workspace_root=Path("."))
        engine.initialize_branch("feature/31-test", "discovery", issue_number=31)

        result = engine.transition(
            "feature/31-test",
            "discovery",
            "planning",
            human_approval="Approved by user"
        )

        assert result.success is True
        history = engine.get_transition_history("feature/31-test")
        assert history[-1].get("human_approval") == "Approved by user"


class TestPhaseStateEngineGetProjectPlan:
    """Test PhaseStateEngine.get_project_plan() integration."""

    def test_get_project_plan_for_branch(self):
        """Should retrieve project plan via branch->issue mapping."""
        engine = PhaseStateEngine(workspace_root=Path("."))
        # Assume issue #31 has project plan in projects.json
        engine.initialize_branch("feature/31-test", "discovery", issue_number=31)

        plan = engine.get_project_plan("feature/31-test")

        # Should return plan or None (depends on projects.json)
        assert plan is None or isinstance(plan, dict)

    def test_get_project_plan_for_unknown_branch_returns_none(self):
        """Should return None for branch without state."""
        engine = PhaseStateEngine(workspace_root=Path("."))

        plan = engine.get_project_plan("feature/unknown")

        assert plan is None


class TestPhaseStateEnginePersistence:
    """Test PhaseStateEngine state persistence to .st3/state.json."""

    def test_state_persists_across_instances(self):
        """Should persist state to file and reload."""
        workspace = Path(".")
        engine1 = PhaseStateEngine(workspace_root=workspace)
        engine1.initialize_branch("feature/31-test", "discovery", issue_number=31)
        engine1.transition("feature/31-test", "discovery", "planning")

        # Create new instance (should load from file)
        engine2 = PhaseStateEngine(workspace_root=workspace)
        phase = engine2.get_phase("feature/31-test")

        assert phase == "planning"

    def test_state_file_created_in_st3_directory(self):
        """Should create .st3/state.json file."""
        workspace = Path(".")
        engine = PhaseStateEngine(workspace_root=workspace)
        engine.initialize_branch("feature/31-test", "discovery", issue_number=31)

        state_file = workspace / ".st3" / "state.json"
        assert state_file.exists()
