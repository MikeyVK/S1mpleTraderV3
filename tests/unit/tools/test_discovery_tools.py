"""Tests for discovery tools."""
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.tools.discovery_tools import (
    GetWorkContextInput,
    GetWorkContextTool,
    SearchDocumentationInput,
    SearchDocumentationTool,
)


class TestSearchDocumentationTool:
    """Tests for SearchDocumentationTool."""

    @pytest.fixture
    def tool(self) -> SearchDocumentationTool:
        """Create tool instance."""
        return SearchDocumentationTool()

    def test_tool_name(self, tool: SearchDocumentationTool) -> None:
        """Should have correct name."""
        assert tool.name == "search_documentation"

    def test_tool_description(self, tool: SearchDocumentationTool) -> None:
        """Should have meaningful description."""
        assert "search" in tool.description.lower()
        assert "docs" in tool.description.lower()

    def test_tool_schema_has_query(self, tool: SearchDocumentationTool) -> None:
        """Should require query parameter."""
        schema = tool.input_schema
        assert "query" in schema["properties"]
        assert "query" in schema["required"]

    def test_tool_schema_has_scope(self, tool: SearchDocumentationTool) -> None:
        """Should have optional scope parameter."""
        schema = tool.input_schema
        assert "scope" in schema["properties"]
        assert "scope" not in schema.get("required", [])

    @pytest.mark.asyncio
    async def test_search_returns_results(self, tool: SearchDocumentationTool) -> None:
        """Should return search results from DocumentIndexer + SearchService."""
        mock_results = [
            {
                "path": "docs/architecture/DATA_FLOW.md",
                "title": "Data Flow",
                "_snippet": "DTOs flow through the pipeline...",
                "_relevance": 0.85,
                "type": "architecture"
            }
        ]

        with patch("mcp_server.tools.discovery_tools.DocumentIndexer.build_index") as mock_build, \
             patch("mcp_server.tools.discovery_tools.SearchService.search_index") as mock_search:
            mock_build.return_value = {}  # Empty index dict
            mock_search.return_value = mock_results

            result = await tool.execute(SearchDocumentationInput(query="DTO flow"))

        assert not result.is_error
        assert "DATA_FLOW.md" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_search_with_scope(self, tool: SearchDocumentationTool) -> None:
        """Should pass scope to SearchService."""
        with patch("mcp_server.tools.discovery_tools.DocumentIndexer.build_index") as mock_build, \
             patch("mcp_server.tools.discovery_tools.SearchService.search_index") as mock_search:
            mock_build.return_value = {}
            mock_search.return_value = []

            await tool.execute(
                SearchDocumentationInput(query="code style", scope="coding_standards")
            )

        mock_search.assert_called_once_with(
            index={},
            query="code style",
            max_results=10,
            scope="coding_standards"
        )

    @pytest.mark.asyncio
    async def test_search_empty_results(self, tool: SearchDocumentationTool) -> None:
        """Should handle no results gracefully."""
        with patch("mcp_server.tools.discovery_tools.DocumentIndexer.build_index") as mock_build, \
             patch("mcp_server.tools.discovery_tools.SearchService.search_index") as mock_search:
            mock_build.return_value = {}
            mock_search.return_value = []

            result = await tool.execute(SearchDocumentationInput(query="xyznonexistent"))

        assert not result.is_error
        assert "no results" in result.content[0]["text"].lower()


