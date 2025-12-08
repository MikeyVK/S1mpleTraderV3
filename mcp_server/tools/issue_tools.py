"""GitHub issue tools."""
from typing import Any, Dict, Optional
from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.managers.github_manager import GitHubManager

class CreateIssueTool(BaseTool):
    """Tool to create a GitHub issue."""

    name = "create_issue"
    description = "Create a new GitHub issue"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> Dict[str, Any]:
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

    async def execute(
        self,
        title: str,
        body: str,
        labels: Optional[list[str]] = None,
        milestone: Optional[int] = None,
        assignees: Optional[list[str]] = None,
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool."""
        result = self.manager.create_issue(
            title=title,
            body=body,
            labels=labels,
            milestone=milestone,
            assignees=assignees
        )

        return ToolResult.text(f"Created issue #{result['number']}: {result['url']}")
