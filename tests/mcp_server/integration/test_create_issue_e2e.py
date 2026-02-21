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

import pytest

from mcp_server.tools.issue_tools import CreateIssueInput, CreateIssueTool, IssueBody

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Scenario 1: Minimal input — issue created, labels correct
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_minimal_input_creates_issue_with_correct_labels() -> None:
    """Create an issue with only required fields; verify label set on GitHub."""
    tool = CreateIssueTool()
    params = make_input()

    result = await tool.execute(params)

    assert not result.is_error, f"Expected success, got error: {result.content}"
    assert "Created issue #" in result.content[0]["text"]

    # Parse the issue number from the result message
    text: str = result.content[0]["text"]
    issue_number = int(text.split("#")[1].split(":")[0].strip())

    # Fetch the created issue and verify labels
    from mcp_server.managers.github_manager import GitHubManager

    manager = GitHubManager()
    issue = manager.get_issue(issue_number)
    label_names = {lbl.name for lbl in issue.labels}

    assert "type:feature" in label_names, f"Missing type:feature in {label_names}"
    assert "scope:tooling" in label_names, f"Missing scope:tooling in {label_names}"
    assert "priority:low" in label_names, f"Missing priority:low in {label_names}"
    # feature workflow first phase = research
    assert "phase:research" in label_names, f"Missing phase:research in {label_names}"


# ---------------------------------------------------------------------------
# Scenario 2: All options — parent, is_epic, all labels applied
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_options_creates_issue_with_full_label_set() -> None:
    """Create an epic issue with parent; verify type:epic + parent:N labels."""
    tool = CreateIssueTool()
    params = make_input(
        title="[e2e smoke] create_issue full-options test",
        issue_type="feature",
        is_epic=True,
        parent_issue=149,
        priority="medium",
        scope="mcp-server",
        body=IssueBody(
            problem="[e2e smoke] Full-options test — safe to close.",
            expected="Issue created with complete label set.",
        ),
    )

    result = await tool.execute(params)

    assert not result.is_error, f"Expected success, got error: {result.content}"

    text: str = result.content[0]["text"]
    issue_number = int(text.split("#")[1].split(":")[0].strip())

    from mcp_server.managers.github_manager import GitHubManager

    manager = GitHubManager()
    issue = manager.get_issue(issue_number)
    label_names = {lbl.name for lbl in issue.labels}

    assert "type:epic" in label_names, f"Missing type:epic in {label_names}"
    assert "parent:149" in label_names, f"Missing parent:149 in {label_names}"
    assert "scope:mcp-server" in label_names, f"Missing scope:mcp-server in {label_names}"
    assert "priority:medium" in label_names, f"Missing priority:medium in {label_names}"
    assert "phase:research" in label_names, f"Missing phase:research in {label_names}"


# ---------------------------------------------------------------------------
# Scenario 3: Invalid input — tool refuses before GitHub API call
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Scenario 4: Milestone validation — permissive when milestones.yaml is empty
# ---------------------------------------------------------------------------


def test_milestone_accepted_when_milestones_yaml_is_empty() -> None:
    """Milestone validation is permissive when milestones.yaml has no entries.

    This is documented in planning.md (Risk #2): milestones.yaml starts empty
    and validation is a no-op until populated.
    """
    # Should NOT raise — empty milestones list means any value is accepted
    params = make_input(milestone="any-future-milestone")
    assert params.milestone == "any-future-milestone"
