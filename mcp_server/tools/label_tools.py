"""GitHub label tools."""
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.base import BaseTool, ToolResult


class ListLabelsInput(BaseModel):
    """Input for ListLabelsTool."""
    # No input fields needed currently, but model required for consistency


class ListLabelsTool(BaseTool):
    """Tool to list all labels in the repository."""

    name = "list_labels"
    description = "List all labels in the repository"
    args_model = ListLabelsInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: ListLabelsInput) -> ToolResult:
        labels = self.manager.list_labels()

        if not labels:
            return ToolResult.text("No labels found in repository.")

        lines = [f"Found {len(labels)} label(s):\n"]
        for label in labels:
            desc = f" - {label.description}" if label.description else ""
            lines.append(f"- **{label.name}** (#{label.color}){desc}")

        return ToolResult.text("\n".join(lines))


class CreateLabelInput(BaseModel):
    """Input for CreateLabelTool."""
    name: str = Field(..., description="Label name (e.g., 'type:feature')")
    color: str = Field(..., description="Color hex code without # (e.g., '0e8a16')")
    description: str | None = Field(default="", description="Label description")


class CreateLabelTool(BaseTool):
    """Tool to create a new label in the repository."""

    name = "create_label"
    description = "Create a new label in the repository"
    args_model = CreateLabelInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: CreateLabelInput) -> ToolResult:
        label = self.manager.create_label(
            name=params.name,
            color=params.color,
            description=params.description or ""
        )
        return ToolResult.text(f"Created label: **{label.name}** (#{params.color})")


class DeleteLabelInput(BaseModel):
    """Input for DeleteLabelTool."""
    name: str = Field(..., description="Label name to delete")


class DeleteLabelTool(BaseTool):
    """Tool to delete a label from the repository."""

    name = "delete_label"
    description = "Delete a label from the repository"
    args_model = DeleteLabelInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: DeleteLabelInput) -> ToolResult:
        self.manager.delete_label(params.name)
        return ToolResult.text(f"Deleted label: **{params.name}**")


class RemoveLabelsInput(BaseModel):
    """Input for RemoveLabelsTool."""
    issue_number: int = Field(..., description="Issue/PR number")
    labels: list[str] = Field(..., description="List of labels to remove")


class RemoveLabelsTool(BaseTool):
    """Tool to remove labels from an issue or PR."""

    name = "remove_labels"
    description = "Remove labels from an issue or PR"
    args_model = RemoveLabelsInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: RemoveLabelsInput) -> ToolResult:
        self.manager.remove_labels(params.issue_number, params.labels)
        return ToolResult.text(
            f"Removed labels from #{params.issue_number}: {', '.join(params.labels)}"
        )


class AddLabelsInput(BaseModel):
    """Input for AddLabelsTool."""
    issue_number: int = Field(..., description="Issue/PR number")
    labels: list[str] = Field(..., description="List of labels to add")


class AddLabelsTool(BaseTool):
    """Tool to add labels to an issue or PR."""

    name = "add_labels"
    description = "Add labels to an issue or PR"
    args_model = AddLabelsInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: AddLabelsInput) -> ToolResult:
        self.manager.add_labels(params.issue_number, params.labels)
        return ToolResult.text(
            f"Added labels to #{params.issue_number}: {', '.join(params.labels)}"
        )
