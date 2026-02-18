"""Tests for Discovery Tools (search_documentation, get_work_context)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from mcp_server.config.settings import settings
from mcp_server.tools.discovery_tools import (
    GetWorkContextInput,
    GetWorkContextTool,
    SearchDocumentationInput,
    SearchDocumentationTool,
)


class TestSearchDocumentationTool:
    """Tests for SearchDocumentationTool."""

    @pytest.fixture()
    def tool(self) -> SearchDocumentationTool:
        """Fixture to instantiate SearchDocumentationTool."""
        return SearchDocumentationTool()

    def test_tool_name(self, tool: SearchDocumentationTool) -> None:
        """Should have correct tool name."""
        assert tool.name == "search_documentation"

    def test_tool_description(self, tool: SearchDocumentationTool) -> None:
        """Should have a non-empty description."""
        assert tool.description
        assert len(tool.description) > 0

    def test_tool_schema_has_query(self, tool: SearchDocumentationTool) -> None:  # noqa: ARG002
        """Should require query parameter."""
        with pytest.raises(ValidationError):
            SearchDocumentationInput()  # Missing required query

    def test_tool_schema_has_scope(self, tool: SearchDocumentationTool) -> None:  # noqa: ARG002
        """Should have scope with default value."""
        result = SearchDocumentationInput(query="test")
        assert result.scope == "all"

    @pytest.mark.asyncio
    async def test_search_returns_results(self, tool: SearchDocumentationTool) -> None:
        """Should return search results with snippets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock docs directory
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            test_file = docs_dir / "test.md"
            test_file.write_text("# Test Document\nContains worker implementation info.")

            with patch.object(settings.server, "workspace_root", tmpdir):
                result = await tool.execute(SearchDocumentationInput(query="worker"))

            assert not result.is_error
            assert "test.md" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_search_with_scope(self, tool: SearchDocumentationTool) -> None:
        """Should filter by scope."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            (docs_dir / "architecture").mkdir(parents=True)

            test_file = docs_dir / "architecture" / "design.md"
            test_file.write_text("# Architecture Design")

            with patch.object(settings.server, "workspace_root", tmpdir):
                result = await tool.execute(
                    SearchDocumentationInput(query="design", scope="architecture")
                )

            assert not result.is_error

    @pytest.mark.asyncio
    async def test_search_empty_results(self, tool: SearchDocumentationTool) -> None:
        """Should handle no results gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()

            test_file = docs_dir / "test.md"
            test_file.write_text("# Test")

            with patch.object(settings.server, "workspace_root", tmpdir):
                result = await tool.execute(SearchDocumentationInput(query="nonexistent123"))

            assert not result.is_error
            assert "No results" in result.content[0]["text"]


