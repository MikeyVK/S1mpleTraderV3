"""Issue management tools."""
from typing import Any, Literal

from pydantic import BaseModel, Field

from mcp_server.core.exceptions import ExecutionError
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult

IssueState = Literal["open", "closed", "all"]


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

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: CreateIssueInput) -> ToolResult:
        try:
            issue = self.manager.create_issue(
                title=params.title,
                body=params.body,
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
            labels_str = ", ".join(l.name for l in issue.labels) or "none"
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
            issues = self.manager.list_issues(
                state=state_str or "open",
                labels=params.labels
            )
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
    labels: list[str] | None = Field(
        default=None,
        description="Replace labels with this list"
    )
    milestone: int | None = Field(default=None, description="Milestone number to assign")
    assignees: list[str] | None = Field(
        default=None,
        description="Replace assignees with this list"
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
