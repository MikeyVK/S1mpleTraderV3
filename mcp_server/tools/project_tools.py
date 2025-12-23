"""Project management tools for MCP server.

Phase 0.5: Project initialization with issue type selection.
"""
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.managers.project_manager import ProjectManager, PHASE_TEMPLATES


class InitializeProjectInput(BaseModel):
    """Input for initialize_project tool."""

    issue_number: int = Field(..., description="GitHub issue number")
    issue_title: str = Field(..., description="Issue title")
    issue_type: str = Field(
        ...,
        description=(
            "Type of work: feature (7 phases), bug (6), docs (4), "
            "refactor (5), hotfix (3), or custom"
        )
    )
    custom_phases: tuple[str, ...] | None = Field(
        default=None,
        description="Custom phase list (required if issue_type=custom)"
    )
    skip_reason: str | None = Field(
        default=None,
        description="Reason for custom phases"
    )


class InitializeProjectTool:
    """Tool for initializing projects with phase plan selection.

    Phase 0.5: Human selects issue_type → generates project phase plan.
    """

    name = "initialize_project"
    description = (
        "Initialize project with phase plan selection. "
        "Human selects issue_type (feature/bug/docs/refactor/hotfix/custom) "
        "to generate project-specific phase plan."
    )
    args_model = InitializeProjectInput

    def __init__(self, workspace_root: Path | str):
        """Initialize tool.

        Args:
            workspace_root: Path to workspace root directory
        """
        self.manager = ProjectManager(workspace_root=workspace_root)

    def execute(self, params: InitializeProjectInput) -> dict[str, Any]:
        """Execute project initialization.

        Args:
            params: InitializeProjectInput with issue details

        Returns:
            Result dict with success, issue_type, required_phases

        Raises:
            ValueError: If issue_type invalid or custom_phases missing
        """
        result = self.manager.initialize_project(
            issue_number=params.issue_number,
            issue_title=params.issue_title,
            issue_type=params.issue_type,
            custom_phases=params.custom_phases,
            skip_reason=params.skip_reason
        )

        # Add template info to result
        if params.issue_type != "custom":
            template = PHASE_TEMPLATES[params.issue_type]
            result["description"] = template["description"]

        return result


class GetProjectPlanTool:
    """Tool for retrieving project plan."""

    name = "get_project_plan"
    description = "Get project phase plan for issue number"

    def __init__(self, workspace_root: Path | str):
        """Initialize tool.

        Args:
            workspace_root: Path to workspace root directory
        """
        self.manager = ProjectManager(workspace_root=workspace_root)

    def execute(self, issue_number: int) -> dict[str, Any] | None:
        """Execute project plan retrieval.

        Args:
            issue_number: GitHub issue number

        Returns:
            Project plan dict or None if not found
        """
        return self.manager.get_project_plan(issue_number=issue_number)
