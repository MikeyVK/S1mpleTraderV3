"""RED/Green tests for GitPullTool existence."""

import importlib


def test_git_pull_tool_exists():
    """GitPullTool should exist and be importable."""
    module = importlib.import_module("mcp_server.tools.git_pull_tool")
    tool_cls = getattr(module, "GitPullTool", None)

    # RED: this will fail until GitPullTool is implemented.
    assert tool_cls is not None, "GitPullTool is not implemented yet"
