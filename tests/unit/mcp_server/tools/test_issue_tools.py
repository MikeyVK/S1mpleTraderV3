"""Tests for GitHub issue tools (List, Get, Close)."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from mcp_server.core.exceptions import ExecutionError
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.issue_tools import (
    CloseIssueTool,
    GetIssueTool,
    ListIssuesTool,
    UpdateIssueTool,
)


@pytest.fixture
def mock_adapter():
    """Create a mock GitHub adapter for testing."""
    return Mock()


class TestListIssuesTool:
    """Tests for ListIssuesTool."""

    def test_tool_name(self, mock_adapter) -> None:
        """Should have correct name."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = ListIssuesTool(manager=manager)
        assert tool.name == "list_issues"

    def test_tool_description(self, mock_adapter) -> None:
        """Should have meaningful description."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = ListIssuesTool(manager=manager)
        assert "issues" in tool.description.lower()
        assert "list" in tool.description.lower()

    def test_tool_schema_has_state(self, mock_adapter) -> None:
        """Should have optional state parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = ListIssuesTool(manager=manager)
        schema = tool.input_schema
        assert "state" in schema["properties"]
        assert "state" not in schema.get("required", [])

    def test_tool_schema_has_labels(self, mock_adapter) -> None:
        """Should have optional labels filter parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = ListIssuesTool(manager=manager)
        schema = tool.input_schema
        assert "labels" in schema["properties"]
        assert "labels" not in schema.get("required", [])

    def test_list_issues_returns_formatted_results(self, mock_adapter) -> None:
        """Should return formatted list of issues."""
        # Setup mock issues
        mock_label1 = Mock()
        mock_label1.name = "bug"

        mock_label2 = Mock()
        mock_label2.name = "feature"

        mock_issue1 = Mock()
        mock_issue1.number = 1
        mock_issue1.title = "First issue"
        mock_issue1.state = "open"
        mock_issue1.labels = [mock_label1]
        mock_issue1.created_at = datetime(2025, 12, 1, tzinfo=timezone.utc)

        mock_issue2 = Mock()
        mock_issue2.number = 2
        mock_issue2.title = "Second issue"
        mock_issue2.state = "open"
        mock_issue2.labels = [mock_label2]
        mock_issue2.created_at = datetime(2025, 12, 2, tzinfo=timezone.utc)

        mock_adapter.list_issues.return_value = [mock_issue1, mock_issue2]

        manager = GitHubManager(adapter=mock_adapter)
        tool = ListIssuesTool(manager=manager)

        result = asyncio.run(tool.execute())

        assert not result.is_error
        assert "#1" in result.content[0]["text"]
        assert "First issue" in result.content[0]["text"]
        assert "#2" in result.content[0]["text"]
        assert "Second issue" in result.content[0]["text"]

    def test_list_issues_with_state_filter(self, mock_adapter) -> None:
        """Should pass state filter to adapter."""
        mock_adapter.list_issues.return_value = []
        manager = GitHubManager(adapter=mock_adapter)
        tool = ListIssuesTool(manager=manager)

        asyncio.run(tool.execute(state="closed"))

        mock_adapter.list_issues.assert_called_with(state="closed", labels=None)

    def test_list_issues_with_labels_filter(self, mock_adapter) -> None:
        """Should pass labels filter to adapter."""
        mock_adapter.list_issues.return_value = []
        manager = GitHubManager(adapter=mock_adapter)
        tool = ListIssuesTool(manager=manager)

        asyncio.run(tool.execute(labels=["bug", "high-priority"]))

        mock_adapter.list_issues.assert_called_with(
            state="open",
            labels=["bug", "high-priority"]
        )

    def test_list_issues_empty_results(self, mock_adapter) -> None:
        """Should handle no issues gracefully."""
        mock_adapter.list_issues.return_value = []
        manager = GitHubManager(adapter=mock_adapter)
        tool = ListIssuesTool(manager=manager)

        result = asyncio.run(tool.execute())

        assert not result.is_error
        assert "no" in result.content[0]["text"].lower()


class TestGetIssueTool:
    """Tests for GetIssueTool."""

    def test_tool_name(self, mock_adapter) -> None:
        """Should have correct name."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = GetIssueTool(manager=manager)
        assert tool.name == "get_issue"

    def test_tool_description(self, mock_adapter) -> None:
        """Should have meaningful description."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = GetIssueTool(manager=manager)
        assert "issue" in tool.description.lower()

    def test_tool_schema_requires_issue_number(self, mock_adapter) -> None:
        """Should require issue_number parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = GetIssueTool(manager=manager)
        schema = tool.input_schema
        assert "issue_number" in schema["properties"]
        assert "issue_number" in schema["required"]

    def test_get_issue_returns_details(self, mock_adapter) -> None:
        """Should return issue details with body and labels."""
        mock_label1 = Mock()
        mock_label1.name = "dto"
        mock_label2 = Mock()
        mock_label2.name = "week-1"

        mock_assignee = Mock()
        mock_assignee.login = "developer"

        mock_milestone = Mock()
        mock_milestone.title = "v1.0"

        mock_issue = Mock()
        mock_issue.number = 42
        mock_issue.title = "Implement DTO validation"
        mock_issue.body = """## Description
Implement validation for DTOs.

## Acceptance Criteria
- [ ] Add validators
- [ ] Write tests
- [x] Create design doc
"""
        mock_issue.state = "open"
        mock_issue.labels = [mock_label1, mock_label2]
        mock_issue.assignees = [mock_assignee]
        mock_issue.milestone = mock_milestone
        mock_issue.created_at = datetime(2025, 12, 1, tzinfo=timezone.utc)
        mock_issue.updated_at = datetime(2025, 12, 5, tzinfo=timezone.utc)

        mock_adapter.get_issue.return_value = mock_issue

        manager = GitHubManager(adapter=mock_adapter)
        tool = GetIssueTool(manager=manager)

        result = asyncio.run(tool.execute(issue_number=42))

        assert not result.is_error
        text = result.content[0]["text"]
        assert "#42" in text
        assert "Implement DTO validation" in text
        assert "Acceptance Criteria" in text
        assert "dto" in text.lower()

    def test_get_issue_extracts_acceptance_criteria(self, mock_adapter) -> None:
        """Should extract acceptance criteria checklist from body."""
        mock_issue = Mock()
        mock_issue.number = 42
        mock_issue.title = "Test"
        mock_issue.body = """
## Acceptance Criteria
- [ ] First criterion
- [x] Second criterion (done)
- [ ] Third criterion
"""
        mock_issue.state = "open"
        mock_issue.labels = []
        mock_issue.assignees = []
        mock_issue.milestone = None
        mock_issue.created_at = datetime(2025, 12, 1, tzinfo=timezone.utc)
        mock_issue.updated_at = datetime(2025, 12, 1, tzinfo=timezone.utc)

        mock_adapter.get_issue.return_value = mock_issue

        manager = GitHubManager(adapter=mock_adapter)
        tool = GetIssueTool(manager=manager)

        result = asyncio.run(tool.execute(issue_number=42))

        text = result.content[0]["text"]
        # Should show acceptance criteria
        assert "First criterion" in text
        assert "Second criterion" in text
        assert "Third criterion" in text

    def test_get_issue_handles_not_found(self, mock_adapter) -> None:
        """Should handle issue not found gracefully."""
        mock_adapter.get_issue.side_effect = ExecutionError("Issue #999 not found")

        manager = GitHubManager(adapter=mock_adapter)
        tool = GetIssueTool(manager=manager)

        result = asyncio.run(tool.execute(issue_number=999))

        assert result.is_error
        assert "not found" in result.content[0]["text"].lower()


