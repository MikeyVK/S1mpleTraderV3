"""Unit tests for issue_tools.py."""

from unittest.mock import MagicMock

import pytest

from mcp_server.tools.issue_tools import (
    CloseIssueInput,
    CloseIssueTool,
    CreateIssueInput,
    CreateIssueTool,
    GetIssueInput,
    GetIssueTool,
    IssueBody,
    ListIssuesInput,
    ListIssuesTool,
    UpdateIssueInput,
    UpdateIssueTool,
)


@pytest.fixture
def mock_github_manager() -> MagicMock:
    return MagicMock()


@pytest.mark.asyncio
async def test_create_issue_tool(mock_github_manager: MagicMock) -> None:
    tool = CreateIssueTool(manager=mock_github_manager)
    issue_mock = {"number": 123, "url": "http://github.com/issues/123", "title": "New Issue"}
    mock_github_manager.create_issue.return_value = issue_mock

    params = CreateIssueInput(
        issue_type="feature",
        title="New Issue",
        priority="medium",
        scope="mcp-server",
        body=IssueBody(problem="Some problem description"),
    )
    result = await tool.execute(params)

    mock_github_manager.create_issue.assert_called_once()
    assert "Created issue #123" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_create_issue_tool_forwards_milestone(mock_github_manager: MagicMock) -> None:
    tool = CreateIssueTool(manager=mock_github_manager)
    issue_mock = {"number": 7, "url": "http://github.com/issues/7", "title": "Milestone Issue"}
    mock_github_manager.create_issue.return_value = issue_mock

    params = CreateIssueInput(
        issue_type="feature",
        title="Milestone Issue",
        priority="medium",
        scope="mcp-server",
        body=IssueBody(problem="Needs milestone"),
        milestone="v2.0",
    )
    await tool.execute(params)

    call_kwargs = mock_github_manager.create_issue.call_args.kwargs
    assert call_kwargs["milestone"] == "v2.0"


@pytest.mark.asyncio
async def test_create_issue_tool_milestone_none_when_not_set(
    mock_github_manager: MagicMock,
) -> None:
    tool = CreateIssueTool(manager=mock_github_manager)
    mock_github_manager.create_issue.return_value = {"number": 8, "url": "", "title": "No ms"}

    params = CreateIssueInput(
        issue_type="feature",
        title="No milestone",
        priority="medium",
        scope="mcp-server",
        body=IssueBody(problem="No milestone set"),
    )
    await tool.execute(params)

    call_kwargs = mock_github_manager.create_issue.call_args.kwargs
    assert call_kwargs["milestone"] is None


@pytest.mark.asyncio
async def test_update_issue_tool(mock_github_manager: MagicMock) -> None:
    tool = UpdateIssueTool(manager=mock_github_manager)
    mock_github_manager.update_issue.return_value = MagicMock(number=123)

    params = UpdateIssueInput(issue_number=123, title="Updated Title")
    result = await tool.execute(params)

    mock_github_manager.update_issue.assert_called_with(
        issue_number=123,
        title="Updated Title",
        body=None,
        state=None,
        labels=None,
        assignees=None,
        milestone=None,
    )
    assert "Updated issue #123" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_list_issues_tool(mock_github_manager: MagicMock) -> None:
    tool = ListIssuesTool(manager=mock_github_manager)
    mock_github_manager.list_issues.return_value = [
        MagicMock(number=1, title="Issue 1", state="open", labels=[MagicMock(name="bug")]),
        MagicMock(number=2, title="Issue 2", state="closed", labels=[]),
    ]

    params = ListIssuesInput(state="open", labels=["bug"])
    result = await tool.execute(params)

    # Configure mock labels correctly for assert_called check
    mock_github_manager.list_issues.assert_called_with(state="open", labels=["bug"])
    assert "#1 Issue 1" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_get_issue_tool(mock_github_manager: MagicMock) -> None:
    tool = GetIssueTool(manager=mock_github_manager)

    issue_mock = MagicMock(
        number=1,
        title="Bug",
        body="Fix it",
        state="open",
        html_url="url",
        created_at=MagicMock(isoformat=lambda: "2023-01-01"),
        assignees=[],
        labels=[],
        milestone=None,
    )
    mock_github_manager.get_issue.return_value = issue_mock

    result = await tool.execute(GetIssueInput(issue_number=1))

    mock_github_manager.get_issue.assert_called_with(1)
    assert "#1: Bug" in result.content[0]["text"]
    assert "Fix it" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_close_issue_tool(mock_github_manager: MagicMock) -> None:
    tool = CloseIssueTool(manager=mock_github_manager)
    mock_github_manager.close_issue.return_value = MagicMock(number=5)

    # Test with comment
    await tool.execute(CloseIssueInput(issue_number=5, comment="Done"))

    mock_github_manager.close_issue.assert_called_with(5, comment="Done")
