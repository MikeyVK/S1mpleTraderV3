"""Project management tools for MCP server.

Phase 0.5: Project initialization with workflow selection.
Issue #39: Atomic initialization of projects.json + state.json.
Issue #79: Parent branch tracking with auto-detection.
"""
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.config.workflows import WorkflowConfig
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectInitOptions, ProjectManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult

logger = logging.getLogger(__name__)


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
    parent_branch: str | None = Field(
        default=None,
        description=(
            "Parent branch this feature/bug branches from. "
            "If not provided, attempts auto-detection from git reflog. "
            "Example: 'epic/76-quality-gates-tooling'"
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

    def _detect_parent_branch_from_reflog(self, current_branch: str) -> str | None:
        """Detect parent branch from git reflog.

        Searches reflog for "checkout: moving from <parent> to <current>"

        Args:
            current_branch: Current branch name

        Returns:
            Parent branch name or None if not detectable

        Example:
            >>> _detect_parent_branch_from_reflog("feature/79-test")
            'epic/76-quality-gates-tooling'
        """
        try:
            # Get reflog output
            result = subprocess.run(
                ["git", "reflog", "show", "--all"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )

            # Pattern: "checkout: moving from <parent> to <current>"
            pattern = f"checkout: moving from (.+?) to {re.escape(current_branch)}"

            # Search most recent first
            for line in result.stdout.splitlines():
                match = re.search(pattern, line)
                if match:
                    parent = match.group(1)
                    logger.info("Detected parent branch from reflog: %s", parent)
                    return parent

            logger.warning("No parent branch found in reflog for %s", current_branch)
            return None

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.warning("Git reflog failed: %s", e)
            return None

    async def execute(self, params: InitializeProjectInput) -> ToolResult:
        """Execute project initialization with atomic state creation.

        Issue #39: Creates both projects.json AND state.json atomically.
        Issue #79: Auto-detects parent_branch if not provided.

        Args:
            params: InitializeProjectInput with issue details

        Returns:
            ToolResult with success message and project details

        Raises:
            ValueError: If workflow_name invalid or custom_phases missing
        """
        try:
            # Get current branch once and reuse (avoid duplicate Git calls)
            branch = self.git_manager.get_current_branch()

            # Step 1: Determine parent_branch
            parent_branch = params.parent_branch

            if parent_branch is None:
                # Auto-detect from git reflog
                parent_branch = self._detect_parent_branch_from_reflog(branch)

                if parent_branch:
                    logger.info(
                        "Auto-detected parent_branch: %s for %s",
                        parent_branch, branch
                    )

            # Step 2: Create projects.json (workflow definition)
            options = None
            if params.custom_phases or params.skip_reason or parent_branch:
                options = ProjectInitOptions(
                    custom_phases=params.custom_phases,
                    skip_reason=params.skip_reason,
                    parent_branch=parent_branch
                )

            result = self.manager.initialize_project(
                issue_number=params.issue_number,
                issue_title=params.issue_title,
                workflow_name=params.workflow_name,
                options=options
            )

            # Step 3: Determine first phase from workflow
            first_phase = result["required_phases"][0]

            # Step 5: Initialize branch state atomically
            self.state_engine.initialize_branch(
                branch=branch,
                issue_number=params.issue_number,
                initial_phase=first_phase
            )

            # Step 6: Build success message
            success_message = {
                "success": True,
                "issue_number": params.issue_number,
                "workflow_name": params.workflow_name,
                "branch": branch,
                "initial_phase": first_phase,
                "parent_branch": parent_branch,
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
