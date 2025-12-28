"""GitHub label tools."""
import re
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.config.label_config import LabelConfig
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
        # Load label config for validation
        label_config = LabelConfig.load()
        
        # Validate label name pattern
        is_valid, error_msg = label_config.validate_label_name(params.name)
        if not is_valid:
            return ToolResult.text(f"❌ {error_msg}")
        
        # Validate color format (no # prefix)
        if params.color.startswith("#"):
            return ToolResult.text(
                f"❌ Color must not include # prefix. "
                f"Use '{params.color[1:]}' instead."
            )
        
        # Validate hex format
        if not re.match(r'^[0-9A-Fa-f]{6}$', params.color):
            return ToolResult.text(
                f"❌ Invalid color format '{params.color}'. "
                f"Must be 6-character hex code (e.g., '1D76DB')."
            )
        
        # Create label
        label = await self.manager.create_label(
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
        # Load label config for validation
        label_config = LabelConfig.load()
        
        # Validate all labels exist
        undefined = [label for label in params.labels if not label_config.label_exists(label)]
        if undefined:
            return ToolResult.text(
                f"❌ Labels not defined in labels.yaml: {undefined}"
            )
        
        # Add labels
        await self.manager.add_labels(params.issue_number, params.labels)
        return ToolResult.text(
            f"Added labels to #{params.issue_number}: {', '.join(params.labels)}"
        )

class SyncLabelsInput(BaseModel):
    """Input for SyncLabelsToGitHubTool."""
    dry_run: bool = Field(default=True, description="Preview changes without applying")


class SyncLabelsToGitHubTool(BaseTool):
    """Tool to sync labels from labels.yaml to GitHub."""

    name = "sync_labels_to_github"
    description = "Sync label definitions from labels.yaml to GitHub"
    args_model = SyncLabelsInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: SyncLabelsInput) -> ToolResult:
        """Execute label sync."""
        label_config = LabelConfig.load()
        
        # Create a simple adapter that uses the manager
        class GitHubAdapter:
            def __init__(self, manager):
                self.manager = manager
            
            def list_labels(self):
                labels = self.manager.list_labels()
                return [
                    {
                        "name": label.name,
                        "color": label.color,
                        "description": label.description or ""
                    }
                    for label in labels
                ]
            
            def create_label(self, name: str, color: str, description: str):
                self.manager.create_label(name=name, color=color, description=description)
            
            def update_label(self, name: str, color: str, description: str):
                self.manager.update_label(name=name, color=color, description=description)
        
        adapter = GitHubAdapter(self.manager)
        result = label_config.sync_to_github(adapter, dry_run=params.dry_run)
        
        summary = (
            f"Created {len(result['created'])}, "
            f"Updated {len(result['updated'])}, "
            f"Skipped {len(result['skipped'])}"
        )
        
        if result['errors']:
            summary += f", Errors {len(result['errors'])}"
        
        details = []
        if result['created']:
            details.append(f"Created: {', '.join(result['created'])}")
        if result['updated']:
            details.append(f"Updated: {', '.join(result['updated'])}")
        if result['skipped']:
            details.append(f"Skipped: {', '.join(result['skipped'])}")
        if result['errors']:
            details.append(f"Errors: {', '.join(result['errors'])}")
        
        mode_str = "dry_run: True" if params.dry_run else "dry_run: False"
        full_text = f"{summary}\n{mode_str}"
        if details:
            full_text += f"\n\n" + "\n".join(details)
        
        return ToolResult.text(full_text)