class TestCloseIssueTool:
    """Tests for CloseIssueTool."""

    def test_tool_name(self, mock_adapter) -> None:
        """Should have correct name."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = CloseIssueTool(manager=manager)
        assert tool.name == "close_issue"

    def test_tool_description(self, mock_adapter) -> None:
        """Should have meaningful description."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = CloseIssueTool(manager=manager)
        assert "close" in tool.description.lower()
        assert "issue" in tool.description.lower()

    def test_tool_schema_requires_issue_number(self, mock_adapter) -> None:
        """Should require issue_number parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = CloseIssueTool(manager=manager)
        schema = tool.input_schema
        assert "issue_number" in schema["properties"]
        assert "issue_number" in schema["required"]

    def test_tool_schema_has_optional_comment(self, mock_adapter) -> None:
        """Should have optional comment parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = CloseIssueTool(manager=manager)
        schema = tool.input_schema
        assert "comment" in schema["properties"]
        assert "comment" not in schema.get("required", [])

    def test_close_issue_success(self, mock_adapter) -> None:
        """Should close issue and return confirmation."""
        mock_issue = Mock()
        mock_issue.number = 42
        mock_issue.title = "Fixed issue"
        mock_adapter.close_issue.return_value = mock_issue

        manager = GitHubManager(adapter=mock_adapter)
        tool = CloseIssueTool(manager=manager)

        result = asyncio.run(tool.execute(issue_number=42))

        assert not result.is_error
        assert "Closed" in result.content[0]["text"]
        assert "#42" in result.content[0]["text"]
        mock_adapter.close_issue.assert_called_with(42, comment=None)

    def test_close_issue_with_comment(self, mock_adapter) -> None:
        """Should pass comment to adapter when closing."""
        mock_issue = Mock()
        mock_issue.number = 42
        mock_issue.title = "Fixed issue"
        mock_adapter.close_issue.return_value = mock_issue

        manager = GitHubManager(adapter=mock_adapter)
        tool = CloseIssueTool(manager=manager)

        result = asyncio.run(
            tool.execute(issue_number=42, comment="Completed via PR #123")
        )

        assert not result.is_error
        mock_adapter.close_issue.assert_called_with(
            42,
            comment="Completed via PR #123"
        )

    def test_close_issue_handles_not_found(self, mock_adapter) -> None:
        """Should handle issue not found gracefully."""
        mock_adapter.close_issue.side_effect = ExecutionError("Issue #999 not found")

        manager = GitHubManager(adapter=mock_adapter)
        tool = CloseIssueTool(manager=manager)

        result = asyncio.run(tool.execute(issue_number=999))

        assert result.is_error
        assert "not found" in result.content[0]["text"].lower()


