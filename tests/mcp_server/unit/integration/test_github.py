"""Tests for GitHub integration."""

import asyncio
from unittest.mock import Mock

import pytest

from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.issue_tools import CreateIssueInput, CreateIssueTool, IssueBody


@pytest.fixture
def mock_adapter() -> Mock:
    """Create a mock GitHub adapter for testing."""
    return Mock()


def test_manager_get_issues(mock_adapter: Mock) -> None:
    """Test GitHubManager returns correctly formatted issue data."""
    # Setup mock
    mock_issue = Mock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.state = "open"
    mock_issue.labels = []
    mock_issue.assignees = []
    mock_issue.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    mock_issue.updated_at.isoformat.return_value = "2023-01-01T00:00:00"

    mock_adapter.list_issues.return_value = [mock_issue]

    manager = GitHubManager(adapter=mock_adapter)
    data = manager.get_issues_resource_data()

    assert data["open_count"] == 1
    assert data["issues"][0]["title"] == "Test Issue"


def test_create_issue_tool(mock_adapter: Mock) -> None:
    """Test CreateIssueTool creates issue and returns correct response."""
    # Setup mock
    mock_issue = Mock()
    mock_issue.number = 42
    mock_issue.html_url = "http://github.com/owner/repo/issues/42"
    mock_issue.title = "New Issue"
    mock_adapter.create_issue.return_value = mock_issue

    manager = GitHubManager(adapter=mock_adapter)
    tool = CreateIssueTool(manager=manager)

    params = CreateIssueInput(
        issue_type="feature",
        title="New Issue",
        priority="medium",
        scope="mcp-server",
        body=IssueBody(problem="Some problem description"),
    )
    result = asyncio.run(tool.execute(params))

    assert "Created issue #42" in result.content[0]["text"]
