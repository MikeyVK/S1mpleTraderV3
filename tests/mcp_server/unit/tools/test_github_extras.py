"""Tests for PR and Label tools."""
import asyncio
from unittest.mock import Mock

import pytest

from mcp_server.config.label_config import LabelConfig
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.label_tools import AddLabelsInput, AddLabelsTool
from mcp_server.tools.pr_tools import (
    CreatePRInput,
    CreatePRTool,
    ListPRsInput,
    ListPRsTool,
    MergePRInput,
    MergePRTool,
)


@pytest.fixture
def mock_adapter():
    """Create a mock GitHub adapter for testing."""
    return Mock()

@pytest.fixture
def test_label_config(tmp_path):
    """Create a temp label config with test labels."""
    yaml_content = """version: "1.0"
labels:
  - name: "bug"
    color: "d73a4a"
  - name: "high-priority"
    color: "0052cc"
"""
    yaml_file = tmp_path / "labels.yaml"
    yaml_file.write_text(yaml_content)

    LabelConfig.reset()
    LabelConfig.load(yaml_file)
    yield
    LabelConfig.reset()

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

    result = asyncio.run(tool.execute(CreatePRInput(
        title="New Feature",
        body="Description",
        head="feature/branch"
    )))

    assert "Created PR #123" in result.content[0]["text"]
    mock_adapter.create_pr.assert_called_with(
        title="New Feature",
        body="Description",
        head="feature/branch",
        base="main",
        draft=False
    )

def test_add_labels_tool(mock_adapter, test_label_config) -> None:
    """Test AddLabelsTool adds labels and returns confirmation."""
    manager = GitHubManager(adapter=mock_adapter)
    tool = AddLabelsTool(manager=manager)

    result = asyncio.run(tool.execute(AddLabelsInput(
        issue_number=456,
        labels=["bug", "high-priority"]
    )))

    assert "Added labels to #456" in result.content[0]["text"]
    mock_adapter.add_labels.assert_called_with(456, ["bug", "high-priority"])


def test_list_prs_tool(mock_adapter) -> None:
    """Test ListPRsTool lists pull requests with formatting."""
    mock_base = Mock()
    mock_base.ref = "main"
    mock_head = Mock()
    mock_head.ref = "feature/branch"

    mock_pr = Mock()
    mock_pr.number = 5
    mock_pr.title = "Add feature"
    mock_pr.state = "open"
    mock_pr.base = mock_base
    mock_pr.head = mock_head

    mock_adapter.list_prs.return_value = [mock_pr]

    manager = GitHubManager(adapter=mock_adapter)
    tool = ListPRsTool(manager=manager)

    result = asyncio.run(tool.execute(ListPRsInput()))

    assert not result.is_error
    assert "#5" in result.content[0]["text"]
    assert "feature/branch" in result.content[0]["text"]
    mock_adapter.list_prs.assert_called_with(state="open", base=None, head=None)


def test_merge_pr_tool(mock_adapter) -> None:
    """Test MergePRTool merges PRs and returns confirmation."""
    mock_adapter.merge_pr.return_value = {
        "merged": True,
        "sha": "abc123",
        "message": "Merged"
    }

    manager = GitHubManager(adapter=mock_adapter)
    tool = MergePRTool(manager=manager)

    result = asyncio.run(tool.execute(MergePRInput(pr_number=8, merge_method="squash")))

    assert not result.is_error
    assert "abc123" in result.content[0]["text"]
    mock_adapter.merge_pr.assert_called_with(
        pr_number=8,
        commit_message=None,
        merge_method="squash",
    )
