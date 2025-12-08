"""Git tools."""
from typing import Any, Dict
from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.managers.git_manager import GitManager

class CreateBranchTool(BaseTool):
    """Tool to create a git branch."""

    name = "create_feature_branch"
    description = "Create a new feature branch"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Branch name (kebab-case)"},
                "branch_type": {
                    "type": "string",
                    "enum": ["feature", "fix", "refactor", "docs"],
                    "default": "feature"
                }
            },
            "required": ["name"]
        }

    async def execute(
        self, name: str, branch_type: str = "feature", **kwargs: Any
    ) -> ToolResult:
        branch_name = self.manager.create_feature_branch(name, branch_type)
        return ToolResult.text(f"Created and switched to branch: {branch_name}")

class GitStatusTool(BaseTool):
    """Tool to check git status."""

    name = "git_status"
    description = "Check current git status"

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    async def execute(self, **kwargs: Any) -> ToolResult:
        status = self.manager.get_status()

        text = f"Branch: {status['branch']}\n"
        text += f"Clean: {status['is_clean']}\n"
        if status['untracked_files']:
            text += f"Untracked: {', '.join(status['untracked_files'])}\n"
        if status['modified_files']:
            text += f"Modified: {', '.join(status['modified_files'])}\n"

        return ToolResult.text(text)
