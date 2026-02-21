"""Unit tests for GitHubAdapter."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from github import GithubException

from mcp_server.adapters.github_adapter import GitHubAdapter
from mcp_server.core.exceptions import ExecutionError, MCPSystemError


@pytest.fixture
def mock_github_client():
    with patch("mcp_server.adapters.github_adapter.Github") as mock:
        yield mock


@pytest.fixture
def mock_settings():
    with patch("mcp_server.adapters.github_adapter.settings") as mock:
        mock.github.token = "test-token"
        mock.github.owner = "test-owner"
        mock.github.repo = "test-repo"
        yield mock


@pytest.fixture
def adapter(mock_github_client, mock_settings):
    """Return an adapter with mocked client and settings."""
    return GitHubAdapter()


def test_init_no_token():
    with patch("mcp_server.adapters.github_adapter.settings") as mock_settings:
        mock_settings.github.token = None
        with pytest.raises(MCPSystemError, match="GitHub token not configured"):
            GitHubAdapter()


def test_repo_property(adapter, mock_github_client):
    mock_repo = MagicMock()
    adapter.client.get_repo.return_value = mock_repo

    assert adapter.repo == mock_repo
    adapter.client.get_repo.assert_called_once_with("test-owner/test-repo")


def test_repo_property_error(adapter):
    adapter.client.get_repo.side_effect = GithubException(404, "Not Found")
    with pytest.raises(MCPSystemError, match="Failed to access repository"):
        _ = adapter.repo


def test_get_issue(adapter):
    mock_issue = MagicMock()
    adapter.client.get_repo.return_value.get_issue.return_value = mock_issue

    assert adapter.get_issue(1) == mock_issue
    adapter.repo.get_issue.assert_called_once_with(1)


def test_get_issue_not_found(adapter):
    adapter.client.get_repo.return_value.get_issue.side_effect = GithubException(404, "Not Found")
    with pytest.raises(ExecutionError, match="Issue #1 not found"):
        adapter.get_issue(1)


def test_create_issue(adapter):
    mock_issue = MagicMock()
    adapter.client.get_repo.return_value.create_issue.return_value = mock_issue

    result = adapter.create_issue("Title", "Body", labels=["bug"], assignees=["user"])

    assert result == mock_issue
    adapter.repo.create_issue.assert_called_once_with(
        title="Title", body="Body", labels=["bug"], assignees=["user"]
    )


def test_update_issue(adapter):
    mock_issue = MagicMock()
    adapter.client.get_repo.return_value.get_issue.return_value = mock_issue

    adapter.update_issue(1, title="New Title", state="closed")

    mock_issue.edit.assert_called_once_with(title="New Title", state="closed")


def test_list_issues(adapter):
    mock_issues = [MagicMock(), MagicMock()]
    adapter.client.get_repo.return_value.get_issues.return_value = mock_issues

    assert adapter.list_issues(state="closed") == mock_issues
    adapter.repo.get_issues.assert_called_once_with(state="closed")


def test_create_pr(adapter):
    mock_pr = MagicMock()
    adapter.client.get_repo.return_value.create_pull.return_value = mock_pr

    result = adapter.create_pr("Title", "Body", "feature", "main", True)

    assert result == mock_pr
    adapter.repo.create_pull.assert_called_once_with(
        title="Title", body="Body", head="feature", base="main", draft=True
    )


def test_create_label(adapter):
    mock_label = MagicMock()
    adapter.client.get_repo.return_value.create_label.return_value = mock_label

    result = adapter.create_label("bug", "ff0000", "desc")
    assert result == mock_label
    adapter.repo.create_label.assert_called_once_with(
        name="bug", color="ff0000", description="desc"
    )


def test_create_label_exists(adapter):
    adapter.client.get_repo.return_value.create_label.side_effect = GithubException(
        422, "Validation Failed"
    )
    with pytest.raises(ExecutionError, match="Label 'bug' already exists"):
        adapter.create_label("bug", "ff0000")


def test_create_milestone(adapter):
    mock_milestone = MagicMock()
    adapter.client.get_repo.return_value.create_milestone.return_value = mock_milestone

    # Test with valid date string
    result = adapter.create_milestone("v1", due_on="2025-12-31T00:00:00Z")
    assert result == mock_milestone
    adapter.repo.create_milestone.assert_called_once()
    call_kwargs = adapter.repo.create_milestone.call_args[1]
    assert call_kwargs["title"] == "v1"
    assert call_kwargs["due_on"] == date(2025, 12, 31)


def test_create_milestone_invalid_date(adapter):
    with pytest.raises(ExecutionError, match="Invalid due_on format"):
        adapter.create_milestone("v1", due_on="invalid-date")


def test_merge_pr_success(adapter):
    mock_pr = MagicMock()
    mock_merge_status = MagicMock()
    mock_merge_status.merged = True
    mock_merge_status.sha = "abc1234"
    mock_merge_status.message = "Merged"

    mock_pr.merge.return_value = mock_merge_status
    adapter.client.get_repo.return_value.get_pull.return_value = mock_pr

    result = adapter.merge_pr(1, "Merge commit", "squash")

    assert result["merged"] is True
    assert result["sha"] == "abc1234"
    mock_pr.merge.assert_called_once_with(commit_message="Merge commit", merge_method="squash")


def test_merge_pr_failed(adapter):
    mock_pr = MagicMock()
    mock_merge_status = MagicMock()
    mock_merge_status.merged = False
    mock_merge_status.message = "Conflict"

    mock_pr.merge.return_value = mock_merge_status
    adapter.client.get_repo.return_value.get_pull.return_value = mock_pr

    with pytest.raises(ExecutionError, match="Merge failed: Conflict"):
        adapter.merge_pr(1)


def test_close_issue(adapter):
    mock_issue = MagicMock()
    adapter.client.get_repo.return_value.get_issue.return_value = mock_issue

    adapter.close_issue(1, comment="Done")

    mock_issue.create_comment.assert_called_once_with("Done")
    mock_issue.edit.assert_called_once_with(state="closed")


def test_list_labels(adapter):
    mock_labels = [MagicMock(), MagicMock()]
    adapter.client.get_repo.return_value.get_labels.return_value = mock_labels

    assert adapter.list_labels() == mock_labels


def test_delete_label(adapter):
    mock_label = MagicMock()
    adapter.client.get_repo.return_value.get_label.return_value = mock_label

    adapter.delete_label("bug")

    adapter.repo.get_label.assert_called_once_with("bug")
    mock_label.delete.assert_called_once()


def test_remove_labels(adapter):
    mock_issue = MagicMock()
    adapter.client.get_repo.return_value.get_issue.return_value = mock_issue

    adapter.remove_labels(1, ["bug", "wontfix"])

    assert mock_issue.remove_from_labels.call_count == 2
    mock_issue.remove_from_labels.assert_any_call("bug")
    mock_issue.remove_from_labels.assert_any_call("wontfix")


def test_list_milestones(adapter):
    mock_milestones = [MagicMock()]
    adapter.client.get_repo.return_value.get_milestones.return_value = mock_milestones

    assert adapter.list_milestones() == mock_milestones
    adapter.repo.get_milestones.assert_called_once_with(state="open")


def test_close_milestone(adapter):
    mock_milestone = MagicMock()
    mock_milestone.title = "v1"
    adapter.client.get_repo.return_value.get_milestone.return_value = mock_milestone

    result = adapter.close_milestone(1)

    assert result == mock_milestone
    mock_milestone.edit.assert_called_once_with(title="v1", state="closed")


def test_list_prs(adapter):
    mock_prs = [MagicMock()]
    adapter.client.get_repo.return_value.get_pulls.return_value = mock_prs

    assert adapter.list_prs(base="main") == mock_prs
    adapter.repo.get_pulls.assert_called_once()
    assert adapter.repo.get_pulls.call_args[1]["base"] == "main"


def test_list_prs_filter_head(adapter):
    mock_prs = [MagicMock()]
    adapter.client.get_repo.return_value.get_pulls.return_value = mock_prs

    assert adapter.list_prs(head="feature") == mock_prs
    adapter.repo.get_pulls.assert_called_once()
    assert adapter.repo.get_pulls.call_args[1]["head"] == "feature"


def test_list_prs_error(adapter):
    adapter.client.get_repo.return_value.get_pulls.side_effect = GithubException(500, "Error")
    with pytest.raises(ExecutionError, match="Failed to list pull requests"):
        adapter.list_prs()


def test_create_issue_with_labels_assignees_milestone(adapter):
    mock_issue = MagicMock()
    mock_milestone = MagicMock()
    adapter.client.get_repo.return_value.create_issue.return_value = mock_issue
    adapter.client.get_repo.return_value.get_milestone.return_value = mock_milestone

    adapter.create_issue("Title", "Body", labels=["L1"], assignees=["U1"], milestone_number=1)

    adapter.repo.create_issue.assert_called_once()
    kwargs = adapter.repo.create_issue.call_args[1]
    assert kwargs["labels"] == ["L1"]
    assert kwargs["assignees"] == ["U1"]
    assert kwargs["milestone"] == mock_milestone


def test_create_issue_milestone_not_found(adapter):
    adapter.client.get_repo.return_value.get_milestone.side_effect = GithubException(
        404, "Not Found"
    )
    with pytest.raises(ExecutionError, match="Milestone 1 not found"):
        adapter.create_issue("Title", "Body", milestone_number=1)


def test_create_issue_error(adapter):
    adapter.client.get_repo.return_value.create_issue.side_effect = GithubException(500, "Error")
    with pytest.raises(ExecutionError, match="Failed to create issue"):
        adapter.create_issue("Title", "Body")


def test_update_issue_all_fields(adapter):
    mock_issue = MagicMock()
    mock_milestone = MagicMock()
    adapter.client.get_repo.return_value.get_issue.return_value = mock_issue
    adapter.client.get_repo.return_value.get_milestone.return_value = mock_milestone

    adapter.update_issue(
        1, title="T", body="B", state="open", labels=["L"], milestone_number=2, assignees=["U"]
    )

    mock_issue.edit.assert_called_once()
    kwargs = mock_issue.edit.call_args[1]
    assert kwargs["title"] == "T"
    assert kwargs["body"] == "B"
    assert kwargs["milestone"] == mock_milestone
    assert kwargs["assignees"] == ["U"]


def test_update_issue_milestone_error(adapter):
    adapter.client.get_repo.return_value.get_issue.return_value = MagicMock()
    adapter.client.get_repo.return_value.get_milestone.side_effect = GithubException(
        404, "Not Found"
    )
    with pytest.raises(ExecutionError, match="Milestone 1 not found"):
        adapter.update_issue(10, milestone_number=1)


def test_update_issue_error(adapter):
    adapter.client.get_repo.return_value.get_issue.side_effect = GithubException(500, "Error")
    with pytest.raises(MCPSystemError, match="GitHub API error"):
        adapter.update_issue(1)


def test_list_issues_with_labels(adapter):
    mock_issues = [MagicMock()]
    adapter.client.get_repo.return_value.get_issues.return_value = mock_issues
    adapter.list_issues(labels=["bug"])
    adapter.repo.get_issues.assert_called_once()
    assert adapter.repo.get_issues.call_args[1]["labels"] == ["bug"]


def test_create_pr_error(adapter):
    adapter.client.get_repo.return_value.create_pull.side_effect = GithubException(500, "Error")
    with pytest.raises(ExecutionError, match="Failed to create PR"):
        adapter.create_pr("T", "B", "H")


def test_add_labels_error(adapter):
    adapter.client.get_repo.return_value.get_issue.side_effect = GithubException(500, "Error")
    with pytest.raises(MCPSystemError, match="GitHub API error"):
        adapter.add_labels(1, ["bug"])


def test_close_issue_error(adapter):
    adapter.client.get_repo.return_value.get_issue.side_effect = GithubException(500, "Error")
    with pytest.raises(MCPSystemError, match="GitHub API error"):
        adapter.close_issue(1)


def test_list_labels_error(adapter):
    adapter.client.get_repo.return_value.get_labels.side_effect = GithubException(500, "Error")
    with pytest.raises(MCPSystemError, match="Failed to list labels"):
        adapter.list_labels()


def test_create_label_error(adapter):
    adapter.client.get_repo.return_value.create_label.side_effect = GithubException(500, "Error")
    with pytest.raises(ExecutionError, match="Failed to create label"):
        adapter.create_label("L", "C")


def test_delete_label_not_found(adapter):
    adapter.client.get_repo.return_value.get_label.side_effect = GithubException(404, "Not Found")
    with pytest.raises(ExecutionError, match="Label 'bug' not found"):
        adapter.delete_label("bug")


def test_delete_label_error(adapter):
    adapter.client.get_repo.return_value.get_label.side_effect = GithubException(500, "Error")
    with pytest.raises(ExecutionError, match="Failed to delete label"):
        adapter.delete_label("bug")


def test_remove_labels_error(adapter):
    adapter.client.get_repo.return_value.get_issue.side_effect = GithubException(500, "Error")
    with pytest.raises(MCPSystemError, match="GitHub API error"):
        adapter.remove_labels(1, ["L"])


def test_remove_labels_ignore_missing(adapter):
    mock_issue = MagicMock()
    mock_issue.remove_from_labels.side_effect = GithubException(404, "Not Found")
    adapter.client.get_repo.return_value.get_issue.return_value = mock_issue

    # Should not raise
    adapter.remove_labels(1, ["missing"])


def test_list_milestones_error(adapter):
    adapter.client.get_repo.return_value.get_milestones.side_effect = GithubException(500, "Error")
    with pytest.raises(ExecutionError, match="Failed to list milestones"):
        adapter.list_milestones()


def test_create_milestone_error(adapter):
    adapter.client.get_repo.return_value.create_milestone.side_effect = GithubException(
        500, "Error"
    )
    with pytest.raises(ExecutionError, match="Failed to create milestone"):
        adapter.create_milestone("T")


def test_close_milestone_not_found(adapter):
    adapter.client.get_repo.return_value.get_milestone.side_effect = GithubException(
        404, "Not Found"
    )
    with pytest.raises(ExecutionError, match="Milestone 1 not found"):
        adapter.close_milestone(1)


def test_close_milestone_error(adapter):
    adapter.client.get_repo.return_value.get_milestone.side_effect = GithubException(500, "Error")
    with pytest.raises(ExecutionError, match="Failed to close milestone"):
        adapter.close_milestone(1)


def test_merge_pr_not_found(adapter):
    adapter.client.get_repo.return_value.get_pull.side_effect = GithubException(404, "Not Found")
    with pytest.raises(ExecutionError, match="Pull request #1 not found"):
        adapter.merge_pr(1)


def test_merge_pr_error(adapter):
    adapter.client.get_repo.return_value.get_pull.side_effect = GithubException(500, "Error")
    with pytest.raises(ExecutionError, match="Failed to merge PR"):
        adapter.merge_pr(1)
