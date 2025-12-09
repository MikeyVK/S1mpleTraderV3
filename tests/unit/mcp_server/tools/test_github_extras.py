"""Tests for PR and Label tools."""
import asyncio
from unittest.mock import Mock

import pytest

from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.label_tools import AddLabelsTool
from mcp_server.tools.pr_tools import CreatePRTool


@pytest.fixture
def mock_adapter():
    """Create a mock GitHub adapter for testing."""
    return Mock()

def test_create_pr_tool(mock_adapter) -> None:
    """Test CreatePRTool creates PR and returns correct response."""
    # Setup mock
    mock_pr = Mock()
    mock_pr.number = 123
    mock_pr.html_url = "http://github.com/owner/repo/pull/123"
    mock_pr.title = "New Feature"
    mock_adapter.create_pr.return_value = mock_pr

    manager = GitHubManager(adapter=mock_adapter)
    tool = CreatePRTool(manager=manager)

    result = asyncio.run(tool.execute(
        title="New Feature",
        body="Description",
        head="feature/branch"
    ))

    assert "Created PR #123" in result.content[0]["text"]
    mock_adapter.create_pr.assert_called_with(
        title="New Feature",
        body="Description",
        head="feature/branch",
        base="main",
        draft=False
    )

def test_add_labels_tool(mock_adapter) -> None:
    """Test AddLabelsTool adds labels and returns confirmation."""
    manager = GitHubManager(adapter=mock_adapter)
    tool = AddLabelsTool(manager=manager)

    result = asyncio.run(tool.execute(
        issue_number=456,
        labels=["bug", "high-priority"]
    ))

    assert "Added labels to #456" in result.content[0]["text"]
    mock_adapter.add_labels.assert_called_with(456, ["bug", "high-priority"])
