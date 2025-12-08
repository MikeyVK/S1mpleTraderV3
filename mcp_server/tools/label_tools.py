"""GitHub label tools."""
from typing import Any, Dict
from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.managers.github_manager import GitHubManager

class AddLabelsTool(BaseTool):
    """Tool to add labels to an issue or PR."""

    name = "add_labels"
    description = "Add labels to an issue or PR"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "issue_number": {"type": "integer", "description": "Issue/PR number"},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of labels to add"
                }
            },
            "required": ["issue_number", "labels"]
        }

    async def execute(
        self,
        issue_number: int,
        labels: list[str],
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool."""
        self.manager.add_labels(issue_number, labels)
        return ToolResult.text(f"Added labels to #{issue_number}: {', '.join(labels)}")
