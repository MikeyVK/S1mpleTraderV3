"""Tests for PR and Label tools.

@layer: Tests (Unit)
@dependencies: [pytest, pathlib, mcp_server.tools.pr_tools]
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import LabelConfig
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.schemas.tool_outputs import LabelOperationOutput, ListPRsOutput, MergePROutput
from mcp_server.tools.label_tools import AddLabelsInput, AddLabelsTool
from mcp_server.tools.pr_tools import (
    ListPRsInput,
    ListPRsTool,
    MergePRInput,
    MergePRTool,
)
from tests.mcp_server.test_support import get_default_server_root

_PGMCP_CONFIG = Path(__file__).resolve().parents[4] / get_default_server_root() / "config"


@pytest.fixture
def mock_git_config() -> Mock:
    git_config = Mock()
    git_config.default_base_branch = "main"
    return git_config


@pytest.fixture
def mock_adapter() -> Mock:
    """Create a mock GitHub adapter for testing."""
    return Mock()


@pytest.fixture
def test_label_config(tmp_path: Path) -> LabelConfig:
    """Create a temp label config with test labels."""
    yaml_content = """version: "1.0.0"
labels:
  - name: "bug"
    color: "d73a4a"
  - name: "high-priority"
    color: "0052cc"
"""
    yaml_file = tmp_path / "labels.yaml"
    yaml_file.write_text(yaml_content)

    return ConfigLoader(_PGMCP_CONFIG).load_label_config(config_path=yaml_file)


def test_add_labels_tool(mock_adapter: Mock, test_label_config: LabelConfig) -> None:
    """Test AddLabelsTool adds labels and returns confirmation."""
    manager = GitHubManager(adapter=mock_adapter)
    tool = AddLabelsTool(manager=manager, label_config=test_label_config, workphases_config=Mock())

    result = asyncio.run(
        tool.execute(
            AddLabelsInput(issue_number=456, labels=["bug", "high-priority"]), NoteContext()
        )
    )

    assert isinstance(result, LabelOperationOutput)
    assert result.issue_number == 456
    assert result.labels == ["bug", "high-priority"]
    mock_adapter.add_labels.assert_called_with(456, ["bug", "high-priority"])


def test_list_prs_tool(mock_adapter: Mock, mock_git_config: Mock) -> None:
    """Test ListPRsTool lists pull requests."""
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
    mock_pr.html_url = "https://github.com/pulls/5"

    mock_adapter.list_prs.return_value = [mock_pr]

    manager = GitHubManager(adapter=mock_adapter)
    tool = ListPRsTool(manager=manager, git_config=mock_git_config)

    result = asyncio.run(tool.execute(ListPRsInput(), NoteContext()))

    assert isinstance(result, ListPRsOutput)
    assert result.success is True
    assert result.prs_count == 1
    assert result.pull_requests[0].number == 5
    assert result.pull_requests[0].title == "Add feature"
    mock_adapter.list_prs.assert_called_with(state="open", base=None, head=None)


def test_merge_pr_tool(mock_adapter: Mock, mock_git_config: Mock) -> None:
    """Test MergePRTool merges PRs."""
    mock_adapter.merge_pr.return_value = {"merged": True, "sha": "abc123", "message": "Merged"}

    mock_pr = Mock()
    mock_pr.number = 8
    mock_pr.title = "Test PR"
    mock_pr.state = "open"
    mock_pr.base.ref = "main"
    mock_pr.head.ref = "feature/branch"
    mock_pr.merged_at = None
    mock_pr.merge_commit_sha = None
    mock_pr.body = ""
    mock_pr.html_url = "https://github.com/pulls/8"
    mock_adapter.get_pr.return_value = mock_pr

    manager = GitHubManager(adapter=mock_adapter)
    pr_status_writer = MagicMock()
    tool = MergePRTool(
        manager=manager, git_config=mock_git_config, pr_status_writer=pr_status_writer
    )

    result = asyncio.run(
        tool.execute(MergePRInput(pr_number=8, merge_method="merge"), NoteContext())
    )

    assert isinstance(result, MergePROutput)
    assert result.success is True
    assert result.merge_sha == "abc123"
    mock_adapter.merge_pr.assert_called_with(
        pr_number=8,
        commit_message=None,
        merge_method="merge",
    )
