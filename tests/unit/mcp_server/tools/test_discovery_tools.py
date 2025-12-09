"""Tests for discovery tools."""
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.tools.discovery_tools import GetWorkContextTool, SearchDocumentationTool


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
        """Should return search results from DocManager."""
        mock_results = [
            {
                "file_path": "docs/architecture/DATA_FLOW.md",
                "title": "Data Flow",
                "snippet": "DTOs flow through the pipeline...",
                "relevance_score": 0.85,
                "line_number": 5
            }
        ]

        with patch("mcp_server.tools.discovery_tools.DocManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.search.return_value = mock_results
            MockManager.return_value = mock_instance

            result = await tool.execute(query="DTO flow")

        assert not result.is_error
        assert "DATA_FLOW.md" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_search_with_scope(self, tool: SearchDocumentationTool) -> None:
        """Should pass scope to DocManager."""
        with patch("mcp_server.tools.discovery_tools.DocManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.search.return_value = []
            MockManager.return_value = mock_instance

            await tool.execute(query="code style", scope="coding_standards")

        mock_instance.search.assert_called_once_with(
            "code style",
            scope="coding_standards",
            max_results=10
        )

    @pytest.mark.asyncio
    async def test_search_empty_results(self, tool: SearchDocumentationTool) -> None:
        """Should handle no results gracefully."""
        with patch("mcp_server.tools.discovery_tools.DocManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.search.return_value = []
            MockManager.return_value = mock_instance

            result = await tool.execute(query="xyznonexistent")

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
        with patch("mcp_server.tools.discovery_tools.GitManager") as MockGit:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/42-implement-dto"
            mock_git.get_recent_commits.return_value = []
            MockGit.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None  # No GitHub

                result = await tool.execute()

        assert not result.is_error
        assert "feature/42-implement-dto" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_get_context_extracts_issue_number(
        self, tool: GetWorkContextTool
    ) -> None:
        """Should extract issue number from branch name."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as MockGit:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/42-implement-dto"
            mock_git.get_recent_commits.return_value = []
            MockGit.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None

                result = await tool.execute()

        assert not result.is_error
        # Should identify issue #42 from branch name
        assert "42" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_get_context_detects_tdd_phase(
        self, tool: GetWorkContextTool
    ) -> None:
        """Should detect TDD phase from recent commits."""
        with patch("mcp_server.tools.discovery_tools.GitManager") as MockGit:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/42-dto"
            mock_git.get_recent_commits.return_value = [
                "test: Add failing test for DTO validation"
            ]
            MockGit.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = None

                result = await tool.execute()

        assert not result.is_error
        # Should identify red phase from recent test commit
        assert "red" in result.content[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_get_context_with_github_integration(
        self, tool: GetWorkContextTool
    ) -> None:
        """Should handle GitHub integration gracefully.

        Note: Full GitHub integration is tested via integration tests.
        This unit test verifies the tool handles errors gracefully.
        """
        with patch("mcp_server.tools.discovery_tools.GitManager") as MockGit:
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = "feature/42-implement-dto"
            mock_git.get_recent_commits.return_value = []
            MockGit.return_value = mock_git

            with patch("mcp_server.tools.discovery_tools.settings") as mock_settings:
                mock_settings.github.token = "test-token"

                # Execute - GitHub code path will fail gracefully
                result = await tool.execute()

        # Should not error even if GitHub fetch fails
        assert not result.is_error
        # Should still contain branch info
        assert "feature/42-implement-dto" in result.content[0]["text"]
        assert "42" in result.content[0]["text"]
