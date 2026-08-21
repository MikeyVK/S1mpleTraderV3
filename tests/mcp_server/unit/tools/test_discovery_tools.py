# tests/mcp_server/unit/tools/test_discovery_tools.py
# pyright: reportPrivateUsage=false
"""
Tests for the get_work_context discovery tool.

@layer: Tests (Unit)
@dependencies: [pytest, tempfile, unittest.mock, mcp_server.tools.discovery_tools]
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

import mcp_server.tools.discovery_tools as discovery_module
from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import GitConfig
from mcp_server.config.schemas.contracts_config import (
    ContractsConfig,
    MergePolicy,
    PhaseInstructionsSpec,
    WorkflowEntry,
    WorkflowPhaseEntry,
)
from mcp_server.config.schemas.workflows import WorkflowConfig
from mcp_server.config.schemas.workphases import WorkphasesConfig
from mcp_server.config.settings import Settings
from mcp_server.core.exceptions import StateNotFoundError
from mcp_server.core.interfaces import IContextLoadedWriter
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.state_repository import StateBranchMismatchError
from mcp_server.schemas.tool_outputs import WorkflowStateStatus
from mcp_server.state.workflow_status import WorkflowStatusDTO
from mcp_server.tools.discovery_tools import GetWorkContextInput, GetWorkContextTool
from tests.mcp_server.test_support import (
    get_default_server_root,
    make_phase_state_engine,
    make_project_manager,
)


def make_settings(workspace_root: Path | str = ".", github_token: str | None = None) -> Settings:
    """Create explicit settings for discovery tool tests."""
    return Settings(
        server={"workspace_root": str(workspace_root)},
        github={"token": github_token},
    )


def make_work_context_tool(
    workspace_root: Path | str = ".",
    github_token: str | None = None,
    contracts_config: ContractsConfig | None = None,
    context_loaded_writer: IContextLoadedWriter | None = None,
) -> GetWorkContextTool:
    settings = make_settings(workspace_root=workspace_root, github_token=github_token)
    return GetWorkContextTool(
        settings=settings,
        git_manager=MagicMock(),
        project_manager=MagicMock(),
        state_engine=MagicMock(),
        github_manager=MagicMock(),
        workphases_config=load_workphases_config(),
        workflow_status_resolver=MagicMock(),
        contracts_config=contracts_config,
        context_loaded_writer=context_loaded_writer,
    )


def load_workflow_config() -> WorkflowConfig:
    return ConfigLoader(Path(f"{get_default_server_root()}/config")).load_workflow_config()


def load_git_config() -> GitConfig:
    return ConfigLoader(Path(f"{get_default_server_root()}/config")).load_git_config()


def load_workphases_config() -> WorkphasesConfig:
    return ConfigLoader(Path(f"{get_default_server_root()}/config")).load_workphases_config()


def load_contracts_config() -> ContractsConfig:
    return ConfigLoader(Path(f"{get_default_server_root()}/config")).load_contracts_config()


class TestGetWorkContextTool:
    """Tests for GetWorkContextTool."""

    @pytest.fixture()
    def tool(self) -> GetWorkContextTool:
        """Fixture to instantiate GetWorkContextTool."""
        return make_work_context_tool()

    def test_tool_name(self, tool: GetWorkContextTool) -> None:
        """Should have correct tool name."""
        assert tool.name == "get_work_context"

    @pytest.mark.asyncio
    async def test_get_context_returns_branch_info(self, tool: GetWorkContextTool) -> None:
        """Should return branch information."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "main"
            mock_git.get_recent_commits.return_value = []
            mock_git_class.return_value = mock_git
            tool._git_manager = mock_git

            tool._settings.github.token = None
            result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.current_branch == "main"

    @pytest.mark.asyncio
    async def test_get_context_extracts_issue_number(self, tool: GetWorkContextTool) -> None:
        """Issue number comes from BranchState after C1 (issue #268)."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool._state_engine.get_state.return_value.issue_number = 42
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "feature/42-implement-dto"
        tool._git_manager = mock_git
        tool._settings.github.token = None

        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.issue_number == 42

    @pytest.mark.asyncio
    async def test_get_context_extracts_issue_number_alternate_format(
        self, tool: GetWorkContextTool
    ) -> None:
        """Issue number from BranchState for bug/ branches after C1 (issue #268)."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool._state_engine.get_state.return_value.issue_number = 99
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "bug/99-bug"
        tool._git_manager = mock_git
        tool._settings.github.token = None

        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.issue_number == 99

    @pytest.mark.asyncio
    async def test_get_context_detects_workflow_phase_from_commit_scope(
        self, tool: GetWorkContextTool
    ) -> None:
        """Phase and sub-phase come from BranchState after C1 (issue #268)."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool._state_engine.get_state.return_value.current_phase = "implementation"
        tool._state_engine.get_state.return_value.current_sub_phase = "red"
        tool._state_engine.get_state.return_value.workflow_name = "feature"
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "feature/42-dto"
        tool._git_manager = mock_git
        tool._settings.github.token = None

        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.phase == "implementation"
        assert result.sub_phase == "red"

    @pytest.mark.asyncio
    async def test_detect_workflow_phase_variations(self, tool: GetWorkContextTool) -> None:
        """All 7 workflow phases appear in output when set via BranchState after C1."""
        test_cases = [
            ("research", "🔍"),
            ("planning", "📋"),
            ("design", "🎨"),
            ("implementation", "🧪"),
            ("validation", "✅"),
            ("documentation", "📝"),
            ("coordination", "🤝"),
        ]

        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "main"
        tool._git_manager = mock_git  # pyright: ignore[reportPrivateUsage]
        tool._settings.github.token = None  # pyright: ignore[reportPrivateUsage]

        for expected_phase, _ in test_cases:
            tool._state_engine.get_state.return_value.current_phase = expected_phase  # pyright: ignore[reportPrivateUsage]
            tool._state_engine.get_state.return_value.workflow_name = "feature"  # pyright: ignore[reportPrivateUsage]
            result = await tool.execute(GetWorkContextInput(), NoteContext())
            assert isinstance(result, GetWorkContextOutput)
            assert result.success
            assert result.phase == expected_phase

    @pytest.mark.asyncio
    async def test_get_context_with_github_integration(self, tool: GetWorkContextTool) -> None:
        """Should handle GitHub integration gracefully (error case)."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "feature/42-implement-dto"
        mock_git.get_recent_commits.return_value = []
        tool._git_manager = mock_git
        mock_github_manager = tool._github_manager
        assert mock_github_manager is not None
        mock_github_manager.get_issue.side_effect = RuntimeError("GitHub unavailable")

        tool._settings.github.token = "test-token"

        # Execute - GitHub code path will fail gracefully
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        # Should not error even if GitHub fetch fails
        assert isinstance(result, GetWorkContextOutput)
        assert result.success

    @pytest.mark.asyncio
    async def test_get_context_github_success(self, tool: GetWorkContextTool) -> None:
        """GitHub block removed in C1 (issue #268); tool completes successfully."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "feature/42-test"
        tool._git_manager = mock_git  # pyright: ignore[reportPrivateUsage]
        tool._settings.github.token = "test-token"  # pyright: ignore[reportPrivateUsage]

        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success

    @pytest.mark.asyncio
    async def test_get_context_shows_error_message_when_phase_unknown(
        self, tool: GetWorkContextTool
    ) -> None:
        """When state engine fails, output shows unknown confidence (no error raised)."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool._state_engine.get_state.side_effect = OSError("state.json missing")  # pyright: ignore[reportPrivateUsage]
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "main"
        tool._git_manager = mock_git  # pyright: ignore[reportPrivateUsage]
        tool._settings.github.token = None  # pyright: ignore[reportPrivateUsage]

        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.phase_confidence == "unknown"
        assert result.workflow_state_status is WorkflowStateStatus.UNREADABLE


class TestGetWorkContextTddCycleInfo:
    """Tests for TDD cycle info in get_work_context.

    Issue #146 Cycle 3: Conditional visibility of tdd_cycle_info.
    """

    @pytest.fixture()
    def tool(self) -> GetWorkContextTool:
        """Fixture to instantiate GetWorkContextTool."""
        return make_work_context_tool()

    @pytest.mark.asyncio
    async def test_tdd_cycle_info_shown_during_tdd_phase(
        self, tool: GetWorkContextTool, tmp_path: Path
    ) -> None:
        """Test that tdd_cycle_info appears when in TDD phase.

        Issue #146 Cycle 3: Conditional visibility based on workflow_phase.
        """
        workspace_root = tmp_path

        # Create minimal project structure
        project_manager = make_project_manager(workspace_root)
        state_engine = make_phase_state_engine(workspace_root, project_manager=project_manager)

        # Initialize project
        project_manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Save planning deliverables with total=2 (matching 2 cycles)
        planning_deliverables = {
            "cycles": {
                "total": 2,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": " & Storage",
                        "deliverables": [{"id": "D1.1", "description": "ProjectManager schema"}],
                        "exit_criteria": "Schema validated",
                    },
                    {
                        "cycle_number": 2,
                        "name": "Validation Logic",
                        "deliverables": [{"id": "D2.1", "description": "Cycle validation"}],
                        "exit_criteria": "All validation covered",
                    },
                ],
            }
        }
        project_manager.save_planning_deliverables(146, planning_deliverables)

        # Set implementation phase with current cycle = 2
        state_engine.initialize_branch(
            branch="feature/146-tdd-cycle-tracking",
            issue_number=146,
            initial_phase="implementation",
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        state = state.with_updates(current_cycle=2)
        state_engine._state_repository.save(state)  # pyright: ignore[reportPrivateUsage]  # State fixture injection.

        # Mock Git and settings
        with (
            patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            # Provide implementation-scoped commit so ScopeDecoder has context
            mock_git.get_recent_commits.return_value = [
                "test(P_IMPLEMENTATION_SP_C2_GREEN): add cycle info display"
            ]
            mock_git_class.return_value = mock_git
            tool._git_manager = mock_git

            tool._settings.github.token = None
            tool._project_manager = project_manager
            tool._state_engine = state_engine
            tool._settings.server.workspace_root = str(workspace_root)

            # Configure resolver to match expected phase/cycle for TDD info visibility
            tool._workflow_status_resolver.resolve_current.return_value = WorkflowStatusDTO(  # pyright: ignore[reportPrivateUsage]
                current_phase="implementation",
                sub_phase="green",
                current_cycle=2,
                phase_source="state.json",
                phase_confidence="high",
                phase_detection_error=None,
            )

            result = await tool.execute(GetWorkContextInput(), NoteContext())

        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.current_cycle is None

    @pytest.mark.asyncio
    async def test_tdd_cycle_info_hidden_outside_tdd_phase(
        self, tool: GetWorkContextTool, tmp_path: Path
    ) -> None:
        """Test that tdd_cycle_info is hidden when NOT in TDD phase.

        Issue #146 Cycle 3: Conditional visibility - no noise outside TDD.
        """
        workspace_root = tmp_path

        # Create minimal project structure
        project_manager = make_project_manager(workspace_root)
        state_engine = make_phase_state_engine(workspace_root, project_manager=project_manager)

        # Initialize project
        project_manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Save planning deliverables
        planning_deliverables = {
            "cycles": {
                "total": 1,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": "Schema & Storage",
                        "deliverables": [{"id": "D1.1", "description": "ProjectManager schema"}],
                        "exit_criteria": "Tests pass",
                    }
                ],
            }
        }
        project_manager.save_planning_deliverables(146, planning_deliverables)

        # Set DESIGN phase (not TDD)
        state_engine.initialize_branch(
            branch="feature/146-tdd-cycle-tracking", issue_number=146, initial_phase="design"
        )

        # Mock Git
        with (
            patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git.get_recent_commits.return_value = [
                "test(P_IMPLEMENTATION_SP_C1_RED): graceful degradation path"
            ]
            mock_git_class.return_value = mock_git
            tool._git_manager = mock_git

            tool._settings.github.token = None
            tool._project_manager = project_manager
            tool._state_engine = state_engine
            tool._settings.server.workspace_root = str(workspace_root)

            tool._workflow_status_resolver.resolve_current.return_value = WorkflowStatusDTO(
                current_phase="design",
                sub_phase=None,
                current_cycle=None,
                phase_source="state.json",
                phase_confidence="high",
                phase_detection_error=None,
            )
            result = await tool.execute(GetWorkContextInput(), NoteContext())

        # Assert - NO tdd_cycle_info in design phase
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.phase == "design"

    @pytest.mark.asyncio
    async def test_tdd_cycle_info_graceful_degradation(
        self, tool: GetWorkContextTool, tmp_path: Path
    ) -> None:
        """Test graceful degradation when planning deliverables missing.

        Issue #146 Cycle 3: Avoid crashes if planning_deliverables not saved.
        """
        workspace_root = tmp_path

        # Create minimal project structure WITHOUT planning deliverables
        project_manager = make_project_manager(workspace_root)
        state_engine = make_phase_state_engine(workspace_root, project_manager=project_manager)

        # Initialize project WITHOUT planning deliverables
        project_manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )
        # NOTE: Deliberately NOT calling save_planning_deliverables

        # Set implementation phase
        state_engine.initialize_branch(
            branch="feature/146-tdd-cycle-tracking",
            issue_number=146,
            initial_phase="implementation",
        )

        # Mock Git
        with (
            patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git.get_recent_commits.return_value = [
                "test(P_IMPLEMENTATION_SP_C1_RED): graceful degradation path"
            ]
            mock_git_class.return_value = mock_git
            tool._git_manager = mock_git

            tool._settings.github.token = None
            tool._project_manager = project_manager
            tool._state_engine = state_engine
            tool._settings.server.workspace_root = str(workspace_root)

            tool._workflow_status_resolver.resolve_current.return_value = WorkflowStatusDTO(
                current_phase="implementation",
                sub_phase="red",
                current_cycle=1,
                phase_source="state.json",
                phase_confidence="high",
                phase_detection_error=None,
            )
            result = await tool.execute(GetWorkContextInput(), NoteContext())

        # Assert - tool should NOT crash
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.phase == "implementation"


class TestTddCycleInfoStatusField:
    """Tests for the status field in tdd_cycle_info (Issue #146 Cycle 7 D2).

    design.md:365-376 specifies tdd_cycle_info must include status='in_progress'.
    discovery_tools.py:168-175 did not include this field.
    """

    @pytest.fixture()
    def tool(self) -> GetWorkContextTool:
        """Fixture to instantiate GetWorkContextTool."""
        return make_work_context_tool()

    @pytest.mark.asyncio
    async def test_tdd_cycle_info_includes_status_field(
        self, tool: GetWorkContextTool, tmp_path: Path
    ) -> None:
        """tdd_cycle_info must include status='in_progress' per design.md:375.

        Issue #146 Cycle 7 D2: Align implementation with design spec.
        The status field is always 'in_progress' when the cycle is active.
        """
        workspace_root = tmp_path
        project_manager = make_project_manager(workspace_root)
        state_engine = make_phase_state_engine(workspace_root, project_manager=project_manager)

        project_manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        planning_deliverables = {
            "cycles": {
                "total": 1,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": "Status Field Test",
                        "deliverables": [{"id": "D1.1", "description": "Add status field"}],
                        "exit_criteria": "Status field present in output",
                    }
                ],
            }
        }
        project_manager.save_planning_deliverables(146, planning_deliverables)

        state_engine.initialize_branch(
            branch="feature/146-tdd-cycle-tracking",
            issue_number=146,
            initial_phase="implementation",
        )
        # Set current cycle so tdd_cycle_info is populated
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        state = state.with_updates(current_cycle=1)
        state_engine._state_repository.save(state)  # pyright: ignore[reportPrivateUsage]  # State fixture injection.

        with (
            patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            # Provide a non-empty commits list so ScopeDecoder is invoked (not short-circuited)
            mock_git.get_recent_commits.return_value = [
                "test(P_IMPLEMENTATION_SP_C1_RED): add status field test"
            ]
            mock_git_class.return_value = mock_git
            tool._git_manager = mock_git

            tool._settings.github.token = None
            tool._project_manager = project_manager
            tool._state_engine = state_engine
            tool._settings.server.workspace_root = str(workspace_root)

            # Configure resolver to provide implementation phase with cycle 1
            tool._workflow_status_resolver.resolve_current.return_value = WorkflowStatusDTO(
                current_phase="implementation",
                sub_phase="red",
                current_cycle=1,
                phase_source="state.json",
                phase_confidence="high",
                phase_detection_error=None,
            )

            result = await tool.execute(GetWorkContextInput(), NoteContext())

        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.current_cycle is None


class TestGetWorkContextResolverAdoption:
    """C4: WorkflowStatusResolver adoption in GetWorkContextTool.execute().

    Issue #231: These tests FAIL (RED) until WorkflowStatusResolver is added as
    a constructor parameter and used in execute() instead of local phase detection.
    """

    @pytest.mark.asyncio
    async def test_execute_calls_resolver_when_injected(self) -> None:
        """GetWorkContextTool calls resolver.resolve_current() when resolver is injected."""
        resolver = MagicMock()
        resolver.resolve_current.return_value = WorkflowStatusDTO(
            current_phase="design",
            sub_phase=None,
            current_cycle=None,
            phase_source="state.json",
            phase_confidence="high",
            phase_detection_error=None,
        )
        settings = make_settings()
        settings.github.token = None
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "feature/99-test"

        tool = GetWorkContextTool(
            settings=settings,
            git_manager=mock_git,
            project_manager=MagicMock(),
            state_engine=MagicMock(),
            workflow_status_resolver=resolver,
        )
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.current_branch == "feature/99-test"

    @pytest.mark.asyncio
    async def test_execute_gates_cycle_enrichment_on_current_cycle_not_none(self) -> None:
        """Cycle enrichment gated on current_cycle is not None, not phase string equality."""
        resolver = MagicMock()
        resolver.resolve_current.return_value = WorkflowStatusDTO(
            current_phase="implementation",
            sub_phase="red",
            current_cycle=None,  # Gate: no cycle → no enrichment
            phase_source="state.json",
            phase_confidence="high",
            phase_detection_error=None,
        )
        settings = make_settings()
        settings.github.token = None
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "feature/99-test"

        tool = GetWorkContextTool(
            settings=settings,
            git_manager=mock_git,
            project_manager=MagicMock(),
            state_engine=MagicMock(),
            workflow_status_resolver=resolver,
        )
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.current_cycle is None

    @pytest.mark.asyncio
    async def test_execute_hides_cycle_for_non_cycle_phase_even_when_preserved(self) -> None:
        planning_tool = make_work_context_tool(contracts_config=load_contracts_config())
        planning_tool._git_manager.get_current_branch.return_value = "bug/230-test"  # pyright: ignore[reportPrivateUsage]
        planning_tool._state_engine.get_state.return_value.workflow_name = "bug"  # pyright: ignore[reportPrivateUsage]
        planning_tool._state_engine.get_state.return_value.current_phase = "planning"  # pyright: ignore[reportPrivateUsage]
        planning_tool._state_engine.get_state.return_value.issue_number = 230  # pyright: ignore[reportPrivateUsage]
        planning_tool._state_engine.get_state.return_value.parent_branch = None  # pyright: ignore[reportPrivateUsage]
        planning_tool._state_engine.get_state.return_value.current_cycle = 3  # pyright: ignore[reportPrivateUsage]
        planning_tool._state_engine.get_state.return_value.current_sub_phase = None  # pyright: ignore[reportPrivateUsage]

        planning_result = await planning_tool.execute(GetWorkContextInput(), NoteContext())

        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        assert isinstance(planning_result, GetWorkContextOutput)
        assert planning_result.success
        assert planning_result.phase == "planning"
        assert planning_result.current_cycle is None

        implementation_tool = make_work_context_tool(contracts_config=load_contracts_config())
        implementation_tool._git_manager.get_current_branch.return_value = "bug/230-test"  # pyright: ignore[reportPrivateUsage]
        implementation_tool._state_engine.get_state.return_value.workflow_name = "bug"  # pyright: ignore[reportPrivateUsage]
        implementation_tool._state_engine.get_state.return_value.current_phase = "implementation"  # pyright: ignore[reportPrivateUsage]
        implementation_tool._state_engine.get_state.return_value.issue_number = 230  # pyright: ignore[reportPrivateUsage]
        implementation_tool._state_engine.get_state.return_value.parent_branch = None  # pyright: ignore[reportPrivateUsage]
        implementation_tool._state_engine.get_state.return_value.current_cycle = 3  # pyright: ignore[reportPrivateUsage]
        implementation_tool._state_engine.get_state.return_value.current_sub_phase = None  # pyright: ignore[reportPrivateUsage]

        implementation_result = await implementation_tool.execute(
            GetWorkContextInput(), NoteContext()
        )

        assert isinstance(implementation_result, GetWorkContextOutput)
        assert implementation_result.success
        assert implementation_result.phase == "implementation"
        assert implementation_result.current_cycle == 3

    @pytest.mark.asyncio
    async def test_execute_shows_phase_from_resolver(self) -> None:
        """GetWorkContextTool output reflects phase from BranchState after C1."""
        resolver = MagicMock()
        settings = make_settings()
        settings.github.token = None
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "feature/42-test"
        mock_state_engine = MagicMock()
        mock_state_engine.get_state.return_value.current_phase = "research"
        mock_state_engine.get_state.return_value.workflow_name = "feature"

        tool = GetWorkContextTool(
            settings=settings,
            git_manager=mock_git,
            project_manager=MagicMock(),
            state_engine=mock_state_engine,
            workflow_status_resolver=resolver,
        )
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.phase == "research"


# ---------------------------------------------------------------------------
# C6 RED — GetWorkContextTool StateNotFoundError / StateBranchMismatchError (issue #298)
# ---------------------------------------------------------------------------


def _make_work_context_tool(
    tmp_path: Path,
    resolver_side_effect: Exception,
) -> GetWorkContextTool:
    """Return a GetWorkContextTool whose resolver raises the given exception."""
    mock_git = MagicMock()
    mock_git.get_current_branch.return_value = "feature/298-test"

    mock_resolver = MagicMock()
    mock_resolver.resolve_current.side_effect = resolver_side_effect

    settings = make_settings(tmp_path)

    return GetWorkContextTool(
        settings=settings,
        git_manager=mock_git,
        project_manager=MagicMock(),
        state_engine=MagicMock(),
        workflow_status_resolver=mock_resolver,
    )


class TestGetWorkContextStateErrors:
    """C6 (issue #298): StateNotFoundError / StateBranchMismatchError → error + RecoveryNote."""

    @pytest.mark.asyncio
    async def test_get_work_context_returns_error_with_recovery_note_when_state_absent(
        self, tmp_path: Path
    ) -> None:
        """StateNotFoundError from state_engine → graceful degradation (not error) after C1."""
        tool = _make_work_context_tool(
            tmp_path, resolver_side_effect=StateNotFoundError("feature/298-test")
        )
        ctx = NoteContext()
        result = await tool.execute(GetWorkContextInput(), ctx)

        # C1 (issue #268): graceful degradation path; state errors no longer hard-fail
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        assert isinstance(result, GetWorkContextOutput)
        assert result.success

    @pytest.mark.asyncio
    async def test_get_work_context_returns_error_with_recovery_note_on_mismatch(
        self, tmp_path: Path
    ) -> None:
        """StateBranchMismatchError from state_engine → graceful degradation after C1."""
        tool = _make_work_context_tool(
            tmp_path, resolver_side_effect=StateBranchMismatchError("branch mismatch")
        )
        ctx = NoteContext()
        result = await tool.execute(GetWorkContextInput(), ctx)

        # C1 (issue #268): graceful degradation path; state errors no longer hard-fail
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        assert isinstance(result, GetWorkContextOutput)
        assert result.success

    @pytest.mark.asyncio
    async def test_get_work_context_graceful_io_error_path_unchanged(self, tmp_path: Path) -> None:
        """OSError in resolver still uses existing graceful fallback (not error result)."""
        tool = _make_work_context_tool(tmp_path, resolver_side_effect=OSError("disk error"))
        ctx = NoteContext()
        result = await tool.execute(GetWorkContextInput(), ctx)

        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        assert isinstance(result, GetWorkContextOutput)
        assert result.success  # OSError → graceful degradation, not hard error


# ---------------------------------------------------------------------------
# C1 RED — GetWorkContextTool sub_role_hint + phase_instructions (issue #268)
# ---------------------------------------------------------------------------


class TestGetWorkContextSubRoleAndPhaseInstructions:
    """C1 MVP (issue #268): sub_role_hint and phase_instructions fields in response."""

    def _make_tool(self, phase: str, workflow_name: str = "feature") -> GetWorkContextTool:
        """Return a GetWorkContextTool whose resolver returns the given phase."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "feature/268-test"
        resolver = MagicMock()
        resolver.resolve_current.return_value = WorkflowStatusDTO(
            current_phase=phase,
            sub_phase=None,
            current_cycle=None,
            phase_source="state.json",
            phase_confidence="high",
            phase_detection_error=None,
        )
        mock_state_engine = MagicMock()
        mock_branch_state = MagicMock()
        mock_branch_state.workflow_name = workflow_name
        mock_branch_state.current_phase = phase
        mock_state_engine.get_state.return_value = mock_branch_state
        settings = make_settings()
        settings.github.token = None
        return GetWorkContextTool(
            settings=settings,
            git_manager=mock_git,
            project_manager=MagicMock(),
            state_engine=mock_state_engine,
            workflow_status_resolver=resolver,
            contracts_config=load_contracts_config(),
        )

    @pytest.mark.asyncio
    async def test_get_work_context_returns_sub_role_hint_for_known_phase(self) -> None:
        """sub_role_hint must equal 'implementer' when phase is 'implementation'."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(phase="implementation")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.sub_role_hint == "implementer"
        assert result.workflow_state_status is WorkflowStateStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_get_work_context_returns_phase_instructions_for_feature_implementation(
        self,
    ) -> None:
        """phase_instructions must be non-empty for (feature, implementation)."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(phase="implementation")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert "get_project_plan" in result.phase_instructions
        assert "run_tests" in result.phase_instructions

    @pytest.mark.asyncio
    async def test_get_work_context_returns_empty_string_for_unknown_workflow_phase(
        self,
    ) -> None:
        """Unknown (workflow, phase) combo must return empty string, never KeyError."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(phase="nonexistent_phase_xyz")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.phase_instructions == ""
        assert result.workflow_state_status is WorkflowStateStatus.INVALID_PHASE
        assert "research" in result.valid_phases

    @pytest.mark.asyncio
    async def test_get_work_context_returns_empty_string_when_workflow_unavailable(
        self,
    ) -> None:
        """Graceful fallback when workflow resolution raises (OSError path)."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "feature/268-test"
        resolver = MagicMock()
        resolver.resolve_current.side_effect = OSError("state.json missing")
        settings = make_settings()
        settings.github.token = None
        tool = GetWorkContextTool(
            settings=settings,
            git_manager=mock_git,
            project_manager=MagicMock(),
            state_engine=MagicMock(),
            workflow_status_resolver=resolver,
        )

        result = await tool.execute(GetWorkContextInput(), NoteContext())
        assert isinstance(result, GetWorkContextOutput)
        assert result.success

    # --- C1 correction: bug workflow entries ---

    @pytest.mark.asyncio
    async def test_get_work_context_returns_phase_instructions_for_bug_research(
        self,
    ) -> None:
        """phase_instructions for (bug, research) must contain key research actions."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(phase="research", workflow_name="bug")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert "get_issue" in result.phase_instructions
        assert "root cause" in result.phase_instructions.lower()

    @pytest.mark.asyncio
    async def test_get_work_context_returns_phase_instructions_for_bug_implementation(
        self,
    ) -> None:
        """phase_instructions for (bug, implementation) must contain TDD hard rules."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(phase="implementation", workflow_name="bug")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert "RED" in result.phase_instructions
        assert "get_project_plan" in result.phase_instructions


# ---------------------------------------------------------------------------
# C1 RED — GetWorkContextTool response restructuring (issue #268 F_268.13)
# ---------------------------------------------------------------------------


class TestGetWorkContextC1Restructuring:
    """C1 (issue #268 F_268.13): execute() restructuring + _format_context() rewrite.

    All tests in this class FAIL (RED) until C1 is implemented in discovery_tools.py.
    """

    def _make_tool(
        self,
        *,
        branch: str = "feature/268-test",
        workflow_name: str = "feature",
        current_phase: str = "implementation",
        issue_number: int = 268,
        parent_branch: str | None = "main",
        current_cycle: int | None = None,
        state_raises: Exception | None = None,
        github_token: str | None = None,
        github_issue: object | None = None,
    ) -> GetWorkContextTool:
        """Return a GetWorkContextTool pre-configured for C1 restructuring tests."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = branch

        mock_state_engine = MagicMock()
        if state_raises is not None:
            mock_state_engine.get_state.side_effect = state_raises
        else:
            mock_state = MagicMock()
            mock_state.workflow_name = workflow_name
            mock_state.current_phase = current_phase
            mock_state.issue_number = issue_number
            mock_state.parent_branch = parent_branch
            mock_state.current_cycle = current_cycle
            mock_state.current_sub_phase = None
            mock_state_engine.get_state.return_value = mock_state

        mock_resolver = MagicMock()
        mock_resolver.resolve_current.return_value = WorkflowStatusDTO(
            current_phase=current_phase,
            sub_phase=None,
            current_cycle=current_cycle,
            phase_source="state.json",
            phase_confidence="high",
            phase_detection_error=None,
        )

        mock_github = None
        if github_token is not None:
            mock_github = MagicMock()
            mock_github.get_issue.return_value = github_issue

        settings = make_settings(github_token=github_token)
        return GetWorkContextTool(
            settings=settings,
            git_manager=mock_git,
            project_manager=MagicMock(),
            state_engine=mock_state_engine,
            github_manager=mock_github,
            workflow_status_resolver=mock_resolver,
            contracts_config=load_contracts_config(),
        )

    def test_get_work_context_input_has_no_include_closed_recent(self) -> None:
        """GetWorkContextInput must reject include_closed_recent (field removed in C1)."""
        with pytest.raises(ValidationError):
            GetWorkContextInput(include_closed_recent=True)  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_get_work_context_returns_sub_role_hint_for_known_phase(self) -> None:
        """New format: orientation header shows 'Role: implementer' for implementation phase."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(current_phase="implementation")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.sub_role_hint == "implementer"

    @pytest.mark.asyncio
    async def test_get_work_context_returns_phase_instructions_for_feature_implementation(
        self,
    ) -> None:
        """New format: phase_instructions rendered under '### 🎯 Phase Instructions'."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(workflow_name="feature", current_phase="implementation")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert "get_project_plan" in result.phase_instructions

    @pytest.mark.asyncio
    async def test_get_work_context_returns_empty_string_for_unknown_workflow_phase(
        self,
    ) -> None:
        """Unknown (workflow, phase): no crash; fallback message shown under instruction header."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(workflow_name="unknownwf", current_phase="unknownphase")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.phase_instructions == ""
        assert result.workflow_state_status is WorkflowStateStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_get_work_context_returns_structured_invalid_phase_status(self) -> None:
        """Known workflow plus invalid phase returns status and valid phases only."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(workflow_name="feature", current_phase="invalid_phase")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.workflow_state_status is WorkflowStateStatus.INVALID_PHASE
        assert result.phase_instructions == ""
        assert tool._contracts_config is not None
        assert result.valid_phases == tuple(
            tool._contracts_config.workflows["feature"].get_phase_names()
        )

    @pytest.mark.asyncio
    async def test_get_work_context_does_not_synthesize_invalid_phase_prose(self) -> None:
        """Invalid phase recovery wording belongs to presentation configuration."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(workflow_name="feature", current_phase="invalid_phase")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.workflow_state_status is WorkflowStateStatus.INVALID_PHASE
        assert result.phase_instructions == ""
        assert "invalid_phase_warning" not in type(result).model_fields

    @pytest.mark.asyncio
    async def test_get_work_context_returns_workflow_name_from_branch_state(self) -> None:
        """Orientation header must contain 'Workflow: feature' sourced from BranchState."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(workflow_name="feature")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.workflow_name == "feature"

    @pytest.mark.asyncio
    async def test_get_work_context_returns_issue_number_from_branch_state(self) -> None:
        """Orientation header shows issue #268 from BranchState, not branch-name regex."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(branch="feature/no-number-in-name", issue_number=268)
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.issue_number == 268

    @pytest.mark.asyncio
    async def test_get_work_context_returns_parent_branch_from_branch_state(self) -> None:
        """Orientation header must show 'Parent: main' from BranchState.parent_branch."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(parent_branch="main")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.parent_branch == "main"

    @pytest.mark.asyncio
    async def test_get_work_context_omits_noise_fields(self) -> None:
        """Verify DTO attributes are present."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        mock_issue = MagicMock()
        mock_issue.number = 268
        tool = self._make_tool(github_token="test-token", github_issue=mock_issue)
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success

    @pytest.mark.asyncio
    async def test_get_work_context_phase_instructions_is_dominant_first_block(self) -> None:
        """Verify phase instructions are non-empty."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(workflow_name="feature", current_phase="implementation")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert len(result.phase_instructions) > 0

    @pytest.mark.asyncio
    async def test_get_work_context_renders_todo_discipline_reminder_in_header(self) -> None:
        """Verify success."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(workflow_name="feature", current_phase="implementation")
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success

    @pytest.mark.asyncio
    async def test_get_work_context_graceful_degradation_when_state_unavailable(self) -> None:
        """No error result when state is unavailable (bootstrap degradation)."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        tool = self._make_tool(state_raises=StateNotFoundError("feature/268-test"))
        tool._workflow_status_resolver.resolve_current.side_effect = StateNotFoundError(
            "feature/268-test"
        )

        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.current_branch == "feature/268-test"
        assert result.workflow_state_status is WorkflowStateStatus.MISSING


# ---------------------------------------------------------------------------
# C7 GREEN - GetWorkContextTool ContractsConfig injection (issue #268)
# ---------------------------------------------------------------------------


def _make_c7_contracts(
    workflow: str = "feature",
    phase: str = "implementation",
    sub_role: str = "implementer-c7",
    phase_instructions: str = "Do TDD. Call get_project_plan.",
    handover_template: str | None = "## Hand-over\nScope: ...",
) -> ContractsConfig:
    """Build a minimal ContractsConfig for C7 injection tests."""
    return ContractsConfig(
        merge_policy=MergePolicy(pr_allowed_phase="ready"),
        workflows={
            workflow: WorkflowEntry(
                phases=[
                    WorkflowPhaseEntry(
                        name=phase,
                        instructions=PhaseInstructionsSpec(
                            sub_role=sub_role,
                            phase_instructions=phase_instructions,
                            handover_template=handover_template,
                        ),
                    ),
                    WorkflowPhaseEntry(
                        name="ready",
                        instructions=PhaseInstructionsSpec(
                            sub_role="documenter",
                            phase_instructions="Create PR.",
                            handover_template=None,
                        ),
                    ),
                ]
            ),
        },
    )


class TestGetWorkContextC7ContractsInjection:
    """C7: Verify removal of hardcoded MVP maps and ContractsConfig injection."""

    def _make_c7_tool(
        self,
        contracts_config: ContractsConfig | None = None,
        context_loaded_writer: IContextLoadedWriter | None = None,
        workflow: str = "feature",
        phase: str = "implementation",
    ) -> GetWorkContextTool:
        """Return a GetWorkContextTool pre-configured for C7 tests."""
        mock_git = MagicMock()
        mock_git.get_current_branch.return_value = "feature/42-test"
        resolver = MagicMock()
        resolver.resolve_current.return_value = WorkflowStatusDTO(
            current_phase=phase,
            sub_phase=None,
            current_cycle=None,
            phase_source="state.json",
            phase_confidence="high",
            phase_detection_error=None,
        )
        mock_state_engine = MagicMock()
        mock_branch_state = MagicMock()
        mock_branch_state.workflow_name = workflow
        mock_branch_state.current_phase = phase
        mock_state_engine.get_state.return_value = mock_branch_state
        settings = make_settings()
        settings.github.token = None
        return GetWorkContextTool(
            settings=settings,
            git_manager=mock_git,
            project_manager=MagicMock(),
            state_engine=mock_state_engine,
            github_manager=MagicMock(),
            workphases_config=load_workphases_config(),
            workflow_status_resolver=resolver,
            contracts_config=contracts_config,
            context_loaded_writer=context_loaded_writer,
        )

    def test_sub_role_map_removed_from_module(self) -> None:
        assert not hasattr(discovery_module, "_SUB_ROLE_MAP")

    def test_phase_instructions_map_removed_from_module(self) -> None:
        assert not hasattr(discovery_module, "_PHASE_INSTRUCTIONS_MAP")

    @pytest.mark.asyncio
    async def test_sub_role_comes_from_contracts(self) -> None:
        """sub_role_hint must come from ContractsConfig, not hardcoded maps."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        contracts = _make_c7_contracts(sub_role="implementer-c7")
        tool = self._make_c7_tool(contracts_config=contracts)
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.sub_role_hint == "implementer-c7"

    @pytest.mark.asyncio
    async def test_phase_instructions_come_from_contracts(self) -> None:
        """phase_instructions must come from ContractsConfig, not hardcoded maps."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        contracts = _make_c7_contracts(
            phase_instructions="Do TDD. Call get_project_plan.",
        )
        tool = self._make_c7_tool(contracts_config=contracts)
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.phase_instructions == "Do TDD. Call get_project_plan."

    @pytest.mark.asyncio
    async def test_handover_template_in_response(self) -> None:
        """Hand-over template must appear in response when contracts provide one."""
        from mcp_server.schemas.tool_outputs import GetWorkContextOutput  # noqa: PLC0415

        contracts = _make_c7_contracts(handover_template="## Hand-over\nScope: ...")
        tool = self._make_c7_tool(contracts_config=contracts)
        result = await tool.execute(GetWorkContextInput(), NoteContext())

        assert isinstance(result, GetWorkContextOutput)
        assert result.success
        assert result.handover_template == "## Hand-over\nScope: ..."

    @pytest.mark.asyncio
    async def test_context_loaded_writer_called_on_success(self) -> None:
        """IContextLoadedWriter.set_context_loaded must be called after successful execute."""
        writer = MagicMock(spec=IContextLoadedWriter)
        tool = self._make_c7_tool(context_loaded_writer=writer)
        await tool.execute(GetWorkContextInput(), NoteContext())

        writer.set_context_loaded.assert_called_once_with("feature/42-test", value=True)
