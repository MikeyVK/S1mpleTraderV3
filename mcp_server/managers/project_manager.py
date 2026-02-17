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
from backend.core.phase_detection import ScopeDecoder
from mcp_server.config.workflows import workflow_config
from mcp_server.managers.git_manager import GitManager


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

    Note: Has 8 fields which exceeds pylint's default of 7,
    but all fields are necessary for complete project metadata.
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

    def __init__(self, workspace_root: Path | str) -> None:
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
        options: ProjectInitOptions | None = None,
    ) -> dict[str, Any]:
        """Initialize project with workflow selection.

        Args:
            issue_number: GitHub issue number
            issue_title: Issue title
            workflow_name: Workflow from workflows.yaml (feature, bug, hotfix, etc.)
            options: Optional parameters (execution_mode, custom_phases, skip_reason,
                    parent_branch)

        Returns:
            dict with success, workflow_name, execution_mode, required_phases,
            skip_reason, parent_branch

        Raises:
            ValueError: If workflow invalid or custom_phases without skip_reason
        """
        opts = options or ProjectInitOptions()

        # Extract parent_branch from options
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
                f"Invalid execution_mode: '{exec_mode}'. Valid values: 'interactive', 'autonomous'"
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
            created_at=datetime.now(UTC).isoformat(),
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
            "parent_branch": plan.parent_branch,
        }

    def save_planning_deliverables(
        self, issue_number: int, planning_deliverables: dict[str, Any]
    ) -> None:
        """Save planning deliverables to projects.json.

        Args:
            issue_number: GitHub issue number
            planning_deliverables: Planning deliverables dict (tdd_cycles, validation_plan, etc.)

        Raises:
            ValueError: If project not found, deliverables already exist, or schema invalid
        """
        if not self.projects_file.exists():
            msg = f"Project {issue_number} not found - initialize_project must be called first"
            raise ValueError(msg)

        # Load existing projects
        projects = json.loads(self.projects_file.read_text(encoding="utf-8-sig"))

        # Check project exists
        if str(issue_number) not in projects:
            msg = f"Project {issue_number} not found - initialize_project must be called first"
            raise ValueError(msg)

        # Guard: Check if planning_deliverables already exist
        if "planning_deliverables" in projects[str(issue_number)]:
            msg = (
                f"Planning deliverables already exist for issue {issue_number}. "
                "Cannot overwrite existing deliverables."
            )
            raise ValueError(msg)

        # Validate schema: tdd_cycles required
        if "tdd_cycles" not in planning_deliverables:
            msg = "planning_deliverables must contain 'tdd_cycles' key"
            raise ValueError(msg)

        tdd_cycles = planning_deliverables["tdd_cycles"]

        # Validate tdd_cycles structure
        if not isinstance(tdd_cycles, dict):
            msg = "tdd_cycles must be a dict"
            raise ValueError(msg)

        if "total" not in tdd_cycles:
            msg = "tdd_cycles must contain 'total' key"
            raise ValueError(msg)

        if not isinstance(tdd_cycles["total"], int) or tdd_cycles["total"] < 1:
            msg = "tdd_cycles.total must be a positive integer"
            raise ValueError(msg)

        if "cycles" not in tdd_cycles:
            msg = "tdd_cycles must contain 'cycles' key"
            raise ValueError(msg)

        if not isinstance(tdd_cycles["cycles"], list):
            msg = "tdd_cycles.cycles must be a list"
            raise ValueError(msg)

        # Add planning_deliverables to project
        projects[str(issue_number)]["planning_deliverables"] = planning_deliverables

        # Write to file
        self.projects_file.write_text(json.dumps(projects, indent=2))

    def get_project_plan(self, issue_number: int) -> dict[str, Any] | None:
        """Get stored project plan with current phase detection.

        Issue #139: Adds current_phase, phase_source, phase_detection_error via ScopeDecoder.
        Uses commit-scope precedence: commit-scope > state.json > unknown.

        Args:
            issue_number: GitHub issue number

        Returns:
            Project plan dict with phase detection fields, or None if not found
        """
        if not self.projects_file.exists():
            return None

        projects: dict[str, Any] = json.loads(
            self.projects_file.read_text(encoding="utf-8-sig")  # Handle BOM if present
        )
        plan: dict[str, Any] | None = projects.get(str(issue_number))

        if plan is None:
            return None

        # Detect current phase via ScopeDecoder (Issue #139)
        git_manager = GitManager()
        try:
            recent_commits = git_manager.get_recent_commits(limit=1)
        except Exception:
            # If git fails (e.g., no repo), return unknown
            recent_commits = []

        if not recent_commits:
            # No commits → unknown phase
            plan["current_phase"] = "unknown"
            plan["phase_source"] = "unknown"
            plan["phase_detection_error"] = "No commits found in repository"
        else:
            # Detect phase from commit
            decoder = ScopeDecoder()
            result = decoder.detect_phase(commit_message=recent_commits[0], fallback_to_state=True)

            # Add phase detection results to plan
            phase = result["workflow_phase"]
            sub_phase = result["sub_phase"]

            # Format: "tdd:red" or "research" (with or without subphase)
            if sub_phase:
                plan["current_phase"] = f"{phase}:{sub_phase}"
            else:
                plan["current_phase"] = phase

            plan["phase_source"] = result["source"]
            plan["phase_detection_error"] = result.get("error_message")

        return plan

    def _save_project_plan(self, plan: ProjectPlan) -> None:
        """Save project plan to projects.json.

        Args:
            plan: ProjectPlan to save
        """
        # Ensure .st3 directory exists
        self.projects_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing projects
        projects = json.loads(self.projects_file.read_text()) if self.projects_file.exists() else {}

        # Store plan (convert tuple to list for JSON)
        projects[str(plan.issue_number)] = {
            "issue_title": plan.issue_title,
            "workflow_name": plan.workflow_name,
            "execution_mode": plan.execution_mode,
            "required_phases": list(plan.required_phases),
            "skip_reason": plan.skip_reason,
            "parent_branch": plan.parent_branch,
            "created_at": plan.created_at,
        }

        # Write to file
        self.projects_file.write_text(json.dumps(projects, indent=2))
