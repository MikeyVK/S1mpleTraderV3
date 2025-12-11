"""Git analysis tools for inspecting repository state."""
from typing import Any

from mcp_server.managers.git_manager import GitManager
from mcp_server.tools.base import BaseTool, ToolResult


class GitListBranchesTool(BaseTool):
    """Tool to list git branches with optional details."""

    name = "git_list_branches"
    description = "List git branches with optional verbose info and remotes"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "verbose": {
                    "type": "boolean",
                    "description": "Include upstream/hash info (-vv)",
                    "default": False
                },
                "remote": {
                    "type": "boolean",
                    "description": "Include remote branches (-r)",
                    "default": False
                }
            },
            "required": []
        }

    async def execute(  # type: ignore[override] # pylint: disable=arguments-differ
        self, verbose: bool = False, remote: bool = False, **kwargs: Any
    ) -> ToolResult:
        branches = self.manager.list_branches(verbose=verbose, remote=remote)
        if not branches:
            return ToolResult.text("No branches found")
        return ToolResult.text("\n".join(branches))


class GitDiffTool(BaseTool):
    """Tool to get diff statistics between branches."""

    name = "git_diff_stat"
    description = "Get diff statistics between two branches"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_branch": {
                    "type": "string",
                    "description": "Target branch to compare against (e.g. main)"
                },
                "source_branch": {
                    "type": "string",
                    "description": "Source branch (default: HEAD)",
                    "default": "HEAD"
                }
            },
            "required": ["target_branch"]
        }

    async def execute(  # type: ignore[override] # pylint: disable=arguments-differ
        self, target_branch: str, source_branch: str = "HEAD", **kwargs: Any
    ) -> ToolResult:
        stats = self.manager.compare_branches(target_branch, source_branch)
        if not stats:
            return ToolResult.text("No differences found")
        return ToolResult.text(stats)
