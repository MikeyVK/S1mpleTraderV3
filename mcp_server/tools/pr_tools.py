"""GitHub PR tools."""
from typing import Any, Dict
from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.managers.github_manager import GitHubManager


class CreatePRTool(BaseTool):
    """Tool to create a GitHub Pull Request."""

    name = "create_pr"
    description = "Create a new GitHub Pull Request"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> Dict[str, Any]:
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
    async def execute(
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
