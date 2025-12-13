"""Unit tests for label_tools.py."""
import pytest
from unittest.mock import MagicMock, patch
from mcp_server.tools.label_tools import (
    ListLabelsTool, ListLabelsInput,
    CreateLabelTool, CreateLabelInput,
    DeleteLabelTool, DeleteLabelInput,
    AddLabelsTool, AddLabelsInput,
    RemoveLabelsTool, RemoveLabelsInput
)
from mcp_server.tools.base import ToolResult

@pytest.fixture
def mock_github_manager():
    return MagicMock()

@pytest.mark.asyncio
async def test_list_labels_tool(mock_github_manager):
    tool = ListLabelsTool(manager=mock_github_manager)
    mock_github_manager.list_labels.return_value = [
        MagicMock(name="bug", color="red", description="Its a feature"),
        MagicMock(name="feat", color="green", description="")
    ]
    
    result = await tool.execute(ListLabelsInput())
    
    mock_github_manager.list_labels.assert_called_once()
    assert "bug" in result.content[0]["text"]
    assert "feat" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_create_label_tool(mock_github_manager):
    tool = CreateLabelTool(manager=mock_github_manager)
    label_mock = MagicMock()
    label_mock.name = "new-label"  # Set attribute explicitly
    mock_github_manager.create_label.return_value = label_mock
    
    params = CreateLabelInput(name="new-label", color="blue", description="New")
    result = await tool.execute(params)
    
    mock_github_manager.create_label.assert_called_with(
        name="new-label", color="blue", description="New"
    )
    assert "Created label: **new-label**" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_delete_label_tool(mock_github_manager):
    tool = DeleteLabelTool(manager=mock_github_manager)
    
    params = DeleteLabelInput(name="old-label")
    result = await tool.execute(params)
    
    mock_github_manager.delete_label.assert_called_with("old-label")
    assert "Deleted label: **old-label**" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_add_labels_tool(mock_github_manager):
    tool = AddLabelsTool(manager=mock_github_manager)
    
    result = await tool.execute(AddLabelsInput(issue_number=10, labels=["bug", "p1"]))
    
    mock_github_manager.add_labels.assert_called_with(10, ["bug", "p1"])
    assert "Added labels to #10" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_remove_labels_tool(mock_github_manager):
    tool = RemoveLabelsTool(manager=mock_github_manager)
    
    result = await tool.execute(RemoveLabelsInput(issue_number=10, labels=["bug"]))
    
    mock_github_manager.remove_labels.assert_called_with(10, ["bug"])
    assert "Removed labels from #10" in result.content[0]["text"]
