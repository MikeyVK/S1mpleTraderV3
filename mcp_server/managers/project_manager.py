"""ProjectManager - Phase 0.5: Project Type Selection & Phase Planning.

Manages project initialization with human-selected phase templates.
"""
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Phase 0.5: PHASE_TEMPLATES for different issue types
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
    issue_type: str  # feature, bug, docs, refactor, hotfix, custom
    required_phases: tuple[str, ...]
    optional_phases: tuple[str, ...] = ()
    skip_reason: str | None = None
    created_at: str | None = None


class ProjectManager:
    """Manages project initialization and phase plan selection.

    Phase 0.5: Human selects issue_type → generates project phase plan.
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
        issue_type: str,
        *,
        custom_phases: tuple[str, ...] | None = None,
        skip_reason: str | None = None
    ) -> dict[str, Any]:
        """Initialize project with phase plan selection.

        Phase 0.5: Human selects issue_type (feature/bug/docs/refactor/hotfix/custom),
        generates project phase plan, stores in .st3/projects.json.

        Args:
            issue_number: GitHub issue number
            issue_title: Issue title
            issue_type: Type of work (feature, bug, docs, refactor, hotfix, custom)
            custom_phases: Custom phase list (required if issue_type=custom)
            skip_reason: Reason for custom phases (required if custom_phases provided)

        Returns:
            dict with success, issue_type, required_phases, skip_reason

        Raises:
            ValueError: If issue_type invalid or custom_phases missing
        """
        # Validate issue_type
        valid_types = list(PHASE_TEMPLATES.keys()) + ["custom"]
        if issue_type not in valid_types:
            raise ValueError(
                f"Invalid issue_type: {issue_type}. "
                f"Valid types: {', '.join(valid_types)}"
            )

        # Handle custom issue_type
        if issue_type == "custom":
            if not custom_phases:
                raise ValueError(
                    "custom_phases required when issue_type='custom'. "
                    "Provide tuple of phase names."
                )
            required_phases = custom_phases
        else:
            # Use template
            template = PHASE_TEMPLATES[issue_type]
            required_phases = tuple(template["required_phases"])

        # Create project plan
        plan = ProjectPlan(
            issue_number=issue_number,
            issue_title=issue_title,
            issue_type=issue_type,
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
            "issue_type": issue_type,
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

        # Add/update project
        projects[str(plan.issue_number)] = {
            "issue_number": plan.issue_number,
            "issue_title": plan.issue_title,
            "issue_type": plan.issue_type,
            "required_phases": plan.required_phases,
            "optional_phases": plan.optional_phases,
            "skip_reason": plan.skip_reason,
            "created_at": plan.created_at
        }

        # Atomic write
        tmp_file = self.projects_file.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(projects, indent=2))
        tmp_file.replace(self.projects_file)
