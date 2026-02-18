"""Issue management tools."""

import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, Field

from mcp_server.config.template_config import get_template_root
from mcp_server.core.exceptions import ExecutionError
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult

IssueState = Literal["open", "closed", "all"]


def normalize_unicode(text: str) -> str:
    """Normalize Unicode text for safe JSON-RPC transmission.

    Preserves emoji and other Unicode while fixing malformed surrogates.
    """
    # Step 1: Encode to UTF-8 bytes, handling surrogates
    try:
        utf8_bytes = text.encode("utf-8", errors="surrogatepass")
    except UnicodeEncodeError:
        # Fallback: replace bad surrogates
        utf8_bytes = text.encode("utf-8", errors="replace")

    # Step 2: Decode back to string
    normalized = utf8_bytes.decode("utf-8", errors="replace")

    # Step 3: Apply Unicode normalization (NFC = canonical composition)
    return unicodedata.normalize("NFC", normalized)


class IssueBody(BaseModel):
    """Structured body for a GitHub issue, rendered via issue.md.jinja2.

    json_schema_extra examples:
    - Minimal: only `problem` provided — all other fields omitted
    - Full: all optional sections populated for a comprehensive report
    """

    problem: str = Field(..., description="Clear description of the problem or feature request")
    expected: str | None = Field(default=None, description="Expected behavior")
    actual: str | None = Field(default=None, description="Actual behavior observed")
    context: str | None = Field(default=None, description="Relevant background or environment info")
    steps_to_reproduce: str | None = Field(
        default=None, description="Numbered steps to reproduce the issue"
    )
    related_docs: list[str] | None = Field(
        default=None, description="List of related documentation paths or URLs"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "problem": "The create_issue tool does not validate issue_type.",
                },
                {
                    "problem": "Login fails on Windows when username contains spaces.",
                    "expected": "Login succeeds and redirects to dashboard.",
                    "actual": "500 Internal Server Error is returned.",
                    "context": "Observed on Windows 11, Python 3.13.",
                    "steps_to_reproduce": "1. Enter username with space\n2. Click Login",
                    "related_docs": ["docs/development/issue149/research.md"],
                },
            ]
        }
    }


class CreateIssueInput(BaseModel):
    """Input for CreateIssueTool."""

    title: str = Field(..., description="Issue title")
    body: str = Field(..., description="Issue description")
    labels: list[str] | None = Field(default=None, description="List of labels")
    milestone: int | None = Field(default=None, description="Milestone number")
    assignees: list[str] | None = Field(default=None, description="List of usernames")


class CreateIssueTool(BaseTool):
    """Tool to create a new GitHub issue."""

    name = "create_issue"
    description = "Create a new GitHub issue"
    args_model = CreateIssueInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()
        self._renderer = JinjaRenderer(template_dir=get_template_root())

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    def _render_body(self, body: IssueBody) -> str:
        """Render an IssueBody to markdown via issue.md.jinja2."""
        return self._renderer.render(
            "concrete/issue.md.jinja2",
            title="",
            problem=body.problem,
            expected=body.expected,
            actual=body.actual,
            context=body.context,
            steps_to_reproduce=body.steps_to_reproduce,
            related_docs=body.related_docs,
        )

    async def execute(self, params: CreateIssueInput) -> ToolResult:
        try:
            # Normalize Unicode to prevent JSON-RPC encoding errors
            # This preserves emoji while fixing malformed surrogates
            title_safe = normalize_unicode(params.title)
            body_safe = normalize_unicode(params.body)

            issue = self.manager.create_issue(
                title=title_safe,
                body=body_safe,
                labels=params.labels,
                milestone=params.milestone,
                assignees=params.assignees,
            )
            return ToolResult.text(f"Created issue #{issue['number']}: {issue['title']}")
        except ExecutionError as e:
            return ToolResult.error(str(e))


class GetIssueInput(BaseModel):
    """Input for GetIssueTool."""

    issue_number: int = Field(..., description="The issue number to retrieve")


