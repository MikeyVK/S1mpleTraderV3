"""Behavior tests for GitFetchTool.

Also covers input schema helpers for 100% module coverage.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_server.core.exceptions import PreflightError
from mcp_server.tools.git_fetch_tool import GitFetchInput, GitFetchTool, _input_schema


def test_git_fetch_input_schema_helper_handles_none() -> None:
    """_input_schema(None) returns an empty schema."""

    assert _input_schema(None) == {}


def test_git_fetch_input_schema_helper_returns_model_schema() -> None:
    """_input_schema(model) returns a JSON schema dict."""

    schema = _input_schema(GitFetchInput)
    assert isinstance(schema, dict)
    assert "properties" in schema



def test_git_fetch_tool_input_schema_property() -> None:
    """Tool.input_schema delegates to _input_schema(args_model)."""

    tool = GitFetchTool(manager=Mock())
    schema = tool.input_schema
    assert isinstance(schema, dict)
    assert "properties" in schema


@pytest.mark.asyncio
async def test_git_fetch_success_returns_text() -> None:
    """Returns ToolResult.text when manager fetch succeeds."""

    manager = Mock()
    manager.fetch.return_value = "Fetched from origin: 1 ref(s)"
    tool = GitFetchTool(manager=manager)

    run_sync = AsyncMock(return_value=manager.fetch.return_value)
    with patch("mcp_server.tools.git_fetch_tool.anyio.to_thread.run_sync", new=run_sync):
        result = await tool.execute(GitFetchInput())

    assert result.is_error is False
    assert "Fetched from origin" in str(result)


@pytest.mark.asyncio
async def test_git_fetch_mcperror_returns_tool_error() -> None:
    """Converts MCPError from manager into ToolResult.error."""

    manager = Mock()
    tool = GitFetchTool(manager=manager)

    run_sync = AsyncMock(side_effect=PreflightError("No remote"))
    with patch("mcp_server.tools.git_fetch_tool.anyio.to_thread.run_sync", new=run_sync):
        result = await tool.execute(GitFetchInput(remote="origin"))

    assert result.is_error is True
    assert "No remote" in str(result)


@pytest.mark.asyncio
async def test_git_fetch_runtime_error_returns_tool_error() -> None:
    """Converts runtime exception into ToolResult.error with prefix."""

    manager = Mock()
    tool = GitFetchTool(manager=manager)

    run_sync = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("mcp_server.tools.git_fetch_tool.anyio.to_thread.run_sync", new=run_sync):
        result = await tool.execute(GitFetchInput(remote="origin"))

    assert result.is_error is True
    assert "Fetch failed: boom" in str(result)
