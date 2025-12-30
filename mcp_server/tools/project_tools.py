"""Project management tools for MCP server.

Phase 0.5: Project initialization with workflow selection.
Issue #39: Atomic initialization of projects.json + state.json.
"""
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.config.workflows import WorkflowConfig
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectInitOptions, ProjectManager
from mcp_server.tools.base import BaseTool, ToolResult


class InitializeProjectInput(BaseModel):
    """Input for initialize_project tool."""

    issue_number: int = Field(..., description="GitHub issue number")
    issue_title: str = Field(..., description="Issue title")
    workflow_name: str = Field(
        ...,
        description=(
            "Workflow from workflows.yaml: feature (7 phases), bug (6), docs (4), "
            "refactor (5), hotfix (3), or custom"
        )
    )
    custom_phases: tuple[str, ...] | None = Field(
        default=None,
        description="Custom phase list (required if workflow_name=custom)"
    )
    skip_reason: str | None = Field(
        default=None,
        description="Reason for custom phases"
    )


class InitializeProjectTool(BaseTool):
    """Tool for initializing projects with atomic state management.

    Phase 0.5: Human selects workflow_name → generates project phase plan.
    Issue #39 Mode 1: Atomic initialization of projects.json + state.json.
    """

    name = "initialize_project"
    description = (
        "Initialize project with phase plan selection. "
        "Human selects workflow_name (feature/bug/docs/refactor/hotfix/custom) "
        "to generate project-specific phase plan."
    )
    args_model = InitializeProjectInput

    def __init__(self, workspace_root: Path | str):
        """Initialize tool with atomic state management.

        Args:
            workspace_root: Path to workspace root directory
        """
        super().__init__()
        self.workspace_root = Path(workspace_root)
        self.manager = ProjectManager(workspace_root=workspace_root)
        self.git_manager = GitManager()
        self.state_engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=self.manager
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return InitializeProjectInput.model_json_schema()

    async def execute(self, params: InitializeProjectInput) -> ToolResult:
        """Execute project initialization with atomic state creation.

        Issue #39: Creates both projects.json AND state.json atomically.

        Args:
            params: InitializeProjectInput with issue details

        Returns:
            ToolResult with success message and project details

        Raises:
            ValueError: If workflow_name invalid or custom_phases missing
        """
        try:
            # Step 1: Create projects.json (workflow definition)
            options = None
            if params.custom_phases or params.skip_reason:
                options = ProjectInitOptions(
                    custom_phases=params.custom_phases,
                    skip_reason=params.skip_reason
                )

            result = self.manager.initialize_project(
                issue_number=params.issue_number,
                issue_title=params.issue_title,
                workflow_name=params.workflow_name,
                options=options
            )

            # Step 2: Get current branch from git
            branch = self.git_manager.get_current_branch()

            # Step 3: Determine first phase from workflow
            first_phase = result["required_phases"][0]

            # Step 4: Initialize branch state atomically
            self.state_engine.initialize_branch(
                branch=branch,
                issue_number=params.issue_number,
                initial_phase=first_phase
            )

            # Step 5: Build success message
            success_message = {
                "success": True,
                "issue_number": params.issue_number,
                "workflow_name": params.workflow_name,
                "branch": branch,
                "initial_phase": first_phase,
                "required_phases": result["required_phases"],
                "execution_mode": result["execution_mode"],
                "files_created": [
                    ".st3/projects.json (workflow definition)",
                    ".st3/state.json (branch state)"
                ]
            }

            # Add template info if not custom
            if params.workflow_name != "custom":
                workflow_config = WorkflowConfig.load()
                workflow = workflow_config.get_workflow(params.workflow_name)
                success_message["description"] = workflow.description

            return ToolResult.text(json.dumps(success_message, indent=2))

        except (ValueError, OSError, RuntimeError) as e:
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
        return GetProjectPlanInput.model_json_schema()

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
                return ToolResult.text(json.dumps(plan, indent=2))
            return ToolResult.error(f"No project plan found for issue #{params.issue_number}")
        except (ValueError, OSError) as e:
            return ToolResult.error(str(e))
