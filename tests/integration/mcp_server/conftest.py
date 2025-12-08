"""Integration test configuration for MCP server tests."""
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def server():
    """
    Create an MCPServer instance with mocked GitHub dependencies.

    This patches the GitHubAdapter at the manager level so all GitHub
    operations return mock data instead of hitting the real API.
    """
    # Patch the GitHubAdapter at the point where it's instantiated
    with patch(
        "mcp_server.managers.github_manager.GitHubAdapter"
    ) as mock_adapter_class:
        # Configure the mock adapter
        mock_adapter = MagicMock()
        mock_adapter.list_issues.return_value = []
        mock_adapter_class.return_value = mock_adapter

        # Now import and create the server with mocked dependencies
        # pylint: disable=import-outside-toplevel
        from mcp_server.server import MCPServer
        yield MCPServer()
