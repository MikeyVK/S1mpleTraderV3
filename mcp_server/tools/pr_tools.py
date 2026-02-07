"""GitHub PR tools."""
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.config.git_config import GitConfig
from mcp_server.core.exceptions import ExecutionError
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


def _get_default_base_branch() -> str:
    """Factory for default base branch from GitConfig (Convention #9-11)."""
    git_config = GitConfig.from_file()
    return git_config.default_base_branch


class CreatePRInput(BaseModel):
    """Input for CreatePRTool."""
    title: str = Field(..., description="PR title")
    body: str = Field(..., description="PR description")
    head: str = Field(..., description="Source branch")
    base: str = Field(
        default_factory=_get_default_base_branch,
        description="Target branch"
    )
    draft: bool = Field(default=False, description="Create as draft")


class CreatePRTool(BaseTool):
    """Tool to create a GitHub Pull Request."""

    name = "create_pr"
    description = "Create a new GitHub Pull Request"
    args_model = CreatePRInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: CreatePRInput) -> ToolResult:
        result = self.manager.create_pr(
            title=params.title,
            body=params.body,
            head=params.head,
            base=params.base,
            draft=params.draft
        )

        return ToolResult.text(f"Created PR #{result['number']}: {result['url']}")


class ListPRsInput(BaseModel):
    """Input for ListPRsTool."""
    state: str = Field(
        default="open",
        description="Filter by PR state",
        pattern="^(open|closed|all)$"
    )
    base: str | None = Field(default=None, description="Filter by base branch")
    head: str | None = Field(default=None, description="Filter by head branch")


class ListPRsTool(BaseTool):
    """Tool to list pull requests."""

    name = "list_prs"
    description = "List pull requests with optional state/base/head filters"
    args_model = ListPRsInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: ListPRsInput) -> ToolResult:
        try:
            prs = self.manager.list_prs(state=params.state, base=params.base, head=params.head)
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


class MergePRInput(BaseModel):
    """Input for MergePRTool."""
    pr_number: int = Field(..., description="Pull request number to merge")
    commit_message: str | None = Field(
        default=None,
        description="Optional commit message for the merge"
    )
    merge_method: str = Field(
        default="merge",
        description="Merge strategy",
        pattern="^(merge|squash|rebase)$"
    )


class MergePRTool(BaseTool):
    """Tool to merge a pull request."""

    name = "merge_pr"
    description = "Merge a pull request with optional commit message and method"
    args_model = MergePRInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return super().input_schema

    async def execute(self, params: MergePRInput) -> ToolResult:
        try:
            result = self.manager.merge_pr(
                pr_number=params.pr_number,
                commit_message=params.commit_message,
                merge_method=params.merge_method,
            )
        except ExecutionError as e:
            return ToolResult.error(str(e))

        return ToolResult.text(
            f"Merged PR #{params.pr_number} using {params.merge_method} (SHA {result['sha']})"
        )
