"""GitHub label tools."""
import re
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.config.label_config import LabelConfig
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


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

    async def execute(self, _params: ListLabelsInput) -> ToolResult:
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
        # Load label config for validation
        label_config = LabelConfig.load()

        # Validate all labels exist
        undefined = [label for label in params.labels if not label_config.label_exists(label)]
        if undefined:
            return ToolResult.text(
                f"❌ Labels not defined in labels.yaml: {undefined}"
            )

        # Add labels
        self.manager.add_labels(params.issue_number, params.labels)
        return ToolResult.text(
            f"Added labels to #{params.issue_number}: {', '.join(params.labels)}"
        )

class DetectLabelDriftInput(BaseModel):
    """Input for DetectLabelDriftTool."""
    # No input fields needed - read-only detection


class DetectLabelDriftTool(BaseTool):
    """Tool to detect drift between labels.yaml and GitHub labels (read-only)."""

    name = "detect_label_drift"
    description = "Detect differences between labels.yaml and GitHub repository labels"
    args_model = DetectLabelDriftInput

    def __init__(self, manager: GitHubManager | None = None) -> None:
        self.manager = manager or GitHubManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, _params: DetectLabelDriftInput) -> ToolResult:
        """Detect label drift between YAML and GitHub."""
        try:
            label_config = LabelConfig.load()
            github_labels = self.manager.list_labels()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return ToolResult.text(f"❌ Error loading labels: {e}")

        # Build lookup dicts
        yaml_by_name = {label.name: label for label in label_config.labels}
        github_by_name = {label.name: label for label in github_labels}

        # Detect drift
        github_only = [name for name in github_by_name if name not in yaml_by_name]
        yaml_only = [name for name in yaml_by_name if name not in github_by_name]

        color_mismatch = []
        desc_mismatch = []

        for name in set(yaml_by_name.keys()) & set(github_by_name.keys()):
            yaml_label = yaml_by_name[name]
            github_label = github_by_name[name]

            if yaml_label.color.lower() != github_label.color.lower():
                color_mismatch.append({
                    "name": name,
                    "yaml_color": yaml_label.color,
                    "github_color": github_label.color
                })

            yaml_desc = yaml_label.description or ""
            github_desc = github_label.description or ""
            if yaml_desc != github_desc:
                desc_mismatch.append({
                    "name": name,
                    "yaml_desc": yaml_desc,
                    "github_desc": github_desc
                })

        # Build report
        if not any([github_only, yaml_only, color_mismatch, desc_mismatch]):
            return ToolResult.text("✅ No drift detected - labels.yaml and GitHub are aligned")

        lines = ["⚠️ Label drift detected:\n"]

        if github_only:
            lines.append(f"**GitHub-only labels ({len(github_only)}):**")
            for label in github_only[:10]:  # Limit to 10
                lines.append(f"  - {label}")
            if len(github_only) > 10:
                lines.append(f"  ... and {len(github_only) - 10} more")
            lines.append("  💡 Recommendation: Add to labels.yaml or remove from GitHub\n")

        if yaml_only:
            lines.append(f"**YAML-only labels ({len(yaml_only)}):**")
            for label in yaml_only[:10]:
                lines.append(f"  - {label}")
            if len(yaml_only) > 10:
                lines.append(f"  ... and {len(yaml_only) - 10} more")
            lines.append("  💡 Recommendation: Create in GitHub or remove from YAML\n")

        if color_mismatch:
            lines.append(f"**Color mismatches ({len(color_mismatch)}):**")
            for item in color_mismatch[:5]:
                lines.append(
                    f"  - {item['name']}: YAML=#{item['yaml_color']}, "
                    f"GitHub=#{item['github_color']}"
                )
            if len(color_mismatch) > 5:
                lines.append(f"  ... and {len(color_mismatch) - 5} more")
            lines.append("  💡 Recommendation: Update manually to align\n")

        if desc_mismatch:
            lines.append(f"**Description mismatches ({len(desc_mismatch)}):**")
            for item in desc_mismatch[:5]:
                lines.append(f"  - {item['name']}")
            if len(desc_mismatch) > 5:
                lines.append(f"  ... and {len(desc_mismatch) - 5} more")
            lines.append("  💡 Recommendation: Update manually to align")

        return ToolResult.text("\n".join(lines))
