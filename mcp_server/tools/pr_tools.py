"""GitHub PR tools."""
from typing import Any

from mcp_server.core.exceptions import ExecutionError
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.base import BaseTool, ToolResult


class CreatePRTool(BaseTool):
    """Tool to create a GitHub Pull Request."""

    name = "create_pr"
    description = "Create a new GitHub Pull Request"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "PR title"},
                "body": {"type": "string", "description": "PR description"},
                "head": {"type": "string", "description": "Source branch"},
                "base": {
                    "type": "string",
                    "description": "Target branch",
                    "default": "main"
                },
                "draft": {
                    "type": "boolean",
                    "description": "Create as draft",
                    "default": False
                }
            },
            "required": ["title", "body", "head"]
        }

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    async def execute(  # type: ignore[override]
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False,
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool."""
        result = self.manager.create_pr(
            title=title,
            body=body,
            head=head,
            base=base,
            draft=draft
        )

        return ToolResult.text(f"Created PR #{result['number']}: {result['url']}")


class ListPRsTool(BaseTool):
    """Tool to list pull requests."""

    name = "list_prs"
    description = "List pull requests with optional state/base/head filters"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Filter by PR state",
                    "default": "open"
                },
                "base": {
                    "type": "string",
                    "description": "Filter by base branch"
                },
                "head": {
                    "type": "string",
                    "description": "Filter by head branch"
                },
            },
            "required": []
        }

    async def execute(
        self,
        state: str = "open",
        base: str | None = None,
        head: str | None = None,
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool."""
        try:
            prs = self.manager.list_prs(state=state, base=base, head=head)
        except ExecutionError as e:
            return ToolResult.error(str(e))

        if not prs:
            return ToolResult.text("No pull requests found matching the criteria.")

        lines = [f"Found {len(prs)} pull request(s):\n"]
        for pr in prs:
            lines.append(
                f"- #{pr.number}: {pr.title}\n"
                f"  State: {pr.state} | Base: {pr.base.ref} | Head: {pr.head.ref}\n"
            )

        return ToolResult.text("\n".join(lines))


class MergePRTool(BaseTool):
    """Tool to merge a pull request."""

    name = "merge_pr"
    description = "Merge a pull request with optional commit message and method"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pr_number": {
                    "type": "integer",
                    "description": "Pull request number to merge"
                },
                "commit_message": {
                    "type": "string",
                    "description": "Optional commit message for the merge"
                },
                "merge_method": {
                    "type": "string",
                    "enum": ["merge", "squash", "rebase"],
                    "description": "Merge strategy",
                    "default": "merge"
                }
            },
            "required": ["pr_number"]
        }

    async def execute(  # type: ignore[override]
        self,
        pr_number: int,
        commit_message: str | None = None,
        merge_method: str = "merge",
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool."""
        try:
            result = self.manager.merge_pr(
                pr_number=pr_number,
                commit_message=commit_message,
                merge_method=merge_method,
            )
        except ExecutionError as e:
            return ToolResult.error(str(e))

        return ToolResult.text(
            f"Merged PR #{pr_number} using {merge_method} (SHA {result['sha']})"
        )
