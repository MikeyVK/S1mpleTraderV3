"""RED/Green tests for GitFetchTool existence."""

from mcp_server.tools.git_fetch_tool import GitFetchTool


def test_git_fetch_tool_exists() -> None:
    """GitFetchTool should exist (scaffolded + implemented)."""
    assert GitFetchTool is not None
