"""GitHub milestone tools."""
from typing import Any

from mcp_server.core.exceptions import ExecutionError
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.base import BaseTool, ToolResult


class ListMilestonesTool(BaseTool):
    """Tool to list milestones in the repository."""

    name = "list_milestones"
    description = "List milestones with optional state filter"

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
                    "description": "Filter milestones by state",
                    "default": "open"
                }
            },
            "required": []
        }

    async def execute(self, state: str = "open", **kwargs: Any) -> ToolResult:
        """Execute the tool."""
        try:
            milestones = self.manager.list_milestones(state=state)
        except ExecutionError as e:
            return ToolResult.error(str(e))

        if not milestones:
            return ToolResult.text("No milestones found matching the criteria.")

        lines = [f"Found {len(milestones)} milestone(s):\n"]
        for milestone in milestones:
            due = f" | Due: {milestone.due_on.isoformat()}" if milestone.due_on else ""
            lines.append(
                f"- #{milestone.number}: {milestone.title}"
                f" | State: {milestone.state}{due}"
            )

        return ToolResult.text("\n".join(lines))


class CreateMilestoneTool(BaseTool):
    """Tool to create a new milestone."""

    name = "create_milestone"
    description = "Create a new milestone in the repository"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Milestone title"},
                "description": {
                    "type": "string",
                    "description": "Optional milestone description"
                },
                "due_on": {
                    "type": "string",
                    "description": "Optional due date (ISO 8601 string)"
                }
            },
            "required": ["title"]
        }

    async def execute(  # type: ignore[override]
        self,
        title: str,
        description: str | None = None,
        due_on: str | None = None,
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool."""
        try:
            milestone = self.manager.create_milestone(
                title=title,
                description=description,
                due_on=due_on,
            )
        except ExecutionError as e:
            return ToolResult.error(str(e))

        return ToolResult.text(f"Created milestone #{milestone.number}: {milestone.title}")


class CloseMilestoneTool(BaseTool):
    """Tool to close a milestone."""

    name = "close_milestone"
    description = "Close a milestone by number"

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "milestone_number": {
                    "type": "integer",
                    "description": "Milestone number to close"
                }
            },
            "required": ["milestone_number"]
        }

    async def execute(  # type: ignore[override]
        self, milestone_number: int, **kwargs: Any
    ) -> ToolResult:
        """Execute the tool."""
        try:
            milestone = self.manager.close_milestone(milestone_number)
        except ExecutionError as e:
            return ToolResult.error(str(e))

        return ToolResult.text(
            f"Closed milestone #{milestone.number}: {milestone.title}"
        )
