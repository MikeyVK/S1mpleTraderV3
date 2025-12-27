"""ProjectManager - Workflow-based project initialization.

Issue #50: Migrated from PHASE_TEMPLATES to workflows.yaml configuration.
Manages project initialization with workflow selection from workflows.yaml.
"""
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp_server.config.workflows import workflow_config


@dataclass
class ProjectInitOptions:
    """Optional parameters for project initialization.

    Reduces initialize_project() parameter count from 7 to 4.

    Attributes:
        execution_mode: Execution mode override (interactive or autonomous)
        custom_phases: Custom phase list (overrides workflow phases)
        skip_reason: Reason for custom phases (required if custom_phases provided)
    """

    execution_mode: str | None = None
    custom_phases: tuple[str, ...] | None = None
    skip_reason: str | None = None


@dataclass
class ProjectPlan:
    """Project phase plan (immutable after creation)."""

    issue_number: int
    issue_title: str
    workflow_name: str
    execution_mode: str
    required_phases: tuple[str, ...]
    skip_reason: str | None = None
    created_at: str | None = None


class ProjectManager:
    """Manages project initialization and phase plan selection.

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
        options: ProjectInitOptions | None = None
    ) -> dict[str, Any]:
        """Initialize project with workflow selection.

        Args:
            issue_number: GitHub issue number
            issue_title: Issue title
            workflow_name: Workflow name from workflows.yaml (feature, bug, hotfix, etc.)
            options: Optional parameters (execution_mode, custom_phases, skip_reason)

        Returns:
            dict with success, workflow_name, execution_mode, required_phases, skip_reason

        Raises:
            ValueError: If workflow_name invalid or custom_phases without skip_reason
        """
        opts = options or ProjectInitOptions()

        # Validate workflow exists
        try:
            workflow = workflow_config.get_workflow(workflow_name)
        except ValueError as e:
            # Re-raise with workflow_config error message (includes available workflows)
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
            "skip_reason": plan.skip_reason
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

        projects: dict[str, Any] = json.loads(self.projects_file.read_text())
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
            "created_at": plan.created_at
        }

        # Write to file
        self.projects_file.write_text(json.dumps(projects, indent=2))