class TestGetWorkContextTool:
    """Tests for GetWorkContextTool."""

    @pytest.fixture
    def tool(self) -> GetWorkContextTool:
        """Create tool instance."""
        return GetWorkContextTool()

    def test_tool_name(self, tool: GetWorkContextTool) -> None:
        """Should have correct name."""
        assert tool.name == "get_work_context"

    def test_tool_description(self, tool: GetWorkContextTool) -> None:
        """Should have meaningful description."""
        assert "context" in tool.description.lower()

    def test_tool_schema_has_include_closed(self, tool: GetWorkContextTool) -> None:
        """Should have optional include_closed_recent parameter."""
        schema = tool.input_schema
        assert "include_closed_recent" in schema["properties"]
        assert "include_closed_recent" not in schema.get("required", [])

    @pytest.mark.asyncio
    async def test_get_context_returns_branch_info(
        self, tool: GetWorkContextTool
    ) -> None:
        """Should include current branch information."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/42-implement-dto"
            mock_git.get_recent_commits.return_value = []
            mock_git_class.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None  # No GitHub

                result = await tool.execute(GetWorkContextInput())

        assert not result.is_error
        assert "feature/42-implement-dto" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_get_context_extracts_issue_number(
        self, tool: GetWorkContextTool
    ) -> None:
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
        # Should identify issue #42 from branch name
        assert "42" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_get_context_extracts_issue_number_alternate_format(
        self, tool: GetWorkContextTool
    ) -> None:
        """Should extract issue number from issue-123 format."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "issue-123"
            mock_git.get_recent_commits.return_value = []
            mock_git_class.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None
                result = await tool.execute(GetWorkContextInput())

        assert "123" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_get_context_detects_tdd_phase(
        self, tool: GetWorkContextTool
    ) -> None:
        """Should detect TDD phase from recent commits."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/42-dto"
            mock_git.get_recent_commits.return_value = [
                "test: Add failing test for DTO validation"
            ]
            mock_git_class.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None

                result = await tool.execute(GetWorkContextInput())

        assert not result.is_error
        # Should identify red phase from recent test commit
        assert "red" in result.content[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_detect_tdd_phase_variations(
        self, tool: GetWorkContextTool
    ) -> None:
        """Should detect green, refactor, and docs phases."""
        test_cases = [
            (["feat: new feature"], "green"),
            (["pass: all tests passed"], "green"),
            (["refactor: clean up"], "refactor"),
            (["docs: update readme"], "docs"),
            (["chore: misc"], "unknown"),
        ]

        emojis = {
            "green": "🟢",
            "refactor": "🔄",
            "docs": "📝",
            "unknown": "❓"
        }

        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "main"
            mock_git_class.return_value = mock_git
            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None

                for commits, expected in test_cases:
                    mock_git.get_recent_commits.return_value = commits
                    result = await tool.execute(GetWorkContextInput())
                    text = result.content[0]["text"]
                    assert expected in text or emojis[expected] in text

    @pytest.mark.asyncio
    async def test_get_context_with_github_integration(
        self, tool: GetWorkContextTool
    ) -> None:
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
        assert "feature/42-implement-dto" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_get_context_github_success(
        self, tool: GetWorkContextTool
    ) -> None:
        """Should successfully retrieve and format GitHub issue info."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as mock_git_class:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/42-feat"
            mock_git.get_recent_commits.return_value = []
            mock_git_class.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = "test-token"

                with patch("mcp_server.tools.discovery_tools.GitHubManager") as mock_gh_cls:
                    mock_gh = MagicMock()
                    # get_issue returns Issue object (not dict)
                    mock_issue = MagicMock()
                    mock_issue.number = 42
                    mock_issue.title = "Implement Feature"
                    mock_issue.body = "Description.\n\n- [ ] Task 1\n- [x] Task 2"
                    mock_label = MagicMock()
                    mock_label.name = "enhancement"
                    mock_issue.labels = [mock_label]
                    mock_gh.get_issue.return_value = mock_issue
                    mock_gh.list_issues.return_value = [
                        MagicMock(number=10, title="Closed 1")
                    ]
                    mock_gh_cls.return_value = mock_gh

                    result = await tool.execute(
                        GetWorkContextInput(include_closed_recent=True)
                    )

        text = result.content[0]["text"]
        assert "Active Issue: #42" in text
        assert "Implement Feature" in text
        assert "enhancement" in text
        assert "Task 1" in text  # Checklist extraction
        assert "Task 2" in text
        assert "Recently Closed Issues" in text
        assert "#10 Closed 1" in text
