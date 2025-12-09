"""GitHub issue tools."""
import re
from typing import Any

from mcp_server.core.exceptions import ExecutionError, MCPSystemError
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.base import BaseTool, ToolResult


def _get_manager(manager: GitHubManager | None) -> GitHubManager:
    """Get or create GitHubManager, raising clear error if not configured."""
    if manager is not None:
        return manager
    try:
        return GitHubManager()
    except MCPSystemError as e:
        raise ExecutionError(
            "GitHub integration not configured. Set GITHUB_TOKEN environment variable.",
            recovery=["Set GITHUB_TOKEN environment variable", "Restart the MCP server"]
        ) from e


class CreateIssueTool(BaseTool):
    """Tool to create a GitHub issue."""

    name = "create_issue"
    description = "Create a new GitHub issue"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self._manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Issue title"},
                "body": {"type": "string", "description": "Issue description"},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of labels"
                },
                "milestone": {"type": "integer", "description": "Milestone number"},
                "assignees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of usernames"
                }
            },
            "required": ["title", "body"]
        }

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    async def execute(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
        milestone: int | None = None,
        assignees: list[str] | None = None,
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool to create a GitHub issue."""
        try:
            manager = _get_manager(self._manager)
            result = manager.create_issue(
                title=title,
                body=body,
                labels=labels,
                milestone=milestone,
                assignees=assignees
            )
            return ToolResult.text(f"Created issue #{result['number']}: {result['url']}")
        except ExecutionError as e:
            return ToolResult.error(str(e))


class ListIssuesTool(BaseTool):
    """Tool to list GitHub issues."""

    name = "list_issues"
    description = "List GitHub issues with optional filtering by state and labels"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        """Initialize with optional manager for testing."""
        self._manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        """Define input schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Filter by issue state",
                    "default": "open"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by labels"
                }
            },
            "required": []
        }

    async def execute(
        self,
        state: str = "open",
        labels: list[str] | None = None,
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool to list GitHub issues."""
        try:
            manager = _get_manager(self._manager)
            issues = manager.list_issues(state=state, labels=labels)

            if not issues:
                return ToolResult.text("No issues found matching the criteria.")

            lines = [f"Found {len(issues)} issue(s):\n"]

            for issue in issues:
                label_str = ", ".join(label.name for label in issue.labels) or "none"
                lines.append(
                    f"- #{issue.number}: {issue.title}\n"
                    f"  State: {issue.state} | Labels: {label_str}\n"
                )

            return ToolResult.text("\n".join(lines))
        except ExecutionError as e:
            return ToolResult.error(str(e))


class GetIssueTool(BaseTool):
    """Tool to get details of a specific GitHub issue."""

    name = "get_issue"
    description = "Get detailed information about a specific GitHub issue"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        """Initialize with optional manager for testing."""
        self._manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        """Define input schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number to retrieve"
                }
            },
            "required": ["issue_number"]
        }

    async def execute(
        self,
        issue_number: int,
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool to get issue details."""
        try:
            manager = _get_manager(self._manager)
            issue = manager.get_issue(issue_number)
        except ExecutionError as e:
            return ToolResult.error(str(e))

        # Extract labels
        label_str = ", ".join(label.name for label in issue.labels) or "none"

        # Extract assignees
        assignee_str = ", ".join(a.login for a in issue.assignees) or "none"

        # Extract milestone
        milestone_str = issue.milestone.title if issue.milestone else "none"

        # Extract acceptance criteria from body
        criteria = self._extract_checklist(issue.body or "")
        criteria_str = "\n".join(f"  - {c}" for c in criteria) if criteria else "  none"

        text = f"""## Issue #{issue.number}: {issue.title}

**State:** {issue.state}
**Labels:** {label_str}
**Assignees:** {assignee_str}
**Milestone:** {milestone_str}
**Created:** {issue.created_at.isoformat()}
**Updated:** {issue.updated_at.isoformat()}

### Description
{issue.body or 'No description provided.'}

### Acceptance Criteria
{criteria_str}
"""

        return ToolResult.text(text)

    def _extract_checklist(self, body: str) -> list[str]:
        """Extract checklist items from issue body."""
        if not body:
            return []

        pattern = r"- \[[ x]\] (.+)"
        matches = re.findall(pattern, body)
        return matches[:20]  # Limit to 20 items


class CloseIssueTool(BaseTool):
    """Tool to close a GitHub issue."""

    name = "close_issue"
    description = "Close a GitHub issue with optional comment"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        """Initialize with optional manager for testing."""
        self._manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        """Define input schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "issue_number": {
                    "type": "integer",
                    "description": "The issue number to close"
                },
                "comment": {
                    "type": "string",
                    "description": "Optional comment to add before closing"
                }
            },
            "required": ["issue_number"]
        }

    async def execute(
        self,
        issue_number: int,
        comment: str | None = None,
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool to close a GitHub issue."""
        try:
            manager = _get_manager(self._manager)
            issue = manager.close_issue(issue_number, comment=comment)
        except ExecutionError as e:
            return ToolResult.error(str(e))

        return ToolResult.text(f"Closed issue #{issue.number}: {issue.title}")
