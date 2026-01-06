"""GitHub milestone tools."""
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.core.exceptions import ExecutionError
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class ListMilestonesInput(BaseModel):
    """Input for ListMilestonesTool."""
    state: str = Field(
        default="open",
        description="Filter milestones by state",
        pattern="^(open|closed|all)$"
    )


class ListMilestonesTool(BaseTool):
    """Tool to list milestones in the repository."""

    name = "list_milestones"
    description = "List milestones with optional state filter"
    args_model = ListMilestonesInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: ListMilestonesInput) -> ToolResult:
        try:
            milestones = self.manager.list_milestones(state=params.state)
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


class CreateMilestoneInput(BaseModel):
    """Input for CreateMilestoneTool."""
    title: str = Field(..., description="Milestone title")
    description: str | None = Field(default=None, description="Optional milestone description")
    due_on: str | None = Field(default=None, description="Optional due date (ISO 8601 string)")


class CreateMilestoneTool(BaseTool):
    """Tool to create a new milestone."""

    name = "create_milestone"
    description = "Create a new milestone in the repository"
    args_model = CreateMilestoneInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: CreateMilestoneInput) -> ToolResult:
        try:
            milestone = self.manager.create_milestone(
                title=params.title,
                description=params.description,
                due_on=params.due_on,
            )
        except ExecutionError as e:
            return ToolResult.error(str(e))

        return ToolResult.text(f"Created milestone #{milestone.number}: {milestone.title}")


class CloseMilestoneInput(BaseModel):
    """Input for CloseMilestoneTool."""
    milestone_number: int = Field(..., description="Milestone number to close")


class CloseMilestoneTool(BaseTool):
    """Tool to close a milestone."""

    name = "close_milestone"
    description = "Close a milestone by number"
    args_model = CloseMilestoneInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: CloseMilestoneInput) -> ToolResult:
        try:
            milestone = self.manager.close_milestone(params.milestone_number)
        except ExecutionError as e:
            return ToolResult.error(str(e))

        return ToolResult.text(
            f"Closed milestone #{milestone.number}: {milestone.title}"
        )
