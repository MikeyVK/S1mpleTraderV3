"""Integration-style tests for CreateIssueTool."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mcp_server.managers.github_manager import GitHubManager
from mcp_server.schemas import MilestoneConfig
from mcp_server.tools.issue_tools import CreateIssueInput, CreateIssueTool, IssueBody
from tests.mcp_server.test_support import load_issue_tool_dependencies, make_create_issue_tool

pytestmark = pytest.mark.asyncio

MINIMAL_BODY = IssueBody(problem="[e2e smoke] Integration test - safe to close automatically.")


def make_input(**overrides: object) -> CreateIssueInput:
    defaults: dict[str, object] = {
        "issue_type": "feature",
        "title": "[e2e smoke] create_issue integration test",
        "priority": "low",
        "scope": "tooling",
        "body": MINIMAL_BODY,
    }
    defaults.update(overrides)
    return CreateIssueInput(**defaults)


def make_validating_tool(
    *, milestone_config: MilestoneConfig | None = None
) -> tuple[CreateIssueTool, MagicMock]:
    dependencies = load_issue_tool_dependencies()
    adapter = MagicMock()
    manager = GitHubManager(
        adapter=adapter,
        issue_config=dependencies["issue_config"],
        label_config=dependencies["label_config"],
        scope_config=dependencies["scope_config"],
        milestone_config=milestone_config or dependencies["milestone_config"],
        contributor_config=dependencies["contributor_config"],
        git_config=dependencies["git_config"],
    )
    tool = CreateIssueTool(
        manager=manager,
        issue_config=dependencies["issue_config"],
        milestone_config=milestone_config or dependencies["milestone_config"],
        workflow_config=dependencies["workflow_config"],
    )
    return tool, adapter


async def test_minimal_input_creates_issue_with_correct_labels() -> None:
    mock_manager = MagicMock()
    mock_manager.create_issue.return_value = {
        "number": 42,
        "title": "[e2e smoke] create_issue integration test",
    }

    tool = make_create_issue_tool(mock_manager)
    params = make_input()

    result = await tool.execute(params)

    assert not result.is_error, f"Expected success, got error: {result.content}"
    assert "Created issue #42" in result.content[0]["text"]

    _, call_kwargs = mock_manager.create_issue.call_args
    label_names = set(call_kwargs["labels"])

    assert "type:feature" in label_names
    assert "scope:tooling" in label_names
    assert "priority:low" in label_names
    assert "phase:research" in label_names


async def test_all_options_creates_issue_with_full_label_set() -> None:
    mock_manager = MagicMock()
    mock_manager.create_issue.return_value = {
        "number": 99,
        "title": "[e2e smoke] create_issue full-options test",
    }

    tool = make_create_issue_tool(mock_manager)
    params = make_input(
        title="[e2e smoke] create_issue full-options test",
        issue_type="feature",
        is_epic=True,
        parent_issue=149,
        priority="medium",
        scope="mcp-server",
        body=IssueBody(
            problem="[e2e smoke] Full-options test.",
            expected="Issue created with complete label set.",
        ),
    )

    result = await tool.execute(params)

    assert not result.is_error, f"Expected success, got error: {result.content}"

    _, call_kwargs = mock_manager.create_issue.call_args
    label_names = set(call_kwargs["labels"])

    assert "type:epic" in label_names
    assert "parent:149" in label_names
    assert "scope:mcp-server" in label_names
    assert "priority:medium" in label_names
    assert "phase:research" in label_names


async def test_invalid_issue_type_is_refused_before_api_call() -> None:
    tool, adapter = make_validating_tool()

    result = await tool.execute(make_input(issue_type="invalid_type"))

    assert result.is_error is True
    assert "Unknown issue type" in result.content[0]["text"]
    adapter.create_issue.assert_not_called()


async def test_invalid_scope_is_refused_before_api_call() -> None:
    tool, adapter = make_validating_tool()

    result = await tool.execute(make_input(scope="nonexistent-scope"))

    assert result.is_error is True
    assert "Unknown scope" in result.content[0]["text"]
    adapter.create_issue.assert_not_called()


async def test_invalid_priority_is_refused_before_api_call() -> None:
    tool, adapter = make_validating_tool()

    result = await tool.execute(make_input(priority="ultra-critical"))

    assert result.is_error is True
    assert "Unknown priority" in result.content[0]["text"]
    adapter.create_issue.assert_not_called()


async def test_title_too_long_is_refused_before_api_call() -> None:
    tool, adapter = make_validating_tool()

    result = await tool.execute(make_input(title="X" * 200))

    assert result.is_error is True
    assert "Title too long" in result.content[0]["text"]
    adapter.create_issue.assert_not_called()


async def test_milestone_accepted_when_milestones_yaml_is_empty() -> None:
    dependencies = load_issue_tool_dependencies()
    empty_milestones = MilestoneConfig(version="1.0", milestones=[])
    adapter = MagicMock()
    manager = GitHubManager(
        adapter=adapter,
        issue_config=dependencies["issue_config"],
        label_config=dependencies["label_config"],
        scope_config=dependencies["scope_config"],
        milestone_config=empty_milestones,
        contributor_config=dependencies["contributor_config"],
        git_config=dependencies["git_config"],
    )
    tool = CreateIssueTool(
        manager=manager,
        issue_config=dependencies["issue_config"],
        milestone_config=empty_milestones,
        workflow_config=dependencies["workflow_config"],
    )
    issue_mock = MagicMock(number=11, title="Milestone ok", html_url="http://x")
    adapter.create_issue.return_value = issue_mock

    result = await tool.execute(make_input(milestone="any-future-milestone"))

    assert result.is_error is False
    assert "Created issue #11" in result.content[0]["text"]
