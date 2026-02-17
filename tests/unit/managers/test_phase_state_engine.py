"""Tests for PhaseStateEngine entry/exit hooks.

Issue #146 Cycle 4: TDD phase lifecycle hooks.
"""

from pathlib import Path

import pytest

from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager


class TestTDDPhaseHooks:
    """Tests for TDD phase entry/exit hooks.
    
    Issue #146 Cycle 4: on_enter_tdd_phase and on_exit_tdd_phase.
    """

    @pytest.fixture()
    def setup_project(self, tmp_path: Path) -> tuple[Path, int]:
        """Create project with planning deliverables."""
        workspace_root = tmp_path
        issue_number = 146

        project_manager = ProjectManager(workspace_root=workspace_root)

        # Initialize project
        project_manager.initialize_project(
            issue_number=issue_number,
            issue_title="TDD Cycle Tracking",
            workflow_name="feature",
        )

        # Save planning deliverables (4 cycles)
        planning_deliverables = {
            "tdd_cycles": {
                "total": 4,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": "Schema & Storage",
                        "deliverables": ["Schema"],
                        "exit_criteria": "Tests pass",
                    },
                    {
                        "cycle_number": 2,
                        "name": "Validation Logic",
                        "deliverables": ["Validators"],
                        "exit_criteria": "All scenarios covered",
                    },
                    {
                        "cycle_number": 3,
                        "name": "Discovery Tools",
                        "deliverables": ["get_work_context"],
                        "exit_criteria": "Tools return cycle info",
                    },
                    {
                        "cycle_number": 4,
                        "name": "Transition Tools",
                        "deliverables": ["transition_cycle", "force_cycle_transition"],
                        "exit_criteria": "All transitions working",
                    },
                ],
            }
        }
        project_manager.save_planning_deliverables(
            issue_number=issue_number, planning_deliverables=planning_deliverables
        )

        return workspace_root, issue_number

    def test_on_enter_tdd_phase_initializes_cycle_1(
        self, setup_project: tuple[Path, int]
    ) -> None:
        """Test that entering TDD phase auto-initializes cycle 1."""
        # Arrange
        workspace_root, issue_number = setup_project
        branch = "feature/146-tdd-cycle-tracking"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize branch in design phase
        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="design"
        )

        # Verify no TDD cycle yet
        state = state_engine.get_state(branch)
        assert state.get("current_tdd_cycle") is None

        # Act
        state_engine.on_enter_tdd_phase(branch, issue_number)

        # Assert
        state = state_engine.get_state(branch)
        assert state.get("current_tdd_cycle") == 1
        assert state.get("last_tdd_cycle") == 0

    def test_on_enter_tdd_phase_blocks_without_planning_deliverables(
        self, tmp_path: Path
    ) -> None:
        """Test that entering TDD phase blocks if planning deliverables missing."""
        # Arrange
        workspace_root = tmp_path
        issue_number = 146
        branch = "feature/146-tdd-cycle-tracking"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize project WITHOUT planning deliverables
        project_manager.initialize_project(
            issue_number=issue_number,
            issue_title="TDD Cycle Tracking",
            workflow_name="feature",
        )

        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="design"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="planning deliverables"):
            state_engine.on_enter_tdd_phase(branch, issue_number)

    def test_on_exit_tdd_phase_preserves_last_cycle(
        self, setup_project: tuple[Path, int]
    ) -> None:
        """Test that exiting TDD phase preserves last_tdd_cycle."""
        # Arrange
        workspace_root, issue_number = setup_project
        branch = "feature/146-tdd-cycle-tracking"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize in TDD phase at cycle 3
        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="tdd"
        )
        state = state_engine.get_state(branch)
        state["current_tdd_cycle"] = 3
        state_engine._save_state(branch, state)

        # Act
        state_engine.on_exit_tdd_phase(branch)

        # Assert
        state = state_engine.get_state(branch)
        assert state.get("last_tdd_cycle") == 3
        assert state.get("current_tdd_cycle") is None

    def test_on_exit_tdd_phase_validates_completion(
        self, setup_project: tuple[Path, int]
    ) -> None:
        """Test that exiting TDD phase validates all cycles completed."""
        # Arrange
        workspace_root, issue_number = setup_project
        branch = "feature/146-tdd-cycle-tracking"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize in TDD phase at cycle 2 (not completed)
        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="tdd"
        )
        state = state_engine.get_state(branch)
        state["current_tdd_cycle"] = 2
        state_engine._save_state(branch, state)

        # Act
        # Design decision: Allow exit with warning (logs but doesn't block)
        state_engine.on_exit_tdd_phase(branch)

        # Assert
        state = state_engine.get_state(branch)
        assert state.get("last_tdd_cycle") == 2
        assert state.get("current_tdd_cycle") is None


class TestTransitionHooksWiring:
    """Tests that transition() automatically calls entry/exit hooks (Issue #146 Cycle 5 D3)."""

    @pytest.fixture()
    def setup_project(self, tmp_path: Path) -> tuple[Path, int]:
        """Create project with planning deliverables."""
        workspace_root = tmp_path
        issue_number = 999

        project_manager = ProjectManager(workspace_root=workspace_root)
        project_manager.initialize_project(
            issue_number=issue_number,
            issue_title="Hook Wiring Test",
            workflow_name="feature",
        )
        project_manager.save_planning_deliverables(
            issue_number=issue_number,
            planning_deliverables={"tdd_cycles": {"total": 1, "cycles": [
                {"cycle_number": 1, "name": "Basic", "deliverables": ["A"], "exit_criteria": "pass"}
            ]}},
        )
        return workspace_root, issue_number

    def test_transition_to_tdd_calls_enter_hook(
        self, setup_project: tuple[Path, int]
    ) -> None:
        """Test that transition() to 'tdd' auto-calls on_enter_tdd_phase (Issue #146)."""
        workspace_root, issue_number = setup_project
        branch = "feature/999-hook-wiring"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize branch in design phase
        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="design"
        )

        # Verify no TDD cycle before transition
        state = state_engine.get_state(branch)
        assert state.get("current_tdd_cycle") is None

        # Transition to TDD - should auto-call on_enter_tdd_phase
        state_engine.transition(branch=branch, to_phase="tdd")

        # Assert: hook was triggered and cycle 1 was initialized
        state = state_engine.get_state(branch)
        assert state.get("current_tdd_cycle") == 1, (
            "on_enter_tdd_phase was not called by transition() - "
            "current_tdd_cycle should be 1 after entering TDD phase"
        )

    def test_transition_from_tdd_calls_exit_hook(
        self, setup_project: tuple[Path, int]
    ) -> None:
        """Test that transition() from 'tdd' auto-calls on_exit_tdd_phase (Issue #146)."""
        workspace_root, issue_number = setup_project
        branch = "feature/999-hook-wiring"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize branch in TDD phase at cycle 2
        state_engine.initialize_branch(
            branch=branch, issue_number=issue_number, initial_phase="tdd"
        )
        state = state_engine.get_state(branch)
        state["current_tdd_cycle"] = 2
        state_engine._save_state(branch, state)

        # Transition away from TDD - should auto-call on_exit_tdd_phase
        state_engine.transition(branch=branch, to_phase="integration")

        # Assert: hook was triggered and last_tdd_cycle was preserved
        state = state_engine.get_state(branch)
        assert state.get("last_tdd_cycle") == 2, (
            "on_exit_tdd_phase was not called by transition() - "
            "last_tdd_cycle should be 2 after exiting TDD phase"
        )
        assert state.get("current_tdd_cycle") is None, (
            "current_tdd_cycle should be None after exiting TDD phase"
        )
