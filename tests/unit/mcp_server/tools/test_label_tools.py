"""Tests for GitHub label tools (Create, List, Delete, Remove)."""
# pylint: disable=protected-access  # Testing internal methods is valid
import asyncio
from unittest.mock import Mock

import pytest

from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.label_tools import (
    AddLabelsTool,
    CreateLabelTool,
    DeleteLabelTool,
    ListLabelsTool,
    RemoveLabelsTool,
)


@pytest.fixture
def mock_adapter():
    """Create a mock GitHub adapter for testing."""
    return Mock()


class TestListLabelsTool:
    """Tests for ListLabelsTool."""

    def test_tool_name(self, mock_adapter) -> None:
        """Should have correct name."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = ListLabelsTool(manager=manager)
        assert tool.name == "list_labels"

    def test_tool_description(self, mock_adapter) -> None:
        """Should have meaningful description."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = ListLabelsTool(manager=manager)
        assert "label" in tool.description.lower()

    def test_tool_schema_empty(self, mock_adapter) -> None:
        """Should have no required parameters."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = ListLabelsTool(manager=manager)
        schema = tool.input_schema
        assert schema.get("required", []) == []

    def test_list_labels_returns_formatted_results(self, mock_adapter) -> None:
        """Should return formatted list of labels."""
        # Setup mock labels
        mock_label1 = Mock()
        mock_label1.name = "type:feature"
        mock_label1.color = "0e8a16"
        mock_label1.description = "New feature"

        mock_label2 = Mock()
        mock_label2.name = "priority:high"
        mock_label2.color = "d93f0b"
        mock_label2.description = "Important"

        mock_adapter.list_labels.return_value = [mock_label1, mock_label2]

        manager = GitHubManager(adapter=mock_adapter)
        tool = ListLabelsTool(manager=manager)

        result = asyncio.run(tool.execute())

        assert "type:feature" in result.content[0]["text"]
        assert "priority:high" in result.content[0]["text"]

    def test_list_labels_empty_results(self, mock_adapter) -> None:
        """Should handle empty label list."""
        mock_adapter.list_labels.return_value = []

        manager = GitHubManager(adapter=mock_adapter)
        tool = ListLabelsTool(manager=manager)

        result = asyncio.run(tool.execute())

        assert "No labels" in result.content[0]["text"]


class TestCreateLabelTool:
    """Tests for CreateLabelTool."""

    def test_tool_name(self, mock_adapter) -> None:
        """Should have correct name."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = CreateLabelTool(manager=manager)
        assert tool.name == "create_label"

    def test_tool_description(self, mock_adapter) -> None:
        """Should have meaningful description."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = CreateLabelTool(manager=manager)
        assert "label" in tool.description.lower()
        assert "create" in tool.description.lower()

    def test_tool_schema_requires_name(self, mock_adapter) -> None:
        """Should require name parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = CreateLabelTool(manager=manager)
        schema = tool.input_schema
        assert "name" in schema["properties"]
        assert "name" in schema["required"]

    def test_tool_schema_requires_color(self, mock_adapter) -> None:
        """Should require color parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = CreateLabelTool(manager=manager)
        schema = tool.input_schema
        assert "color" in schema["properties"]
        assert "color" in schema["required"]

    def test_tool_schema_has_description(self, mock_adapter) -> None:
        """Should have optional description parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = CreateLabelTool(manager=manager)
        schema = tool.input_schema
        assert "description" in schema["properties"]

    def test_create_label_success(self, mock_adapter) -> None:
        """Should create label and return success."""
        mock_label = Mock()
        mock_label.name = "type:feature"
        mock_adapter.create_label.return_value = mock_label

        manager = GitHubManager(adapter=mock_adapter)
        tool = CreateLabelTool(manager=manager)

        result = asyncio.run(tool.execute(
            name="type:feature",
            color="0e8a16",
            description="New feature"
        ))

        assert "type:feature" in result.content[0]["text"]
        assert "created" in result.content[0]["text"].lower()
        mock_adapter.create_label.assert_called_once_with(
            name="type:feature",
            color="0e8a16",
            description="New feature"
        )


class TestDeleteLabelTool:
    """Tests for DeleteLabelTool."""

    def test_tool_name(self, mock_adapter) -> None:
        """Should have correct name."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = DeleteLabelTool(manager=manager)
        assert tool.name == "delete_label"

    def test_tool_description(self, mock_adapter) -> None:
        """Should have meaningful description."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = DeleteLabelTool(manager=manager)
        assert "label" in tool.description.lower()
        assert "delete" in tool.description.lower()

    def test_tool_schema_requires_name(self, mock_adapter) -> None:
        """Should require name parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = DeleteLabelTool(manager=manager)
        schema = tool.input_schema
        assert "name" in schema["properties"]
        assert "name" in schema["required"]

    def test_delete_label_success(self, mock_adapter) -> None:
        """Should delete label and return success."""
        mock_adapter.delete_label.return_value = None

        manager = GitHubManager(adapter=mock_adapter)
        tool = DeleteLabelTool(manager=manager)

        result = asyncio.run(tool.execute(name="old-label"))

        assert "old-label" in result.content[0]["text"]
        assert "deleted" in result.content[0]["text"].lower()
        mock_adapter.delete_label.assert_called_once_with("old-label")


class TestRemoveLabelsTool:
    """Tests for RemoveLabelsTool."""

    def test_tool_name(self, mock_adapter) -> None:
        """Should have correct name."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = RemoveLabelsTool(manager=manager)
        assert tool.name == "remove_labels"

    def test_tool_description(self, mock_adapter) -> None:
        """Should have meaningful description."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = RemoveLabelsTool(manager=manager)
        assert "label" in tool.description.lower()
        assert "remove" in tool.description.lower()

    def test_tool_schema_requires_issue_number(self, mock_adapter) -> None:
        """Should require issue_number parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = RemoveLabelsTool(manager=manager)
        schema = tool.input_schema
        assert "issue_number" in schema["properties"]
        assert "issue_number" in schema["required"]

    def test_tool_schema_requires_labels(self, mock_adapter) -> None:
        """Should require labels parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = RemoveLabelsTool(manager=manager)
        schema = tool.input_schema
        assert "labels" in schema["properties"]
        assert "labels" in schema["required"]

    def test_remove_labels_success(self, mock_adapter) -> None:
        """Should remove labels and return success."""
        mock_adapter.remove_labels.return_value = None

        manager = GitHubManager(adapter=mock_adapter)
        tool = RemoveLabelsTool(manager=manager)

        result = asyncio.run(tool.execute(
            issue_number=5,
            labels=["bug", "wontfix"]
        ))

        assert "#5" in result.content[0]["text"]
        assert "removed" in result.content[0]["text"].lower()
        mock_adapter.remove_labels.assert_called_once_with(5, ["bug", "wontfix"])


class TestAddLabelsTool:
    """Tests for existing AddLabelsTool (ensure coverage)."""

    def test_tool_name(self, mock_adapter) -> None:
        """Should have correct name."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = AddLabelsTool(manager=manager)
        assert tool.name == "add_labels"

    def test_tool_description(self, mock_adapter) -> None:
        """Should have meaningful description."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = AddLabelsTool(manager=manager)
        assert "label" in tool.description.lower()
