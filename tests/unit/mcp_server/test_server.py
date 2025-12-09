"""Tests for MCP Server tool registration."""
from unittest.mock import patch, MagicMock


class TestServerToolRegistration:
    """Tests for server tool registration."""

    def test_github_tools_always_registered(self) -> None:
        """GitHub tools should always be registered, even without token."""
        # Patch settings to simulate no GitHub token
        with patch("mcp_server.server.settings") as mock_settings:
            mock_settings.server.name = "test-server"
            mock_settings.github.token = None  # No token configured
            mock_settings.github.owner = "test"
            mock_settings.github.repo = "repo"

            # Import after patching to get fresh instance
            from mcp_server.server import MCPServer

            server = MCPServer()

            # Get tool names
            tool_names = [t.name for t in server.tools]

            # GitHub issue tools should always be present
            assert "create_issue" in tool_names
            assert "list_issues" in tool_names
            assert "get_issue" in tool_names
            assert "close_issue" in tool_names

    def test_github_tools_registered_with_token(self) -> None:
        """GitHub tools should be registered when token is configured."""
        with patch("mcp_server.server.settings") as mock_settings, \
             patch("mcp_server.resources.github.GitHubManager") as mock_res_manager, \
             patch("mcp_server.tools.pr_tools.GitHubManager") as mock_pr_manager, \
             patch("mcp_server.tools.label_tools.GitHubManager") as mock_label_manager:
            mock_settings.server.name = "test-server"
            mock_settings.github.token = "test-token"
            mock_settings.github.owner = "test"
            mock_settings.github.repo = "repo"

            # Mock all GitHubManager instances to avoid actual API calls
            mock_res_manager.return_value = MagicMock()
            mock_pr_manager.return_value = MagicMock()
            mock_label_manager.return_value = MagicMock()

            from mcp_server.server import MCPServer

            server = MCPServer()

            tool_names = [t.name for t in server.tools]

            # All GitHub tools should be present
            assert "create_issue" in tool_names
            assert "list_issues" in tool_names
            assert "get_issue" in tool_names
            assert "close_issue" in tool_names
            assert "create_pr" in tool_names
            assert "add_labels" in tool_names
