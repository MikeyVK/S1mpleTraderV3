"""Unit tests for label_tools.py."""

from unittest.mock import MagicMock

import pytest

from mcp_server.config.label_config import LabelConfig
from mcp_server.tools.label_tools import (
    AddLabelsInput,
    AddLabelsTool,
    CreateLabelInput,
    CreateLabelTool,
    DeleteLabelInput,
    DeleteLabelTool,
    ListLabelsInput,
    ListLabelsTool,
    RemoveLabelsInput,
    RemoveLabelsTool,
)


@pytest.fixture
def mock_github_manager():
    return MagicMock()


@pytest.fixture
def test_label_config(tmp_path):
    """Create a temp label config with test labels."""
    yaml_content = """version: "1.0"
labels:
  - name: "bug"
    color: "d73a4a"
  - name: "p1"
    color: "0052cc"
  - name: "new-label"
    color: "0000ff"
"""
    yaml_file = tmp_path / "labels.yaml"
    yaml_file.write_text(yaml_content)

    LabelConfig.reset()
    LabelConfig.load(yaml_file)
    yield
    LabelConfig.reset()


@pytest.mark.asyncio
async def test_list_labels_tool(mock_github_manager):
    tool = ListLabelsTool(manager=mock_github_manager)
    mock_github_manager.list_labels.return_value = [
        MagicMock(name="bug", color="red", description="Its a feature"),
        MagicMock(name="feat", color="green", description=""),
    ]

    result = await tool.execute(ListLabelsInput())

    mock_github_manager.list_labels.assert_called_once()
    assert "bug" in result.content[0]["text"]
    assert "feat" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_create_label_tool(mock_github_manager, test_label_config):
    tool = CreateLabelTool(manager=mock_github_manager)
    label_mock = MagicMock()
    label_mock.name = "type:hotfix"  # Must match pattern, not exist in config
    mock_github_manager.create_label.return_value = label_mock

    params = CreateLabelInput(name="type:hotfix", color="ff0000", description="Hotfix")
    result = await tool.execute(params)

    mock_github_manager.create_label.assert_called_with(
        name="type:hotfix", color="ff0000", description="Hotfix"
    )
    assert "Created label: **type:hotfix**" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_delete_label_tool(mock_github_manager):
    tool = DeleteLabelTool(manager=mock_github_manager)

    params = DeleteLabelInput(name="old-label")
    result = await tool.execute(params)

    mock_github_manager.delete_label.assert_called_with("old-label")
    assert "Deleted label: **old-label**" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_add_labels_tool(mock_github_manager, test_label_config):
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
