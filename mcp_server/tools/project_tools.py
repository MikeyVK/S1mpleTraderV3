"""Project management tools for MCP server.

Phase 0.5: Project initialization with workflow selection.
"""
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.managers.project_manager import ProjectManager, ProjectInitOptions
from mcp_server.tools.base import BaseTool, ToolResult


class InitializeProjectInput(BaseModel):
    """Input for initialize_project tool."""

    issue_number: int = Field(..., description="GitHub issue number")
    issue_title: str = Field(..., description="Issue title")
    workflow_name: str = Field(
        ...,
        description=(
            "Workflow name from workflows.yaml: "
            "feature, bug, hotfix, refactor, docs"
        )
    )
    execution_mode: str | None = Field(
        default=None,
        description="Execution mode: 'autonomous' or 'interactive' (overrides workflow default)"
    )
    custom_phases: list[str] | None = Field(
        default=None,
        description="Custom phase list (requires skip_reason)"
    )
    skip_reason: str | None = Field(
        default=None,
        description="Reason for custom phases (required with custom_phases)"
    )


class InitializeProjectTool(BaseTool):
    """Tool for initializing projects with workflow selection.

    Uses workflows.yaml configuration (Issue #50).
    """

    name = "initialize_project"
    description = (
        "Initialize project with workflow from workflows.yaml. "
        "Workflow determines phase sequence and execution mode."
    )
    args_model = InitializeProjectInput

    def __init__(self, workspace_root: Path | str):
        """Initialize tool.

        Args:
            workspace_root: Path to workspace root directory
        """
        super().__init__()
        self.manager = ProjectManager(workspace_root=workspace_root)

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: InitializeProjectInput) -> ToolResult:
        """Execute project initialization.

        Args:
            params: InitializeProjectInput with issue details

        Returns:
            ToolResult with success message and project details

        Raises:
            ValueError: If workflow_name invalid or validation fails
        """
        try:
            # Build options
            options = None
            if params.execution_mode or params.custom_phases or params.skip_reason:
                options = ProjectInitOptions(
                    execution_mode=params.execution_mode,
                    custom_phases=tuple(params.custom_phases) if params.custom_phases else None,
                    skip_reason=params.skip_reason
                )

            # Initialize project with new API
            plan = self.manager.initialize_project(
                issue_number=params.issue_number,
                issue_title=params.issue_title,
                workflow_name=params.workflow_name,
                options=options
            )

            # Format response
            response = {
                "success": True,
                "issue_number": plan.issue_number,  # pylint: disable=no-member
                "issue_title": plan.issue_title,  # pylint: disable=no-member
                "workflow_name": plan.workflow_name,  # pylint: disable=no-member
                "required_phases": list(plan.required_phases),  # pylint: disable=no-member
                "skip_reason": plan.skip_reason,  # pylint: disable=no-member
                "description": f"{len(plan.required_phases)}-phase workflow"  # pylint: disable=no-member
            }

            return ToolResult.text(json.dumps(response, indent=2))
        except (ValueError, OSError) as e:
            return ToolResult.error(str(e))


class GetProjectPlanInput(BaseModel):
    """Input for get_project_plan tool."""

    issue_number: int = Field(..., description="GitHub issue number")


class GetProjectPlanTool(BaseTool):
    """Tool for retrieving project plan."""

    name = "get_project_plan"
    description = "Get project phase plan for issue number"
    args_model = GetProjectPlanInput

    def __init__(self, workspace_root: Path | str):
        """Initialize tool.

        Args:
            workspace_root: Path to workspace root directory
        """
        super().__init__()
        self.manager = ProjectManager(workspace_root=workspace_root)

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: GetProjectPlanInput) -> ToolResult:
        """Execute project plan retrieval.

        Args:
            params: GetProjectPlanInput with issue_number

        Returns:
            ToolResult with project plan or error
        """
        try:
            plan = self.manager.get_project_plan(issue_number=params.issue_number)
            if plan:
                # plan is already a dict from project_manager
                return ToolResult.text(json.dumps(plan, indent=2))
            return ToolResult.error(f"No project plan found for issue #{params.issue_number}")
        except (ValueError, OSError) as e:
            return ToolResult.error(str(e))
