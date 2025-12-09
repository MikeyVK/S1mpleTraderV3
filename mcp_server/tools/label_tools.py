"""GitHub label tools."""
from typing import Any

from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.base import BaseTool, ToolResult


class ListLabelsTool(BaseTool):
    """Tool to list all labels in the repository."""

    name = "list_labels"
    description = "List all labels in the repository"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool."""
        labels = self.manager.list_labels()

        if not labels:
            return ToolResult.text("No labels found in repository.")

        lines = [f"Found {len(labels)} label(s):\n"]
        for label in labels:
            desc = f" - {label.description}" if label.description else ""
            lines.append(f"- **{label.name}** (#{label.color}){desc}")

        return ToolResult.text("\n".join(lines))


class CreateLabelTool(BaseTool):
    """Tool to create a new label in the repository."""

    name = "create_label"
    description = "Create a new label in the repository"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Label name (e.g., 'type:feature')"
                },
                "color": {
                    "type": "string",
                    "description": "Color hex code without # (e.g., '0e8a16')"
                },
                "description": {
                    "type": "string",
                    "description": "Label description"
                }
            },
            "required": ["name", "color"]
        }

    async def execute(
        self,
        name: str,
        color: str,
        description: str = "",
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool."""
        label = self.manager.create_label(
            name=name,
            color=color,
            description=description
        )
        return ToolResult.text(f"Created label: **{label.name}** (#{color})")


class DeleteLabelTool(BaseTool):
    """Tool to delete a label from the repository."""

    name = "delete_label"
    description = "Delete a label from the repository"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Label name to delete"
                }
            },
            "required": ["name"]
        }

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """Execute the tool."""
        self.manager.delete_label(name)
        return ToolResult.text(f"Deleted label: **{name}**")


class RemoveLabelsTool(BaseTool):
    """Tool to remove labels from an issue or PR."""

    name = "remove_labels"
    description = "Remove labels from an issue or PR"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "issue_number": {
                    "type": "integer",
                    "description": "Issue/PR number"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of labels to remove"
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
        self.manager.remove_labels(issue_number, labels)
        return ToolResult.text(
            f"Removed labels from #{issue_number}: {', '.join(labels)}"
        )


class AddLabelsTool(BaseTool):
    """Tool to add labels to an issue or PR."""

    name = "add_labels"
    description = "Add labels to an issue or PR"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
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