class GetIssueTool(BaseTool):
    """Tool to get issue details."""

    name = "get_issue"
    description = "Get detailed information about a specific GitHub issue"
    args_model = GetIssueInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: GetIssueInput) -> ToolResult:
        try:
            issue = self.manager.get_issue(params.issue_number)

            # Formatting helpers
            assignees_str = ", ".join(a.login for a in issue.assignees) or "none"
            labels_str = ", ".join(label.name for label in issue.labels) or "none"
            milestone_str = issue.milestone.title if issue.milestone else "none"

            return ToolResult.text(
                f"## Issue #{issue.number}: {issue.title}\n\n"
                f"**State:** {issue.state}\n"
                f"**Labels:** {labels_str}\n"
                f"**Assignees:** {assignees_str}\n"
                f"**Milestone:** {milestone_str}\n"
                f"**Created:** {issue.created_at.isoformat()}\n\n"
                f"{issue.body}"
            )
        except ExecutionError as e:
            return ToolResult.error(str(e))


class ListIssuesInput(BaseModel):
    """Input for ListIssuesTool."""

    state: IssueState | None = Field(default=None, description="Filter by issue state")
    labels: list[str] | None = Field(default=None, description="Filter by labels")


class ListIssuesTool(BaseTool):
    """Tool to list issues."""

    name = "list_issues"
    description = "List GitHub issues with optional filtering by state and labels"
    args_model = ListIssuesInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: ListIssuesInput) -> ToolResult:
        try:
            # `IssueState` is a typing.Literal alias, not a runtime type.
            # Pydantic will give us either a string value or None.
            state_str = params.state
            issues = self.manager.list_issues(state=state_str or "open", labels=params.labels)
            if not issues:
                return ToolResult.text("No issues found.")

            summary = "\n".join([f"#{i.number} {i.title} ({i.state})" for i in issues])
            return ToolResult.text(f"Found {len(issues)} issues:\n{summary}")
        except ExecutionError as e:
            return ToolResult.error(str(e))


class UpdateIssueInput(BaseModel):
    """Input for UpdateIssueTool."""

    issue_number: int = Field(..., description="Issue number to update")
    title: str | None = Field(default=None, description="New title")
    body: str | None = Field(default=None, description="Updated description")
    state: IssueState | None = Field(default=None, description="Target state")
    labels: list[str] | None = Field(default=None, description="Replace labels with this list")
    milestone: int | None = Field(default=None, description="Milestone number to assign")
    assignees: list[str] | None = Field(
        default=None, description="Replace assignees with this list"
    )


class UpdateIssueTool(BaseTool):
    """Tool to update an issue."""

    name = "update_issue"
    description = "Update title, body, state, labels, milestone, or assignees for an issue"
    args_model = UpdateIssueInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: UpdateIssueInput) -> ToolResult:
        try:
            self.manager.update_issue(
                issue_number=params.issue_number,
                title=params.title,
                body=params.body,
                state=params.state,
                labels=params.labels,
                milestone=params.milestone,
                assignees=params.assignees,
            )
            return ToolResult.text(f"Updated issue #{params.issue_number}")
        except ExecutionError as e:
            return ToolResult.error(str(e))


class CloseIssueInput(BaseModel):
    """Input for CloseIssueTool."""

    issue_number: int = Field(..., description="The issue number to close")
    comment: str | None = Field(default=None, description="Optional comment to add before closing")


class CloseIssueTool(BaseTool):
    """Tool to close an issue."""

    name = "close_issue"
    description = "Close a GitHub issue with optional comment"
    args_model = CloseIssueInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: CloseIssueInput) -> ToolResult:
        try:
            self.manager.close_issue(params.issue_number, comment=params.comment)
            return ToolResult.text(f"Closed issue #{params.issue_number}")
        except ExecutionError as e:
            return ToolResult.error(str(e))
