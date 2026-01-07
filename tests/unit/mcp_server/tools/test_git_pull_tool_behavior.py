"""Behavior tests for GitPullTool.

Also covers input schema helpers for 100% module coverage.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_server.core.exceptions import PreflightError
from mcp_server.tools.git_pull_tool import GitPullInput, GitPullTool, _input_schema


def test_git_pull_input_schema_helper_handles_none() -> None:
    """_input_schema(None) returns an empty schema."""

    assert _input_schema(None) == {}


def test_git_pull_input_schema_helper_returns_model_schema() -> None:
    """_input_schema(model) returns a JSON schema dict."""

    schema = _input_schema(GitPullInput)
    assert isinstance(schema, dict)
    assert "properties" in schema


def test_git_pull_tool_input_schema_property() -> None:
    """Tool.input_schema delegates to _input_schema(args_model)."""

    tool = GitPullTool(manager=Mock())
    schema = tool.input_schema
    assert isinstance(schema, dict)
    assert "properties" in schema


@pytest.mark.asyncio
async def test_git_pull_success_syncs_phase_state() -> None:
    """Pull success triggers a PhaseStateEngine.get_state sync via run_sync."""

    manager = Mock()
    manager.get_current_branch.return_value = "feature/94-missing-git-tools"
    tool = GitPullTool(manager=manager)

    mock_engine = Mock()
    mock_engine.get_state.return_value = {"current_phase": "tdd"}

    run_sync = AsyncMock(side_effect=["Pulled from origin", {"current_phase": "tdd"}])

    with (
        patch("mcp_server.tools.git_pull_tool.Path.cwd", return_value=Path(".")),
        patch("mcp_server.tools.git_pull_tool.project_manager.ProjectManager"),
        patch(
            "mcp_server.tools.git_pull_tool.phase_state_engine.PhaseStateEngine",
            return_value=mock_engine,
        ),
        patch("mcp_server.tools.git_pull_tool.anyio.to_thread.run_sync", new=run_sync),
    ):
        result = await tool.execute(GitPullInput(remote="origin", rebase=False))

    assert result.is_error is False
    assert "Pulled" in str(result)
    assert run_sync.await_count == 2

    second_call = run_sync.await_args_list[1]
    assert second_call.args == (mock_engine.get_state, "feature/94-missing-git-tools")


@pytest.mark.asyncio
async def test_git_pull_phase_sync_failure_is_non_fatal() -> None:
    """Phase sync failure still returns the pull result."""

    manager = Mock()
    manager.get_current_branch.return_value = "feature/94-missing-git-tools"
    tool = GitPullTool(manager=manager)

    mock_engine = Mock()
    mock_engine.get_state.side_effect = ValueError("sync failed")

    run_sync = AsyncMock(side_effect=["Pulled from origin", ValueError("sync failed")])

    with (
        patch("mcp_server.tools.git_pull_tool.Path.cwd", return_value=Path(".")),
        patch("mcp_server.tools.git_pull_tool.project_manager.ProjectManager"),
        patch(
            "mcp_server.tools.git_pull_tool.phase_state_engine.PhaseStateEngine",
            return_value=mock_engine,
        ),
        patch("mcp_server.tools.git_pull_tool.anyio.to_thread.run_sync", new=run_sync),
    ):
        result = await tool.execute(GitPullInput(remote="origin", rebase=False))

    assert result.is_error is False
    assert "Pulled" in str(result)
    assert run_sync.await_count == 2


@pytest.mark.asyncio
async def test_git_pull_mcperror_returns_tool_error() -> None:
    """Converts MCPError from manager into ToolResult.error."""

    manager = Mock()
    tool = GitPullTool(manager=manager)

    run_sync = AsyncMock(side_effect=PreflightError("dirty"))
    with patch("mcp_server.tools.git_pull_tool.anyio.to_thread.run_sync", new=run_sync):
        result = await tool.execute(GitPullInput(remote="origin", rebase=False))

    assert result.is_error is True
    assert "dirty" in str(result)


@pytest.mark.asyncio
async def test_git_pull_runtime_error_returns_tool_error() -> None:
    """Converts runtime exception into ToolResult.error with prefix."""

    manager = Mock()
    tool = GitPullTool(manager=manager)

    run_sync = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("mcp_server.tools.git_pull_tool.anyio.to_thread.run_sync", new=run_sync):
        result = await tool.execute(GitPullInput(remote="origin", rebase=False))

    assert result.is_error is True
    assert "Pull failed: boom" in str(result)
