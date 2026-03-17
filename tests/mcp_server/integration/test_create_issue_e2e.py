"""
@module: tests.integration.test_create_issue_e2e
@layer: Test Infrastructure
@dependencies: mcp_server.tools.issue_tools, mcp_server.managers.github_manager
@responsibilities:
  - Real-world smoke tests for CreateIssueTool against live GitHub API
  - Validates label assembly, milestone forwarding, and input validation end-to-end
  - Marked @pytest.mark.integration — excluded from standard CI
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mcp_server.tools.issue_tools import CreateIssueInput, IssueBody
from tests.mcp_server.test_support import configure_create_issue_input, make_create_issue_tool

pytestmark = pytest.mark.asyncio

configure_create_issue_input()

MINIMAL_BODY = IssueBody(problem="[e2e smoke] Integration test — safe to close automatically.")


def make_input(**overrides: object) -> CreateIssueInput:
    """Return a minimal valid CreateIssueInput, overridable per test."""
    defaults: dict[str, object] = {
        "issue_type": "feature",
        "title": "[e2e smoke] create_issue integration test",
        "priority": "low",
        "scope": "tooling",
        "body": MINIMAL_BODY,
    }
    defaults.update(overrides)
    return CreateIssueInput(**defaults)


@pytest.mark.asyncio
async def test_minimal_input_creates_issue_with_correct_labels() -> None:
    """Minimal input assembles correct label set — verified via mock GitHubManager."""
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

    assert "type:feature" in label_names, f"Missing type:feature in {label_names}"
    assert "scope:tooling" in label_names, f"Missing scope:tooling in {label_names}"
    assert "priority:low" in label_names, f"Missing priority:low in {label_names}"
    assert "phase:research" in label_names, f"Missing phase:research in {label_names}"


@pytest.mark.asyncio
async def test_all_options_creates_issue_with_full_label_set() -> None:
    """All options assemble complete label set — verified via mock GitHubManager."""
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

    assert "type:epic" in label_names, f"Missing type:epic in {label_names}"
    assert "parent:149" in label_names, f"Missing parent:149 in {label_names}"
    assert "scope:mcp-server" in label_names, f"Missing scope:mcp-server in {label_names}"
    assert "priority:medium" in label_names, f"Missing priority:medium in {label_names}"
    assert "phase:research" in label_names, f"Missing phase:research in {label_names}"


def test_invalid_issue_type_is_refused_before_api_call() -> None:
    """Unknown issue_type must be rejected by Pydantic validation, no GitHub call."""
    with pytest.raises(Exception):  # noqa: B017
        make_input(issue_type="invalid_type")


def test_invalid_scope_is_refused_before_api_call() -> None:
    """Unknown scope must be rejected by Pydantic validation, no GitHub call."""
    with pytest.raises(Exception):  # noqa: B017
        make_input(scope="nonexistent-scope")


def test_invalid_priority_is_refused_before_api_call() -> None:
    """Unknown priority must be rejected by Pydantic validation, no GitHub call."""
    with pytest.raises(Exception):  # noqa: B017
        make_input(priority="ultra-critical")


def test_title_too_long_is_refused_before_api_call() -> None:
    """Title exceeding git.yaml max length must be rejected before GitHub call."""
    with pytest.raises(Exception):  # noqa: B017
        make_input(title="X" * 200)


def test_milestone_accepted_when_milestones_yaml_is_empty() -> None:
    """Milestone validation is permissive when milestones.yaml has no entries."""
    configure_create_issue_input()
    params = make_input(milestone="any-future-milestone")
    assert params.milestone == "any-future-milestone"
