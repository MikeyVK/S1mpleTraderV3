"""Git analysis tools for inspecting repository state."""
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.managers.git_manager import GitManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class GitListBranchesInput(BaseModel):
    """Input for GitListBranchesTool."""
    verbose: bool = Field(default=False, description="Include upstream/hash info (-vv)")
    remote: bool = Field(default=False, description="Include remote branches (-r)")


class GitListBranchesTool(BaseTool):
    """Tool to list git branches with optional details."""

    name = "git_list_branches"
    description = "List git branches with optional verbose info and remotes"
    args_model = GitListBranchesInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: GitListBranchesInput) -> ToolResult:
        branches = self.manager.list_branches(verbose=params.verbose, remote=params.remote)
        if not branches:
            return ToolResult.text("No branches found")
        return ToolResult.text("\n".join(branches))


class GitDiffInput(BaseModel):
    """Input for GitDiffTool."""
    target_branch: str = Field(..., description="Target branch to compare against (e.g. main)")
    source_branch: str = Field(default="HEAD", description="Source branch (default: HEAD)")


class GitDiffTool(BaseTool):
    """Tool to get diff statistics between branches."""

    name = "git_diff_stat"
    description = "Get diff statistics between two branches"
    args_model = GitDiffInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: GitDiffInput) -> ToolResult:
        stats = self.manager.compare_branches(params.target_branch, params.source_branch)
        if not stats:
            return ToolResult.text("No differences found")
        return ToolResult.text(stats)
