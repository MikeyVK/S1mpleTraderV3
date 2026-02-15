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
