"""Tests for milestone tools."""
import asyncio
from unittest.mock import Mock

import pytest

from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.milestone_tools import (
    CloseMilestoneTool,
    CreateMilestoneTool,
    ListMilestonesTool,
)


@pytest.fixture
def mock_adapter():
    """Create a mock GitHub adapter for testing."""
    return Mock()


def test_list_milestones_tool(mock_adapter) -> None:
    """Should list milestones with formatting."""
    mock_due = Mock()
    mock_due.isoformat.return_value = "2025-12-01T00:00:00Z"

    mock_milestone = Mock()
    mock_milestone.number = 3
    mock_milestone.title = "v1.0"
    mock_milestone.state = "open"
    mock_milestone.due_on = mock_due

    mock_adapter.list_milestones.return_value = [mock_milestone]

    manager = GitHubManager(adapter=mock_adapter)
    tool = ListMilestonesTool(manager=manager)

    result = asyncio.run(tool.execute())

    assert not result.is_error
    assert "#3" in result.content[0]["text"]
    assert "v1.0" in result.content[0]["text"]
    assert "Due" in result.content[0]["text"]
    mock_adapter.list_milestones.assert_called_with(state="open")


def test_create_milestone_tool(mock_adapter) -> None:
    """Should create milestone and return confirmation."""
    mock_milestone = Mock()
    mock_milestone.number = 4
    mock_milestone.title = "v2.0"

    mock_adapter.create_milestone.return_value = mock_milestone

    manager = GitHubManager(adapter=mock_adapter)
    tool = CreateMilestoneTool(manager=manager)

    result = asyncio.run(tool.execute(title="v2.0", description="desc"))

    assert not result.is_error
    assert "v2.0" in result.content[0]["text"]
    mock_adapter.create_milestone.assert_called_with(
        title="v2.0",
        description="desc",
        due_on=None,
    )


def test_close_milestone_tool(mock_adapter) -> None:
    """Should close milestone and return confirmation."""
    mock_milestone = Mock()
    mock_milestone.number = 5
    mock_milestone.title = "Backlog"

    mock_adapter.close_milestone.return_value = mock_milestone

    manager = GitHubManager(adapter=mock_adapter)
    tool = CloseMilestoneTool(manager=manager)

    result = asyncio.run(tool.execute(milestone_number=5))

    assert not result.is_error
    assert "#5" in result.content[0]["text"]
    mock_adapter.close_milestone.assert_called_with(5)