class TestGetWorkContextTool:
    """Tests for GetWorkContextTool."""

    @pytest.fixture()
    def tool(self) -> GetWorkContextTool:
        """Fixture to instantiate GetWorkContextTool."""
        return GetWorkContextTool()

    def test_tool_name(self, tool: GetWorkContextTool) -> None:
        """Should have correct tool name."""
        assert tool.name == "get_work_context"

    def test_tool_description(self, tool: GetWorkContextTool) -> None:
        """Should have a non-empty description containing 'workflow phase'."""
        assert tool.description
        assert "workflow phase" in tool.description.lower()

    def test_tool_schema_has_include_closed(self, tool: GetWorkContextTool) -> None:  # noqa: ARG002
        """Should have include_closed_recent with default False."""
        result = GetWorkContextInput()
        assert result.include_closed_recent is False

    @pytest.mark.asyncio
    async def test_get_context_returns_branch_info(self, tool: GetWorkContextTool) -> None:
        """Should return branch information."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "main"
            mock_git.get_recent_commits.return_value = []
            mock_git_class.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None

                result = await tool.execute(GetWorkContextInput())

        assert not result.is_error
        assert "main" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_get_context_extracts_issue_number(self, tool: GetWorkContextTool) -> None:
        """Should extract issue number from branch name."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/42-implement-dto"
            mock_git.get_recent_commits.return_value = []
            mock_git_class.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None

                result = await tool.execute(GetWorkContextInput())

        assert not result.is_error
        assert "#42" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_get_context_extracts_issue_number_alternate_format(
        self, tool: GetWorkContextTool
    ) -> None:
        """Should extract issue from fix/ branch."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "fix/99-bug"
            mock_git.get_recent_commits.return_value = []
            mock_git_class.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None

                result = await tool.execute(GetWorkContextInput())

        assert not result.is_error
        assert "#99" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_get_context_detects_workflow_phase_from_commit_scope(
        self, tool: GetWorkContextTool
    ) -> None:
        """Should detect workflow phase deterministically from commit-scope."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/42-dto"
            # Commit with proper commit-scope format (P_TDD_SP_RED)
            mock_git.get_recent_commits.return_value = [
                "test(P_TDD_SP_RED): add failing test for DTO validation"
            ]
            mock_git_class.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None

                result = await tool.execute(GetWorkContextInput())

        assert not result.is_error
        text = result.content[0]["text"].lower()
        # Should identify tdd phase with red sub-phase from commit-scope
        assert "tdd" in text
        assert "red" in text or "🔴" in result.content[0]["text"]
        assert "commit-scope" in text  # Source should be commit-scope

    @pytest.mark.asyncio
    async def test_detect_workflow_phase_variations(self, tool: GetWorkContextTool) -> None:
        """Should detect all 7 workflow phases from commit-scope."""
        test_cases = [
            ("docs(P_RESEARCH): initial research", "research", "🔍"),
            ("chore(P_PLANNING): define tasks", "planning", "📋"),
            ("docs(P_DESIGN): architecture design", "design", "🎨"),
            ("feat(P_TDD_SP_GREEN): implement feature", "tdd", "🧪"),
            ("test(P_INTEGRATION_SP_E2E): e2e tests", "integration", "🔗"),
            ("docs(P_DOCUMENTATION): update readme", "documentation", "📝"),
            ("chore(P_COORDINATION): sync with team", "coordination", "🤝"),
        ]

        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "main"
            mock_git_class.return_value = mock_git
            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None

                for commit, expected_phase, expected_emoji in test_cases:
                    mock_git.get_recent_commits.return_value = [commit]
                    result = await tool.execute(GetWorkContextInput())
                    text = result.content[0]["text"].lower()
                    # Check phase name or emoji present
                    assert expected_phase in text or expected_emoji in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_get_context_with_github_integration(self, tool: GetWorkContextTool) -> None:
        """Should handle GitHub integration gracefully (error case)."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/42-implement-dto"
            mock_git.get_recent_commits.return_value = []
            mock_git_class.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = "test-token"

                # Execute - GitHub code path will fail gracefully
                result = await tool.execute(GetWorkContextInput())

        # Should not error even if GitHub fetch fails
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_get_context_github_success(self, tool: GetWorkContextTool) -> None:
        """Should include GitHub issue when configured."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/42-test"
            mock_git.get_recent_commits.return_value = []
            mock_git_class.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.GitHubManager") as mock_gh_class:
                mock_gh = MagicMock()
                mock_issue = MagicMock()
                mock_issue.number = 42
                mock_issue.title = "Test Issue"
                mock_issue.body = "Test body"
                mock_issue.labels = []
                mock_gh.get_issue.return_value = mock_issue
                mock_gh_class.return_value = mock_gh

                with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                    mock_settings.github.token = "test-token"

                    result = await tool.execute(GetWorkContextInput())

            assert not result.is_error
            assert "Test Issue" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_get_context_shows_error_message_when_phase_unknown(
        self, tool: GetWorkContextTool
    ) -> None:
        """Should display error_message when phase detection fails (no state.json)."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "main"
            # No commits with valid scope -> will fallback to unknown with error_message
            mock_git.get_recent_commits.return_value = ["chore: random commit"]
            mock_git_class.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None

                # Mock ScopeDecoder to return unknown with error_message
                with patch("mcp_server.tools.discovery_tools.ScopeDecoder") as mock_decoder_class:
                    mock_decoder = MagicMock()
                    mock_decoder.detect_phase.return_value = {
                        "workflow_phase": "unknown",
                        "sub_phase": None,
                        "source": "unknown",
                        "confidence": "unknown",
                        "raw_scope": None,
                        "error_message": (
                            "Phase detection failed. "
                            "Recovery: Run transition_phase(to_phase='<phase>') "
                            "or commit with scope 'type(P_PHASE): message'."
                        ),
                    }
                    mock_decoder_class.return_value = mock_decoder

                    result = await tool.execute(GetWorkContextInput())

        assert not result.is_error
        text = result.content[0]["text"]
        # Should show unknown phase
        assert "unknown" in text.lower() or "❓" in text
        # Should show recovery info with error_message
        assert "Recovery Info" in text



class TestGetWorkContextTddCycleInfo:
    """Tests for TDD cycle info in get_work_context.

    Issue #146 Cycle 3: Conditional visibility of tdd_cycle_info.
    """

    @pytest.fixture()
    def tool(self) -> GetWorkContextTool:
        """Fixture to instantiate GetWorkContextTool."""
        return GetWorkContextTool()

    @pytest.mark.asyncio
    async def test_tdd_cycle_info_shown_during_tdd_phase(
        self, tool: GetWorkContextTool, tmp_path: Path
    ) -> None:
        """Test that tdd_cycle_info appears when in TDD phase.

        Issue #146 Cycle 3: Conditional visibility based on workflow_phase.
        """
        workspace_root = tmp_path

        # Create minimal project structure
        from mcp_server.managers.project_manager import ProjectManager
        from mcp_server.managers.phase_state_engine import PhaseStateEngine

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize project
        project_manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Save planning deliverables with total=2 (matching 2 cycles)
        planning_deliverables = {
            "tdd_cycles": {
                "total": 2,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": " & Storage",
                        "deliverables": ["ProjectManager schema"],
                        "exit_criteria": "Schema validated",
                    },
                    {
                        "cycle_number": 2,
                        "name": "Validation Logic",
                        "deliverables": ["Cycle validation"],
                        "exit_criteria": "All validation covered",
                    },
                ],
            }
        }
        project_manager.save_planning_deliverables(146, planning_deliverables)

        # Set TDD phase with current_tdd_cycle = 2
        state_engine.initialize_branch(
            branch="feature/146-tdd-cycle-tracking", issue_number=146, initial_phase="tdd"
        )
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        state["current_tdd_cycle"] = 2
        state_engine._save_state("feature/146-tdd-cycle-tracking", state)

        # Mock Git and settings
        with (
            patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class,
            patch("mcp_server.tools.discovery_tools.ScopeDecoder") as mock_decoder_class,
            patch("mcp_server.tools.discovery_tools.settings") as mock_settings,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            # Provide TDD-scoped commit so ScopeDecoder has context
            mock_git.get_recent_commits.return_value = [
                "test(P_TDD_SP_GREEN): add cycle info display"
            ]
            mock_git_class.return_value = mock_git

            mock_settings.github.token = None
            mock_settings.server.workspace_root = workspace_root

            # ScopeDecoder returns TDD phase from commit scope
            mock_decoder = MagicMock()
            mock_decoder.detect_phase.return_value = {
                "workflow_phase": "tdd",
                "sub_phase": "green",
                "source": "commit-scope",
                "confidence": "high",
                "raw_scope": "P_TDD_SP_GREEN",
            }
            mock_decoder_class.return_value = mock_decoder

            result = await tool.execute(GetWorkContextInput())

        # Assert - tdd_cycle_info should be present
        assert not result.is_error, f"Expected success, got error: {result.content}"
        text = result.content[0]["text"]
        # Check for TDD cycle info (case insensitive)
        assert (
            "TDD Cycle" in text or "tdd cycle" in text.lower()
        ), f"Expected cycle info in output: {text}"
        assert "Validation Logic" in text, f"Expected cycle name in output: {text}"
        assert "2" in text, f"Expected current cycle number in output: {text}"
    @pytest.mark.asyncio
    async def test_tdd_cycle_info_hidden_outside_tdd_phase(
        self, tool: GetWorkContextTool, tmp_path: Path
    ) -> None:
        """Test that tdd_cycle_info is hidden when NOT in TDD phase.

        Issue #146 Cycle 3: Conditional visibility - no noise outside TDD.
        """
        workspace_root = tmp_path

        # Create minimal project structure
        from mcp_server.managers.project_manager import ProjectManager
        from mcp_server.managers.phase_state_engine import PhaseStateEngine

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize project
        project_manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        # Save planning deliverables
        planning_deliverables = {
            "tdd_cycles": {
                "total": 1,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": "Schema & Storage",
                        "deliverables": ["ProjectManager schema"],
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
            patch("mcp_server.tools.discovery_tools.ScopeDecoder") as mock_decoder_class,
            patch("mcp_server.tools.discovery_tools.settings") as mock_settings,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git.get_recent_commits.return_value = []
            mock_git_class.return_value = mock_git

            mock_settings.github.token = None
            mock_settings.server.workspace_root = workspace_root

            # ScopeDecoder returns DESIGN phase (NOT tdd)
            mock_decoder = MagicMock()
            mock_decoder.detect_phase.return_value = {
                "workflow_phase": "design",
                "sub_phase": None,
                "source": "state.json",
                "confidence": "high",
                "raw_scope": None,
            }
            mock_decoder_class.return_value = mock_decoder

            result = await tool.execute(GetWorkContextInput())

        # Assert - NO tdd_cycle_info in design phase
        assert not result.is_error
        text = result.content[0]["text"]
        # Should NOT mention TDD cycle info or cycle names
        assert "TDD Cycle" not in text, f"Expected NO cycle info in design phase: {text}"
        assert (
            "Validation Logic" not in text
        ), f"Expected NO cycle name in design phase: {text}"

    @pytest.mark.asyncio
    async def test_tdd_cycle_info_graceful_degradation(
        self, tool: GetWorkContextTool, tmp_path: Path
    ) -> None:
        """Test graceful degradation when planning deliverables missing.

        Issue #146 Cycle 3: Avoid crashes if planning_deliverables not saved.
        """
        workspace_root = tmp_path

        # Create minimal project structure WITHOUT planning deliverables
        from mcp_server.managers.project_manager import ProjectManager
        from mcp_server.managers.phase_state_engine import PhaseStateEngine

        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        # Initialize project WITHOUT planning deliverables
        project_manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )
        # NOTE: Deliberately NOT calling save_planning_deliverables

        # Set TDD phase
        state_engine.initialize_branch(
            branch="feature/146-tdd-cycle-tracking", issue_number=146, initial_phase="tdd"
        )

        # Mock Git
        with (
            patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class,
            patch("mcp_server.tools.discovery_tools.ScopeDecoder") as mock_decoder_class,
            patch("mcp_server.tools.discovery_tools.settings") as mock_settings,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            mock_git.get_recent_commits.return_value = []
            mock_git_class.return_value = mock_git

            mock_settings.github.token = None
            mock_settings.server.workspace_root = workspace_root

            # ScopeDecoder returns TDD phase
            mock_decoder = MagicMock()
            mock_decoder.detect_phase.return_value = {
                "workflow_phase": "tdd",
                "sub_phase": "red",
                "source": "state.json",
                "confidence": "high",
                "raw_scope": None,
            }
            mock_decoder_class.return_value = mock_decoder

            result = await tool.execute(GetWorkContextInput())

        # Assert - tool should NOT crash
        assert not result.is_error, f"Tool crashed: {result.content}"
        text = result.content[0]["text"]
        # Should show TDD phase
        assert "tdd" in text.lower() or "🔴" in text or "🟢" in text


class TestTddCycleInfoStatusField:
    """Tests for the status field in tdd_cycle_info (Issue #146 Cycle 7 D2).

    design.md:365-376 specifies tdd_cycle_info must include status='in_progress'.
    discovery_tools.py:168-175 did not include this field.
    """

    @pytest.fixture()
    def tool(self) -> GetWorkContextTool:
        """Fixture to instantiate GetWorkContextTool."""
        return GetWorkContextTool()

    @pytest.mark.asyncio
    async def test_tdd_cycle_info_includes_status_field(
        self, tool: GetWorkContextTool, tmp_path: Path
    ) -> None:
        """tdd_cycle_info must include status='in_progress' per design.md:375.

        Issue #146 Cycle 7 D2: Align implementation with design spec.
        The status field is always 'in_progress' when the cycle is active.
        """
        from mcp_server.managers.phase_state_engine import PhaseStateEngine
        from mcp_server.managers.project_manager import ProjectManager

        workspace_root = tmp_path
        project_manager = ProjectManager(workspace_root=workspace_root)
        state_engine = PhaseStateEngine(
            workspace_root=workspace_root, project_manager=project_manager
        )

        project_manager.initialize_project(
            issue_number=146, issue_title="TDD Cycle Tracking", workflow_name="feature"
        )

        planning_deliverables = {
            "tdd_cycles": {
                "total": 1,
                "cycles": [
                    {
                        "cycle_number": 1,
                        "name": "Status Field Test",
                        "deliverables": ["Add status field"],
                        "exit_criteria": "Status field present in output",
                    }
                ],
            }
        }
        project_manager.save_planning_deliverables(146, planning_deliverables)

        state_engine.initialize_branch(
            branch="feature/146-tdd-cycle-tracking", issue_number=146, initial_phase="tdd"
        )
        # Set current_tdd_cycle so tdd_cycle_info is populated
        state = state_engine.get_state("feature/146-tdd-cycle-tracking")
        state["current_tdd_cycle"] = 1
        state_engine._save_state("feature/146-tdd-cycle-tracking", state)

        with (
            patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class,
            patch("mcp_server.tools.discovery_tools.ScopeDecoder") as mock_decoder_class,
            patch("mcp_server.tools.discovery_tools.settings") as mock_settings,
        ):
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/146-tdd-cycle-tracking"
            # Provide a non-empty commits list so ScopeDecoder is invoked (not short-circuited)
            mock_git.get_recent_commits.return_value = [
                "test(P_TDD_SP_RED): add status field test"
            ]
            mock_git_class.return_value = mock_git

            mock_settings.github.token = None
            mock_settings.server.workspace_root = workspace_root

            mock_decoder = MagicMock()
            mock_decoder.detect_phase.return_value = {
                "workflow_phase": "tdd",
                "sub_phase": "red",
                "source": "state.json",
                "confidence": "high",
                "raw_scope": None,
            }
            mock_decoder_class.return_value = mock_decoder

            result = await tool.execute(GetWorkContextInput())

        assert not result.is_error, f"Tool failed: {result.content}"
        # The status field must appear in the rendered output (in_progress)
        text = result.content[0]["text"]
        assert (
            "in_progress" in text or "in progress" in text.lower()
        ), f"Expected 'in_progress' status in tdd_cycle_info output: {text}"