class TestUpdateIssueTool:
    """Tests for UpdateIssueTool."""

    def test_tool_schema_requires_issue_number(self, mock_adapter) -> None:
        """Should require issue_number parameter."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = UpdateIssueTool(manager=manager)
        schema = tool.input_schema

        assert "issue_number" in schema["properties"]
        assert "issue_number" in schema["required"]

    def test_update_issue_requires_changes(self, mock_adapter) -> None:
        """Should error when no update fields are provided."""
        manager = GitHubManager(adapter=mock_adapter)
        tool = UpdateIssueTool(manager=manager)

        result = asyncio.run(tool.execute(issue_number=7))

        assert result.is_error
        assert "no updates" in result.content[0]["text"].lower()

    def test_update_issue_applies_changes(self, mock_adapter) -> None:
        """Should call manager with provided fields and return confirmation."""
        mock_issue = Mock()
        mock_issue.number = 7
        mock_issue.title = "Updated"
        mock_adapter.update_issue.return_value = mock_issue

        manager = GitHubManager(adapter=mock_adapter)
        tool = UpdateIssueTool(manager=manager)

        result = asyncio.run(
            tool.execute(
                issue_number=7,
                title="New Title",
                labels=["bug"],
            )
        )

        assert not result.is_error
        assert "Updated issue #7" in result.content[0]["text"]
        mock_adapter.update_issue.assert_called_with(
            issue_number=7,
            title="New Title",
            body=None,
            state=None,
            labels=["bug"],
            milestone_number=None,
            assignees=None,
        )

    def test_update_issue_handles_error(self, mock_adapter) -> None:
        """Should surface execution errors."""
        mock_adapter.update_issue.side_effect = ExecutionError("fail")

        manager = GitHubManager(adapter=mock_adapter)
        tool = UpdateIssueTool(manager=manager)

        result = asyncio.run(tool.execute(issue_number=7, title="New"))

        assert result.is_error
        assert "fail" in result.content[0]["text"].lower()
