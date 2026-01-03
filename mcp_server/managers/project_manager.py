# mcp_server/managers/project_manager.py
"""
Project manager - Workflow-based project initialization.

Manages project initialization with workflow selection from workflows.yaml.
Replaces hardcoded PHASE_TEMPLATES with dynamic workflow configuration.

@layer: Platform
@dependencies: [workflow_config]
@responsibilities:
    - Initialize projects with workflow selection
    - Validate workflow existence and execution mode
    - Support custom phase overrides with skip_reason
    - Persist project plans to .st3/projects.json
    - Retrieve stored project plans
"""

# Standard library
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Project modules
from mcp_server.config.workflows import workflow_config


@dataclass
class ProjectInitOptions:
    """Optional parameters for project initialization.

    Reduces initialize_project() from 7 to 4 parameters.
    Field order: overrides → customizations → metadata
    """

    # Overrides
    execution_mode: str | None = None

    # Customizations
    custom_phases: tuple[str, ...] | None = None
    skip_reason: str | None = None

    # Branch metadata
    parent_branch: str | None = None


@dataclass
class ProjectPlan:
    """Project phase plan data structure.

    Field order: identifier → core data → optional → metadata
    """

    # Identifiers
    issue_number: int
    issue_title: str

    # Core workflow data
    workflow_name: str
    execution_mode: str
    required_phases: tuple[str, ...]

    # Optional fields
    skip_reason: str | None = None
    parent_branch: str | None = None
    created_at: str | None = None


class ProjectManager:
    """Project initialization manager with workflow support.

    Uses workflows.yaml for workflow definitions and phase sequences.
    """

    def __init__(self, workspace_root: Path | str):
        """Initialize ProjectManager.

        Args:
            workspace_root: Path to workspace root directory
        """
        self.workspace_root = Path(workspace_root)
        self.projects_file = self.workspace_root / ".st3" / "projects.json"

    def initialize_project(
        self,
        issue_number: int,
        issue_title: str,
        workflow_name: str,
        parent_branch: str | None = None,
        options: ProjectInitOptions | None = None
    ) -> dict[str, Any]:
        """Initialize project with workflow selection.

        Args:
            issue_number: GitHub issue number
            issue_title: Issue title
            workflow_name: Workflow from workflows.yaml (feature, bug, hotfix, etc.)
            parent_branch: Optional parent branch this feature/bug branches from
            options: Optional parameters (execution_mode, custom_phases, skip_reason)

        Returns:
            dict with success, workflow_name, execution_mode, required_phases, skip_reason

        Raises:
            ValueError: If workflow invalid or custom_phases without skip_reason
        """
        opts = options or ProjectInitOptions()

        # Use explicit parent_branch parameter, fallback to options
        if parent_branch is None and opts.parent_branch is not None:
            parent_branch = opts.parent_branch

        # Validate workflow exists
        try:
            workflow = workflow_config.get_workflow(workflow_name)
        except ValueError as e:
            # Re-raise with workflow_config error (includes available workflows)
            raise ValueError(str(e)) from e

        # Determine execution mode (override or workflow default)
        exec_mode = opts.execution_mode or workflow.default_execution_mode

        # Validate execution mode
        if exec_mode not in ("interactive", "autonomous"):
            msg = (
                f"Invalid execution_mode: '{exec_mode}'. "
                f"Valid values: 'interactive', 'autonomous'"
            )
            raise ValueError(msg)

        # Determine phases (custom override or workflow default)
        if opts.custom_phases:
            if not opts.skip_reason:
                msg = "skip_reason required when custom_phases provided"
                raise ValueError(msg)
            required_phases = opts.custom_phases
        else:
            required_phases = tuple(workflow.phases)

        # Create project plan
        plan = ProjectPlan(
            issue_number=issue_number,
            issue_title=issue_title,
            workflow_name=workflow_name,
            execution_mode=exec_mode,
            required_phases=required_phases,
            skip_reason=opts.skip_reason,
            parent_branch=parent_branch,
            created_at=datetime.now(UTC).isoformat()
        )

        # Save to projects.json
        self._save_project_plan(plan)

        # Return result
        return {
            "success": True,
            "workflow_name": plan.workflow_name,
            "execution_mode": plan.execution_mode,
            "required_phases": plan.required_phases,
            "skip_reason": plan.skip_reason,
            "parent_branch": plan.parent_branch
        }

    def get_project_plan(self, issue_number: int) -> dict[str, Any] | None:
        """Get stored project plan.

        Args:
            issue_number: GitHub issue number

        Returns:
            Project plan dict or None if not found
        """
        if not self.projects_file.exists():
            return None

        projects: dict[str, Any] = json.loads(
            self.projects_file.read_text(encoding="utf-8-sig")  # Handle BOM if present
        )
        plan: dict[str, Any] | None = projects.get(str(issue_number))
        return plan

    def _save_project_plan(self, plan: ProjectPlan) -> None:
        """Save project plan to projects.json.

        Args:
            plan: ProjectPlan to save
        """
        # Ensure .st3 directory exists
        self.projects_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing projects
        if self.projects_file.exists():
            projects = json.loads(self.projects_file.read_text())
        else:
            projects = {}

        # Store plan (convert tuple to list for JSON)
        projects[str(plan.issue_number)] = {
            "issue_title": plan.issue_title,
            "workflow_name": plan.workflow_name,
            "execution_mode": plan.execution_mode,
            "required_phases": list(plan.required_phases),
            "skip_reason": plan.skip_reason,
            "parent_branch": plan.parent_branch,
            "created_at": plan.created_at
        }

        # Write to file
        self.projects_file.write_text(json.dumps(projects, indent=2))
