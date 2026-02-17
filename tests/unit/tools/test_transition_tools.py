"""Tests for Transition Tools (transition_cycle, force_cycle_transition).

Issue #146 Cycle 4: TDD Cycle transition management.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.tools.transition_tools import (
    TransitionCycleInput,
    TransitionCycleTool,
)


class TestTransitionCycleTool:
    """Tests for transition_cycle tool.
    
    Issue #146 Cycle 4: Sequential cycle progressions with validation.
    """

    @pytest.fixture()
    def tool(self) -> TransitionCycleTool:
        """Fixture to instantiate TransitionCycleTool."""
        return TransitionCycleTool()

    @pytest.fixture()
    def setup_project(self, tmp_path: Path) -> tuple[Path, int]:
        """Create project with planning deliverables and state."""
        from mcp_server.managers.project_manager import ProjectManager
        from mcp_server.managers.phase_state_engine import PhaseStateEngine

        workspace_root = tmp_path
        issue_number = 146

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

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
                        "deliverables": ["transition_cycle"],
                        "exit_criteria": "All transitions working",
                    },
                ],
            }
        }
        project_manager.save_planning_deliverables(issue_number, planning_deliverables)

        # Initialize TDD phase with cycle 1
        state_engine.initialize_branch(
            branch="feature/146-tdd-cycle-tracking",
            issue_number=issue_number,
            initial_phase="tdd",
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        state["current_tdd_cycle"] = 1
        state_engine._save_state("feature/146-tdd-cycle-tracking", state)

        return workspace_root, issue_number

    @pytest.mark.asyncio
    async def test_transition_to_next_cycle_succeeds(
        self, tool: TransitionCycleTool, setup_project: tuple[Path, int]
    ) -> None:
        """Test successful forward transition from cycle 1 to 2.
        
        Issue #146 Cycle 4: Sequential progression validation.
        """
        workspace_root, issue_number = setup_project

        # Mock git and settings
        with (
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git

            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(TransitionCycleInput(to_cycle=2))

        # Assert successful transition
        assert not result.is_error, f"Expected success: {result.content}"
        
        # Check state updated
        from mcp_server.managers.project_manager import ProjectManager
        from mcp_server.managers.phase_state_engine import PhaseStateEngine

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        assert state["current_tdd_cycle"] == 2, "Current cycle should be 2"
        assert state["last_tdd_cycle"] == 1, "Last cycle should be preserved"

    @pytest.mark.asyncio
    async def test_transition_blocks_backward_transition(
        self, tool: TransitionCycleTool, setup_project: tuple[Path, int]
    ) -> None:
        """Test that backward transitions are blocked.
        
        Issue #146 Cycle 4: Forward-only enforcement.
        """
        workspace_root, issue_number = setup_project

        # Set current cycle to 2
        from mcp_server.managers.project_manager import ProjectManager
        from mcp_server.managers.phase_state_engine import PhaseStateEngine

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        state["current_tdd_cycle"] = 2
        state_engine._save_state("feature/146-tdd-cycle-tracking", state)

        #  Mock git
        with (
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git

            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(TransitionCycleInput(to_cycle=1))

        # Assert blocked
        assert result.is_error, "Expected backward transition to be blocked"
        text = result.content[0]["text"]
        assert "backwards" in text.lower() or "forward-only" in text.lower()
        assert "force_cycle_transition" in text

    @pytest.mark.asyncio
    async def test_transition_blocks_non_sequential_jump(
        self, tool: TransitionCycleTool, setup_project: tuple[Path, int]
    ) -> None:
        """Test that skipping cycles requires force_cycle_transition.
        
        Issue #146 Cycle 4: Sequential validation.
        """
        workspace_root, issue_number = setup_project

        # Mock git
        with (
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git

            mock_settings.server.workspace_root = workspace_root

            # Try to jump from cycle 1 to 3 (skipping 2)
            result = await tool.execute(TransitionCycleInput(to_cycle=3))

        # Assert blocked
        assert result.is_error, "Expected non-sequential jump to be blocked"
        text = result.content[0]["text"]
        assert "sequential" in text.lower() or "skip" in text.lower()
        assert "force_cycle_transition" in text

    @pytest.mark.asyncio
    async def test_transition_blocks_outside_tdd_phase(
        self, tool: TransitionCycleTool, setup_project: tuple[Path, int]
    ) -> None:
        """Test that transition only works during TDD phase.
        
        Issue #146 Cycle 4: Phase enforcement.
        """
        workspace_root, issue_number = setup_project

        # Change phase to design
        from mcp_server.managers.project_manager import ProjectManager
        from mcp_server.managers.phase_state_engine import PhaseStateEngine

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        state["current_phase"] = "design"
        state_engine._save_state("feature/146-tdd-cycle-tracking", state)

        # Mock git
        with (
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git

            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(TransitionCycleInput(to_cycle=2))

        # Assert blocked
        assert result.is_error, "Expected transition to be blocked outside TDD phase"
        text = result.content[0]["text"]
        assert "tdd phase" in text.lower()
