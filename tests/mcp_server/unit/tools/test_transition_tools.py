"""Tests for Transition Tools (transition_cycle, force_cycle_transition).

Issue #146 Cycle 4: TDD Cycle transition management.
Issue #146 Cycle 6: Spec alignment - audit schema, history entries, exit criteria.
Issue #229 Cycle 10: GAP-17 — blocking deliverables must appear BEFORE ✅ in response.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
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
        workspace_root, _ = setup_project

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
        workspace_root, _ = setup_project

        # Set current cycle to 2
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
        workspace_root, _ = setup_project

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
        workspace_root, _ = setup_project

        # Change phase to design
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
        workspace_root, _ = setup_forced_project

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
        assert last_entry.get("cycle_number") == 1
        assert last_entry.get("forced") is True
        assert "Re-testing schema changes" in last_entry.get("skip_reason", "")
        assert "John approved" in last_entry.get("human_approval", "")

    @pytest.mark.asyncio()
    async def test_force_skip_transition_succeeds(
        self, tool: ForceCycleTransitionTool, setup_forced_project: tuple[Path, int]
    ) -> None:
        """Test that forced skip transition (2→4) works with approval."""
        workspace_root, _ = setup_forced_project

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
        workspace_root, _ = setup_forced_project

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
        workspace_root, _ = setup_forced_project

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


class TestForceCycleTransitionSkippedDeliverables:
    """Tests for force_cycle_transition ⚠️ warning on unvalidated skipped cycle deliverables.

    Issue #229 Cycle 3 D3.2 (GAP-08): When force_cycle_transition skips cycles whose
    deliverables fail DeliverableChecker, the tool response must include a ⚠️ warning
    listing the unvalidated items. The transition itself still succeeds.
    """

    @pytest.fixture()
    def tool(self) -> ForceCycleTransitionTool:
        """Fixture to instantiate ForceCycleTransitionTool."""
        return ForceCycleTransitionTool()

    def _setup_project_with_validates_deliverables(
        self, tmp_path: Path, cycle3_file_contains: str | None
    ) -> tuple[Path, int]:
        """Set up a project in TDD phase C2 where cycle 3 has a contains_text deliverable.

        Args:
            tmp_path: Workspace root.
            cycle3_file_contains: Text to write in the validated file, or None to omit file.
        """
        workspace_root = tmp_path
        issue_number = 229
        branch = "feature/229-phase-deliverables-enforcement"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        project_manager.initialize_project(
            issue_number=issue_number,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )

        # Create the target file for the check (or not, to simulate failure)
        target_file = workspace_root / "mcp_server" / "tools" / "transition_tools.py"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        if cycle3_file_contains is not None:
            target_file.write_text(cycle3_file_contains)
        # If None: leave file absent → contains_text check fails

        # Save planning deliverables: 4 cycles, cycle 3 has a validates spec
        planning_deliverables = {
            "tdd_cycles": {
                "total": 4,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "deliverables": [{"id": "D1.1", "description": "placeholder"}],
                        "exit_criteria": "C1 done",
                    },
                    {
                        "cycle_number": 2,
                        "deliverables": [{"id": "D2.1", "description": "placeholder"}],
                        "exit_criteria": "C2 done",
                    },
                    {
                        "cycle_number": 3,
                        "deliverables": [
                            {
                                "id": "D3.2",
                                "description": "transition_tools.py contains warning text",
                                "validates": {
                                    "type": "contains_text",
                                    "file": "mcp_server/tools/transition_tools.py",
                                    "text": "Unvalidated cycle deliverables",
                                },
                            }
                        ],
                        "exit_criteria": "D3.2 passes",
                    },
                    {
                        "cycle_number": 4,
                        "deliverables": [{"id": "D4.1", "description": "placeholder"}],
                        "exit_criteria": "C4 done",
                    },
                ],
            }
        }
        project_manager.save_planning_deliverables(
            issue_number=issue_number, planning_deliverables=planning_deliverables
        )

        # Set state: TDD phase, cycle 2
        state = state_engine.get_state(branch)
        state["current_phase"] = "tdd"
        state["current_tdd_cycle"] = 2
        state["last_tdd_cycle"] = 1
        state["tdd_cycle_history"] = []
        state_engine._save_state(branch, state)

        return workspace_root, issue_number

    @pytest.mark.asyncio()
    async def test_force_cycle_transition_warns_unvalidated_skipped_cycle_deliverables(
        self, tool: ForceCycleTransitionTool, tmp_path: Path
    ) -> None:
        """When skipping C2→C4, cycle 3 D3.2 fails check → ⚠️ in tool response.

        The transition still succeeds (forced = unconditional). Only the warning is added.
        Issue #229 D3.2 (GAP-08).
        """
        workspace_root, _ = self._setup_project_with_validates_deliverables(
            tmp_path,
            cycle3_file_contains=None,  # File absent → check fails
        )

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/229-phase-deliverables-enforcement"
            mock_git_class.return_value = mock_git
            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(
                ForceCycleTransitionInput(
                    to_cycle=4,
                    skip_reason="Cycle 3 handled elsewhere",
                    human_approval="Michel approved on 2026-02-19",
                    issue_number=229,
                )
            )

        assert not result.is_error, f"Expected success, got error: {result.content}"
        text = result.content[0]["text"]
        assert "⚠️" in text, f"Expected warning in response, got: {text}"
        assert "cycle:3:D3.2" in text, f"Expected cycle:3:D3.2 in warning, got: {text}"
        assert "Unvalidated cycle deliverables" in text

    @pytest.mark.asyncio()
    async def test_force_cycle_transition_no_warning_when_skipped_cycles_pass_checks(
        self, tool: ForceCycleTransitionTool, tmp_path: Path
    ) -> None:
        """When skipping C2→C4 and cycle 3 D3.2 passes check → no ⚠️ in response.

        Issue #229 D3.2 (GAP-08).
        """
        workspace_root, _ = self._setup_project_with_validates_deliverables(
            tmp_path,
            cycle3_file_contains="def warn():\n    msg = 'Unvalidated cycle deliverables'\n",
        )

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/229-phase-deliverables-enforcement"
            mock_git_class.return_value = mock_git
            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(
                ForceCycleTransitionInput(
                    to_cycle=4,
                    skip_reason="Cycle 3 fully validated",
                    human_approval="Michel approved on 2026-02-19",
                    issue_number=229,
                )
            )

        assert not result.is_error, f"Expected success, got error: {result.content}"
        text = result.content[0]["text"]
        assert "Unvalidated cycle deliverables" not in text, (
            f"Expected no warning when checks pass, got: {text}"
        )


class TestForceCycleAuditSchema:
    """Tests for force_cycle_transition audit schema alignment.

    Issue #146 Cycle 6 D1: force_cycle_transition should produce
    {cycle_number, forced: True, skipped_cycles: [...]} not {from_cycle, to_cycle}.
    Design.md:340-354.
    """

    @pytest.fixture()
    def tool(self) -> ForceCycleTransitionTool:
        """Fixture to instantiate ForceCycleTransitionTool."""
        return ForceCycleTransitionTool()

    @pytest.fixture()
    def setup_project(self, tmp_path: Path) -> tuple[Path, int]:
        """Create project in TDD phase at cycle 2."""
        workspace_root = tmp_path
        issue_number = 146

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        project_manager.initialize_project(
            issue_number=issue_number,
            issue_title="TDD Cycle Tracking",
            workflow_name="feature",
        )

        planning_deliverables = {
            "tdd_cycles": {
                "total": 4,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": "Schema",
                        "deliverables": ["Schema"],
                        "exit_criteria": "Tests pass",
                    },
                    {
                        "cycle_number": 2,
                        "name": "Validation",
                        "deliverables": ["Validators"],
                        "exit_criteria": "All scenarios covered",
                    },
                    {
                        "cycle_number": 3,
                        "name": "Discovery",
                        "deliverables": ["get_work_context"],
                        "exit_criteria": "Tools work",
                    },
                    {
                        "cycle_number": 4,
                        "name": "Transition",
                        "deliverables": ["transition_cycle"],
                        "exit_criteria": "Transitions work",
                    },
                ],
            }
        }
        project_manager.save_planning_deliverables(issue_number, planning_deliverables)

        branch = "feature/146-tdd-cycle-tracking"
        state_engine.initialize_branch(
            branch=branch,
            issue_number=issue_number,
            initial_phase="tdd",
        )
        state = state_engine.get_state(branch)
        state["current_phase"] = "tdd"
        state["current_tdd_cycle"] = 2
        state["last_tdd_cycle"] = 1
        state["tdd_cycle_history"] = []
        state_engine._save_state(branch, state)

        return workspace_root, issue_number

    @pytest.mark.asyncio()
    async def test_force_audit_entry_has_cycle_number_not_from_to(
        self, tool: ForceCycleTransitionTool, setup_project: tuple[Path, int]
    ) -> None:
        """Audit entry must use cycle_number (not from_cycle/to_cycle).

        Issue #146 Cycle 6 D1: Design.md:344 requires cycle_number field.
        """
        workspace_root, _ = setup_project

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
                    skip_reason="Cycles 3 covered by parent",
                    human_approval="John approved on 2026-02-17",
                )
            )

        assert not result.is_error, f"Expected success: {result.content}"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        history = state.get("tdd_cycle_history", [])

        assert len(history) > 0, "Expected audit entry in tdd_cycle_history"
        entry = history[-1]

        assert "cycle_number" in entry, "Audit entry must have cycle_number field"
        assert entry["cycle_number"] == 4, "cycle_number must be the target cycle"
        assert "from_cycle" not in entry, "Audit entry must not use from_cycle (old schema)"
        assert "to_cycle" not in entry, "Audit entry must not use to_cycle (old schema)"

    @pytest.mark.asyncio()
    async def test_force_audit_entry_has_forced_true(
        self, tool: ForceCycleTransitionTool, setup_project: tuple[Path, int]
    ) -> None:
        """Audit entry must explicitly set forced=True.

        Issue #146 Cycle 6 D1: Design.md:344 requires forced: true.
        """
        workspace_root, _ = setup_project

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git
            mock_settings.server.workspace_root = workspace_root

            await tool.execute(
                ForceCycleTransitionInput(
                    to_cycle=1,
                    skip_reason="Re-testing",
                    human_approval="John approved",
                )
            )

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        history = state.get("tdd_cycle_history", [])

        assert len(history) > 0
        entry = history[-1]
        assert "forced" in entry, "Audit entry must have forced field"
        assert entry["forced"] is True, "forced must be True for force_cycle_transition"
        assert "transition_type" not in entry, "Must not use transition_type (old schema)"

    @pytest.mark.asyncio()
    async def test_force_audit_entry_has_skipped_cycles(
        self, tool: ForceCycleTransitionTool, setup_project: tuple[Path, int]
    ) -> None:
        """Audit entry must include list of skipped_cycles.

        Issue #146 Cycle 6 D1: Design.md:346 requires skipped_cycles field.
        Skipping from cycle 2 -> cycle 4 means cycles [3] are skipped.
        """
        workspace_root, _ = setup_project

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
                    skip_reason="Cycles 3 covered by parent tests",
                    human_approval="Jane approved on 2026-02-17",
                )
            )

        assert not result.is_error

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        history = state.get("tdd_cycle_history", [])

        assert len(history) > 0
        entry = history[-1]
        assert "skipped_cycles" in entry, "Audit entry must have skipped_cycles field"
        assert entry["skipped_cycles"] == [3], f"Expected [3], got {entry['skipped_cycles']}"


class TestTransitionCycleHistory:
    """Tests for transition_cycle history entry (forced=False).

    Issue #146 Cycle 6 D2: Normal transition_cycle should write
    {cycle_number, forced: False} to tdd_cycle_history. Design.md:291-297.
    """

    @pytest.fixture()
    def tool(self) -> TransitionCycleTool:
        """Fixture to instantiate TransitionCycleTool."""
        return TransitionCycleTool()

    @pytest.fixture()
    def setup_project(self, tmp_path: Path) -> tuple[Path, int]:
        """Create project in TDD phase at cycle 1."""
        workspace_root = tmp_path
        issue_number = 146

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        project_manager.initialize_project(
            issue_number=issue_number,
            issue_title="TDD Cycle Tracking",
            workflow_name="feature",
        )

        planning_deliverables = {
            "tdd_cycles": {
                "total": 3,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": "Cycle One",
                        "deliverables": ["D1"],
                        "exit_criteria": "EC1",
                    },
                    {
                        "cycle_number": 2,
                        "name": "Cycle Two",
                        "deliverables": ["D2"],
                        "exit_criteria": "EC2",
                    },
                    {
                        "cycle_number": 3,
                        "name": "Cycle Three",
                        "deliverables": ["D3"],
                        "exit_criteria": "EC3",
                    },
                ],
            }
        }
        project_manager.save_planning_deliverables(issue_number, planning_deliverables)

        branch = "feature/146-tdd-cycle-tracking"
        state_engine.initialize_branch(
            branch=branch,
            issue_number=issue_number,
            initial_phase="tdd",
        )
        state = state_engine.get_state(branch)
        state["current_phase"] = "tdd"
        state["current_tdd_cycle"] = 1
        state["last_tdd_cycle"] = None
        state["tdd_cycle_history"] = []
        state_engine._save_state(branch, state)

        return workspace_root, issue_number

    @pytest.mark.asyncio()
    async def test_normal_transition_writes_history_entry(
        self, tool: TransitionCycleTool, setup_project: tuple[Path, int]
    ) -> None:
        """Normal transition_cycle must write a history entry with forced=False.

        Issue #146 Cycle 6 D2: Design.md:291-297.
        """
        workspace_root, _ = setup_project

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git
            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(TransitionCycleInput(to_cycle=2))

        assert not result.is_error, f"Expected success: {result.content}"

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        history = state.get("tdd_cycle_history", [])

        assert len(history) == 1, f"Expected 1 history entry, got {len(history)}"
        entry = history[0]
        assert "cycle_number" in entry, "History entry must have cycle_number"
        assert entry["cycle_number"] == 2, "cycle_number must be the target cycle"
        assert "forced" in entry, "History entry must have forced field"
        assert entry["forced"] is False, "forced must be False for normal transition"

    @pytest.mark.asyncio()
    async def test_multiple_transitions_accumulate_history(
        self, tool: TransitionCycleTool, setup_project: tuple[Path, int]
    ) -> None:
        """Multiple normal transitions accumulate in tdd_cycle_history.

        Issue #146 Cycle 6 D2: History is cumulative.
        """
        workspace_root, _ = setup_project

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git
            mock_settings.server.workspace_root = workspace_root

            result1 = await tool.execute(TransitionCycleInput(to_cycle=2))
            assert not result1.is_error

            result2 = await tool.execute(TransitionCycleInput(to_cycle=3))
            assert not result2.is_error

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        history = state.get("tdd_cycle_history", [])

        assert len(history) == 2, f"Expected 2 history entries, got {len(history)}"
        assert history[0]["cycle_number"] == 2
        assert history[1]["cycle_number"] == 3
        assert history[0]["forced"] is False
        assert history[1]["forced"] is False


class TestTransitionCycleExitCriteria:
    """Tests for transition_cycle exit criteria validation.

    Issue #146 Cycle 6 D3: transition_cycle must validate that the current cycle
    has a non-empty exit_criteria before allowing transition to next cycle.
    Design.md:287 (validate_exit_criteria(current_tdd_cycle)).
    """

    @pytest.fixture()
    def tool(self) -> TransitionCycleTool:
        """Fixture to instantiate TransitionCycleTool."""
        return TransitionCycleTool()

    def _make_project(
        self,
        tmp_path: Path,
        cycles: list[dict],
        current_cycle: int = 1,
        *,
        bypass_validation: bool = False,
    ) -> Path:
        """Helper to create a project with given cycle definitions.

        Args:
            bypass_validation: If True, writes cycle data directly to state file,
                bypassing save_planning_deliverables validation. Used to test edge cases
                where external/corrupt state has invalid exit_criteria.
        """
        workspace_root = tmp_path
        issue_number = 146

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        project_manager.initialize_project(
            issue_number=issue_number,
            issue_title="TDD Cycle Tracking",
            workflow_name="feature",
        )

        if bypass_validation:
            # Write planning deliverables directly to bypass schema validation
            # Used to simulate corrupt/external state for testing robustness
            projects_file = workspace_root / ".st3" / "projects.json"
            with projects_file.open() as f:
                projects = json.load(f)

            projects[str(issue_number)]["planning_deliverables"] = {
                "tdd_cycles": {"total": len(cycles), "cycles": cycles}
            }
            with projects_file.open("w") as f:
                json.dump(projects, f, indent=2)
        else:
            planning_deliverables = {
                "tdd_cycles": {
                    "total": len(cycles),
                    "cycles": cycles,
                }
            }
            project_manager.save_planning_deliverables(issue_number, planning_deliverables)

        branch = "feature/146-tdd-cycle-tracking"
        state_engine.initialize_branch(
            branch=branch,
            issue_number=issue_number,
            initial_phase="tdd",
        )
        state = state_engine.get_state(branch)
        state["current_phase"] = "tdd"
        state["current_tdd_cycle"] = current_cycle
        state["last_tdd_cycle"] = None
        state["tdd_cycle_history"] = []
        state_engine._save_state(branch, state)

        return workspace_root

    @pytest.mark.asyncio()
    async def test_transition_blocked_when_current_cycle_has_empty_exit_criteria(
        self, tool: TransitionCycleTool, tmp_path: Path
    ) -> None:
        """transition_cycle must block when current cycle has empty exit_criteria.

        Issue #146 Cycle 6 D3: Design.md:287 - validate_exit_criteria before transition.
        """
        workspace_root = self._make_project(
            tmp_path,
            bypass_validation=True,
            cycles=[
                {
                    "cycle_number": 1,
                    "name": "Schema",
                    "deliverables": ["Schema"],
                    "exit_criteria": "",  # Empty - bypasses save_planning_deliverables validation
                },
                {
                    "cycle_number": 2,
                    "name": "Validation",
                    "deliverables": ["Validators"],
                    "exit_criteria": "All validators pass",
                },
            ],
        )

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git
            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(TransitionCycleInput(to_cycle=2))

        assert result.is_error, "Must block when exit_criteria is empty"
        text = result.content[0]["text"]
        assert "exit" in text.lower() or "criteria" in text.lower()

    @pytest.mark.asyncio()
    async def test_transition_blocked_when_current_cycle_missing_exit_criteria(
        self, tool: TransitionCycleTool, tmp_path: Path
    ) -> None:
        """transition_cycle must block when current cycle is missing exit_criteria key.

        Issue #146 Cycle 6 D3: exit_criteria key is mandatory.
        """
        workspace_root = self._make_project(
            tmp_path,
            bypass_validation=True,
            cycles=[
                {
                    "cycle_number": 1,
                    "name": "Schema",
                    "deliverables": ["Schema"],
                    # No exit_criteria key at all
                },
                {
                    "cycle_number": 2,
                    "name": "Validation",
                    "deliverables": ["Validators"],
                    "exit_criteria": "All validators pass",
                },
            ],
        )

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git
            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(TransitionCycleInput(to_cycle=2))

        assert result.is_error, "Must block when exit_criteria key is missing"
        text = result.content[0]["text"]
        assert "exit" in text.lower() or "criteria" in text.lower()

    @pytest.mark.asyncio()
    async def test_transition_succeeds_when_exit_criteria_present(
        self, tool: TransitionCycleTool, tmp_path: Path
    ) -> None:
        """transition_cycle must succeed when current cycle has non-empty exit_criteria.

        Issue #146 Cycle 6 D3: Normal path - exit criteria defined means transition allowed.
        """
        workspace_root = self._make_project(
            tmp_path,
            cycles=[
                {
                    "cycle_number": 1,
                    "name": "Schema",
                    "deliverables": ["Schema"],
                    "exit_criteria": "All schema tests pass",
                },
                {
                    "cycle_number": 2,
                    "name": "Validation",
                    "deliverables": ["Validators"],
                    "exit_criteria": "All validators pass",
                },
            ],
        )

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git_class.return_value = mock_git
            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(TransitionCycleInput(to_cycle=2))

        assert not result.is_error, f"Must succeed when exit_criteria present: {result.content}"


# ---------------------------------------------------------------------------
# C10: GAP-17 — force_cycle_transition: blocking deliverables BEFORE ✅ (Issue #229)
# ---------------------------------------------------------------------------


class TestForceCycleTransitionResponseFormat:
    """Blocking deliverables appear BEFORE ✅; passing deliverables appear AFTER ✅.

    Issue #229 Cycle 10 (GAP-17):
    D10.4: Unvalidated (blocking) deliverables emitted before ✅ in force_cycle_transition.
    D10.5: Validated (passing) deliverables listed informatively after ✅.
    """

    @pytest.fixture()
    def tool(self) -> ForceCycleTransitionTool:
        """Fixture to instantiate ForceCycleTransitionTool."""
        return ForceCycleTransitionTool()

    def _setup_for_cycle_transition(
        self, tmp_path: Path, *, cycle3_file_present: bool
    ) -> tuple[Path, int, str]:
        """Build project in TDD phase C2; cycle 3 has a file_glob deliverable."""
        workspace_root = tmp_path
        issue_number = 229
        branch = "feature/229-phase-deliverables-enforcement"

        pm = ProjectManager(workspace_root=workspace_root)
        se = PhaseStateEngine(workspace_root=workspace_root, project_manager=pm)

        pm.initialize_project(
            issue_number=issue_number,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )

        if cycle3_file_present:
            target_dir = workspace_root / "mcp_server" / "tools"
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "transition_tools.py").write_text("# validated content")

        planning_deliverables: dict = {
            "tdd_cycles": {
                "total": 4,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "deliverables": [{"id": "D1.1", "description": "p"}],
                        "exit_criteria": "C1",
                    },
                    {
                        "cycle_number": 2,
                        "deliverables": [{"id": "D2.1", "description": "p"}],
                        "exit_criteria": "C2",
                    },
                    {
                        "cycle_number": 3,
                        "deliverables": [
                            {
                                "id": "D3.2",
                                "description": "transition_tools.py exists",
                                "validates": {
                                    "type": "file_glob",
                                    "dir": "mcp_server/tools",
                                    "pattern": "transition_tools.py",
                                },
                            }
                        ],
                        "exit_criteria": "D3.2 passes",
                    },
                    {
                        "cycle_number": 4,
                        "deliverables": [{"id": "D4.1", "description": "p"}],
                        "exit_criteria": "C4",
                    },
                ],
            }
        }
        pm.save_planning_deliverables(
            issue_number=issue_number, planning_deliverables=planning_deliverables
        )

        state = se.get_state(branch)
        state["current_phase"] = "tdd"
        state["current_tdd_cycle"] = 2
        state["last_tdd_cycle"] = 1
        state["tdd_cycle_history"] = []
        se._save_state(branch, state)

        return workspace_root, issue_number, branch

    @pytest.mark.asyncio()
    async def test_force_cycle_transition_response_blocking_deliverable_appears_before_success(
        self, tool: ForceCycleTransitionTool, tmp_path: Path
    ) -> None:
        """Unvalidated (blocking) deliverables appear BEFORE ✅ in response (GAP-17/D10.4)."""
        workspace_root, issue_number, _branch = self._setup_for_cycle_transition(
            tmp_path,
            cycle3_file_present=False,  # file absent → deliverable FAILS → blocks
        )

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/229-phase-deliverables-enforcement"
            mock_git_class.return_value = mock_git
            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(
                ForceCycleTransitionInput(
                    to_cycle=4,
                    skip_reason="Force skip C3",
                    human_approval="Approved",
                    issue_number=issue_number,
                )
            )

        assert not result.is_error, f"Forced transition must succeed: {result.content}"
        text = result.content[0]["text"]

        assert "Unvalidated" in text, f"Expected 'Unvalidated' in response: {text}"
        assert "✅" in text
        # Blocking warning MUST appear BEFORE ✅
        assert text.index("Unvalidated") < text.index("✅"), (
            f"Blocking warning must precede ✅, got:\n{text}"
        )

    @pytest.mark.asyncio()
    async def test_force_cycle_transition_response_passing_deliverable_appears_after_success(
        self, tool: ForceCycleTransitionTool, tmp_path: Path
    ) -> None:
        """Validated (passing) deliverables listed informatively AFTER ✅ (GAP-17/D10.5)."""
        workspace_root, issue_number, _branch = self._setup_for_cycle_transition(
            tmp_path,
            cycle3_file_present=True,  # file present → deliverable PASSES
        )

        with (
            patch("mcp_server.tools.transition_tools.settings") as mock_settings,
            patch("mcp_server.tools.transition_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/229-phase-deliverables-enforcement"
            mock_git_class.return_value = mock_git
            mock_settings.server.workspace_root = workspace_root

            result = await tool.execute(
                ForceCycleTransitionInput(
                    to_cycle=4,
                    skip_reason="Force skip C3 (validated)",
                    human_approval="Approved",
                    issue_number=issue_number,
                )
            )

        assert not result.is_error, f"Forced transition must succeed: {result.content}"
        text = result.content[0]["text"]

        assert "✅" in text
        # Validated deliverable D3.2 should be reported informatively AFTER ✅
        assert "cycle:3:D3.2" in text, f"Expected cycle:3:D3.2 in informational section: {text}"
        assert text.index("✅") < text.index("cycle:3:D3.2"), (
            f"Informational deliverable info must follow ✅, got:\n{text}"
        )
