"""ProjectManager - Phase 0.5: Project Type Selection & Phase Planning.

Manages project initialization with human-selected phase templates.

Issue #50: Migrated from PHASE_TEMPLATES to workflows.yaml.
- Old API: initialize_project(issue_type="feature")
- New API: initialize_project(workflow_name="feature")
"""
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp_server.config.workflows import workflow_config

# Phase 0.5: PHASE_TEMPLATES for different issue types (DEPRECATED - use workflows.yaml)
PHASE_TEMPLATES = {
    "feature": {
        "required_phases": (
            "discovery", "planning", "design", "component",
            "tdd", "integration", "documentation"
        ),
        "description": "Full 7-phase workflow for new features"
    },
    "bug": {
        "required_phases": (
            "discovery", "planning", "component",
            "tdd", "integration", "documentation"
        ),
        "description": "6-phase workflow (skip design)"
    },
    "docs": {
        "required_phases": ("discovery", "planning", "component", "documentation"),
        "description": "4-phase workflow (skip tdd + integration)"
    },
    "refactor": {
        "required_phases": ("discovery", "planning", "tdd", "integration", "documentation"),
        "description": "5-phase workflow (skip design + component)"
    },
    "hotfix": {
        "required_phases": ("component", "tdd", "integration"),
        "description": "Minimal 3-phase workflow (requires approval for all operations)"
    }
}


@dataclass
class ProjectPlan:
    """Project phase plan (immutable after creation)."""

    issue_number: int
    issue_title: str
    workflow_name: str  # Issue #50: Renamed from issue_type
    execution_mode: str  # Issue #50: New field (interactive or autonomous)
    required_phases: tuple[str, ...]
    optional_phases: tuple[str, ...] = ()
    skip_reason: str | None = None
    created_at: str | None = None


class ProjectManager:
    """Manages project initialization and phase plan selection.

    Phase 0.5: Human selects issue_type → generates project phase plan.
    Issue #50: Migrated to workflow_name + workflows.yaml.
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
        issue_type: str | None = None,  # DEPRECATED: use workflow_name
        *,
        workflow_name: str | None = None,  # NEW: replaces issue_type
        custom_phases: tuple[str, ...] | None = None,
        skip_reason: str | None = None
    ) -> dict[str, Any]:
        """Initialize project with phase plan selection.

        Phase 0.5: Human selects issue_type (feature/bug/docs/refactor/hotfix/custom),
        generates project phase plan, stores in .st3/projects.json.

        Issue #50: Updated to use workflow_name + workflows.yaml instead of PHASE_TEMPLATES.

        Args:
            issue_number: GitHub issue number
            issue_title: Issue title
            issue_type: DEPRECATED - use workflow_name instead
            workflow_name: Workflow name from workflows.yaml (feature, bug, hotfix, etc.)
            custom_phases: Custom phase list (overrides workflow phases)
            skip_reason: Reason for custom phases (required if custom_phases provided)

        Returns:
            dict with success, workflow_name, execution_mode, required_phases, skip_reason

        Raises:
            ValueError: If workflow_name invalid or both issue_type and workflow_name provided
        """
        # Handle backward compatibility
        if issue_type is not None and workflow_name is not None:
            raise ValueError(
                "Cannot specify both issue_type and workflow_name. "
                "Use workflow_name (issue_type is deprecated)."
            )

        if issue_type is not None:
            # Backward compatibility: map issue_type to workflow_name
            workflow_name = issue_type

        if workflow_name is None:
            raise ValueError(
                "workflow_name is required. "
                "Specify workflow_name parameter (e.g., workflow_name='feature')."
            )

        # Validate workflow_name exists in workflows.yaml
        try:
            workflow = workflow_config.get_workflow(workflow_name)
        except ValueError as e:
            # Re-raise with workflow_config error message (includes available workflows)
            raise ValueError(str(e)) from e

        # Determine execution mode and phases
        execution_mode = workflow.default_execution_mode

        if custom_phases is not None:
            # Custom phases override workflow phases
            required_phases = custom_phases
        else:
            # Use workflow phases from workflows.yaml
            required_phases = tuple(workflow.phases)

        # Create project plan
        plan = ProjectPlan(
            issue_number=issue_number,
            issue_title=issue_title,
            workflow_name=workflow_name,
            execution_mode=execution_mode,
            required_phases=required_phases,
            skip_reason=skip_reason,
            created_at=datetime.now(UTC).isoformat()
        )

        # Store project metadata
        self._save_project_plan(plan)

        return {
            "success": True,
            "issue_number": issue_number,
            "issue_title": issue_title,
            "workflow_name": workflow_name,
            "execution_mode": execution_mode,
            "required_phases": required_phases,
            "skip_reason": skip_reason
        }

    def get_project_plan(self, issue_number: int) -> dict[str, Any] | None:
        """Retrieve project plan for issue.

        Args:
            issue_number: GitHub issue number

        Returns:
            Project plan dict or None if not found
        """
        if not self.projects_file.exists():
            return None

        projects: dict[str, Any] = json.loads(self.projects_file.read_text())
        plan = projects.get(str(issue_number))
        return dict(plan) if plan else None

    def _save_project_plan(self, plan: ProjectPlan) -> None:
        """Save project plan to .st3/projects.json (atomic write).

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

        # Add/update project (NEW structure with workflow_name + execution_mode)
        projects[str(plan.issue_number)] = {
            "issue_number": plan.issue_number,
            "issue_title": plan.issue_title,
            "workflow_name": plan.workflow_name,  # NEW: replaces issue_type
            "execution_mode": plan.execution_mode,  # NEW: from workflow
            "required_phases": plan.required_phases,
            "optional_phases": plan.optional_phases,
            "skip_reason": plan.skip_reason,
            "created_at": plan.created_at
        }

        # Atomic write
        tmp_file = self.projects_file.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(projects, indent=2))
        tmp_file.replace(self.projects_file)
