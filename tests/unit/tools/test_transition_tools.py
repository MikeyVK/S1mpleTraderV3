"""Tests for Transition Tools (transition_cycle, force_cycle_transition).

Issue #146 Cycle 4: TDD Cycle transition management.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.tools.transition_tools import (
    ForceCycleTransitionInput,
    ForceCycleTransitionTool,
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


class TestForceCycleTransitionTool:
    """Tests for force_cycle_transition tool.
    
    Issue #146 Cycle 4: Forced transitions with audit trail.
    """

    @pytest.fixture()
    def tool(self) -> ForceCycleTransitionTool:
        """Fixture to instantiate ForceCycleTransitionTool."""
        return ForceCycleTransitionTool()

    @pytest.fixture()
    def setup_forced_project(self, tmp_path: Path) -> tuple[Path, int]:
        """Create project in TDD phase at cycle 2 for forced transitions."""
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
                        "deliverables": ["transition_cycle", "force_cycle_transition"],
                        "exit_criteria": "All transitions working",
                    },
                ],
            }
        }
        project_manager.save_planning_deliverables(
            issue_number=issue_number, planning_deliverables=planning_deliverables
        )

        # Transition to TDD phase and set cycle to 2
        branch = "feature/146-tdd-cycle-tracking"
        state = state_engine.get_state(branch)
        state["current_phase"] = "tdd"
        state["current_tdd_cycle"] = 2
        state["last_tdd_cycle"] = 1
        state["tdd_cycle_history"] = []
        state_engine._save_state(branch, state)

        return workspace_root, issue_number

    @pytest.mark.asyncio()
    async def test_force_backward_transition_succeeds(
        self, tool: ForceCycleTransitionTool, setup_forced_project: tuple[Path, int]
    ) -> None:
        """Test that forced backward transition (2→1) works with approval."""
        workspace_root, issue_number = setup_forced_project

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git

            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(
                ForceCycleTransitionInput(
                    to_cycle=1,
                    skip_reason="Re-testing schema changes",
                    human_approval="John approved on 2026-02-17",
                )
            )

        # Assert success
        assert not result.is_error, f"Expected success, got error: {result.content}"
        text = result.content[0]["text"]
        assert "✅" in text or "Forced" in text
        assert "1" in text

        # Verify state updated
        from mcp_server.managers.phase_state_engine import PhaseStateEngine
        from mcp_server.managers.project_manager import ProjectManager

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        assert state["current_tdd_cycle"] == 1
        assert state["last_tdd_cycle"] == 2

        # Verify audit trail
        history = state.get("tdd_cycle_history", [])
        assert len(history) > 0, "Expected audit trail entry"
        last_entry = history[-1]
        assert last_entry.get("from_cycle") == 2
        assert last_entry.get("to_cycle") == 1
        assert "Re-testing schema changes" in last_entry.get("skip_reason", "")
        assert "John approved" in last_entry.get("human_approval", "")

    @pytest.mark.asyncio()
    async def test_force_skip_transition_succeeds(
        self, tool: ForceCycleTransitionTool, setup_forced_project: tuple[Path, int]
    ) -> None:
        """Test that forced skip transition (2→4) works with approval."""
        workspace_root, issue_number = setup_forced_project

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git

            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(
                ForceCycleTransitionInput(
                    to_cycle=4,
                    skip_reason="Cycle 3 covered by integration tests",
                    human_approval="Jane approved on 2026-02-17",
                )
            )

        # Assert success
        assert not result.is_error, f"Expected success, got error: {result.content}"
        text = result.content[0]["text"]
        assert "✅" in text or "Forced" in text
        assert "4" in text

        # Verify state
        from mcp_server.managers.phase_state_engine import PhaseStateEngine
        from mcp_server.managers.project_manager import ProjectManager

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        assert state["current_tdd_cycle"] == 4

    @pytest.mark.asyncio()
    async def test_force_blocks_without_skip_reason(
        self, tool: ForceCycleTransitionTool, setup_forced_project: tuple[Path, int]
    ) -> None:
        """Test that forced transition blocks when skip_reason is empty."""
        workspace_root, issue_number = setup_forced_project

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git

            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(
                ForceCycleTransitionInput(
                    to_cycle=1,
                    skip_reason="",  # Empty reason
                    human_approval="John approved on 2026-02-17",
                )
            )

        # Assert blocked
        assert result.is_error, "Expected error when skip_reason is empty"
        text = result.content[0]["text"]
        assert "skip_reason" in text.lower() or "reason" in text.lower()

    @pytest.mark.asyncio()
    async def test_force_blocks_without_human_approval(
        self, tool: ForceCycleTransitionTool, setup_forced_project: tuple[Path, int]
    ) -> None:
        """Test that forced transition blocks when human_approval is empty."""
        workspace_root, issue_number = setup_forced_project

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git

            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(
                ForceCycleTransitionInput(
                    to_cycle=1,
                    skip_reason="Re-testing schema changes",
                    human_approval="",  # Empty approval
                )
            )

        # Assert blocked
        assert result.is_error, "Expected error when human_approval is empty"
        text = result.content[0]["text"]
        assert "approval" in text.lower() or "human" in text.lower()

