"""Unit tests for milestone_tools.py."""

from unittest.mock import MagicMock

import pytest

from mcp_server.tools.milestone_tools import (
    CloseMilestoneInput,
    CloseMilestoneTool,
    CreateMilestoneInput,
    CreateMilestoneTool,
    ListMilestonesInput,
    ListMilestonesTool,
)


@pytest.fixture
def mock_github_manager():
    return MagicMock()


@pytest.mark.asyncio
async def test_list_milestones_tool(mock_github_manager):
    tool = ListMilestonesTool(manager=mock_github_manager)
    m1 = MagicMock(number=1, title="M1", state="open")
    m1.due_on = MagicMock(isoformat=lambda: "2023-01-01")

    mock_github_manager.list_milestones.return_value = [m1]

    result = await tool.execute(ListMilestonesInput())

    mock_github_manager.list_milestones.assert_called_with(state="open")
    assert "#1: M1" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_create_milestone_tool(mock_github_manager):
    tool = CreateMilestoneTool(manager=mock_github_manager)
    mock_github_manager.create_milestone.return_value = MagicMock(number=2)

    params = CreateMilestoneInput(title="Sprint 1")
    result = await tool.execute(params)

    mock_github_manager.create_milestone.assert_called_with(
        title="Sprint 1", description=None, due_on=None
    )
    assert "Created milestone #2" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_close_milestone_tool(mock_github_manager):
    tool = CloseMilestoneTool(manager=mock_github_manager)
    mock_github_manager.close_milestone.return_value = MagicMock(number=3, title="Sprint X")

    params = CloseMilestoneInput(milestone_number=3)
    result = await tool.execute(params)

    mock_github_manager.close_milestone.assert_called_with(3)
    assert "Closed milestone #3" in result.content[0]["text"]
