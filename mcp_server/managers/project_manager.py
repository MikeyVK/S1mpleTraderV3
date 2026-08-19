# mcp_server/managers/project_manager.py
"""
Project manager - ContractsConfig-driven project initialization.

Manages project initialization with workflow selection from contracts.yaml.
Replaces hardcoded PHASE_TEMPLATES with dynamic ContractsConfig phase sequences.

@layer: Platform
@dependencies: [contracts_config]
@responsibilities:
    - Initialize projects with workflow selection
    - Validate workflow existence and execution mode
    - Support custom phase overrides with skip_reason
    - Persist project plans to deliverables.json
    - Retrieve stored project plans
"""

from __future__ import annotations

# Standard library
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from mcp_server.core.exceptions import (
    PlanningVersionMismatchError,
    StateCorruptedError,
    StateNotFoundError,
)

# Project modules
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.state_repository import StateBranchMismatchError
from mcp_server.managers.state_version_validator import StateVersionValidator
from mcp_server.schemas import ContractsConfig, WorkphasesConfig
from mcp_server.schemas.deliverables import CyclePlanningModel, UpdatePlanningModel
from mcp_server.utils.atomic_json_writer import AtomicJsonWriter

if TYPE_CHECKING:
    from mcp_server.managers.workflow_status_resolver import WorkflowStatusResolver

# Per-phase keys recognised in planning_deliverables (C8/GAP-15)
# _known_phase_keys is removed (obsolete)


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
    """Project initialization manager with ContractsConfig support.

    Uses contracts.yaml for workflow phase definitions.
    """

    def __init__(
        self,
        workspace_root: Path | str,
        contracts_config: ContractsConfig,
        git_manager: GitManager | None = None,
        workphases_config: WorkphasesConfig | None = None,
        *,
        workflow_status_resolver: WorkflowStatusResolver,
        server_root: Path,
        state_version_validator: StateVersionValidator | None = None,
    ) -> None:
        """Initialize ProjectManager."""
        self.workspace_root = Path(workspace_root)
        self._contracts_config = contracts_config
        self._git_manager = git_manager
        self._workphases_config = workphases_config
        self._workflow_status_resolver = workflow_status_resolver
        self.deliverables_file = server_root / "deliverables.json"
        self.atomic_json_writer = AtomicJsonWriter()
        self._state_version_validator = state_version_validator or StateVersionValidator()

    @property
    def workphases_config(self) -> WorkphasesConfig | None:
        """Return the workphases configuration."""
        return self._workphases_config

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
            workflow_name: Workflow from contracts.yaml (feature, bug, hotfix, etc.)
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
        if workflow_name not in self._contracts_config.workflows:
            available = list(self._contracts_config.workflows.keys())
            msg = f"Unknown workflow: '{workflow_name}'. Available: {available}"
            raise ValueError(msg)

        # Determine execution mode (default: interactive; no longer from workflow config)
        exec_mode = opts.execution_mode or "interactive"

        # Validate execution mode
        if exec_mode not in ("interactive", "autonomous"):
            msg = (
                f"Invalid execution_mode: '{exec_mode}'. Valid values: 'interactive', 'autonomous'"
            )
            raise ValueError(msg)

        # Determine phases (custom override or contracts default)
        if opts.custom_phases:
            if not opts.skip_reason:
                msg = "skip_reason required when custom_phases provided"
                raise ValueError(msg)
            required_phases = opts.custom_phases
        else:
            required_phases = tuple(self._contracts_config.get_phases(workflow_name))

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

        # Save to deliverables.json
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

    def get_first_phase(self, workflow_name: str) -> str:
        """Return the first phase name for the given workflow."""
        return self._contracts_config.get_first_phase(workflow_name)

    def get_phases(self, workflow_name: str) -> list[str]:
        """Return all phase names for the given workflow in order."""
        return self._contracts_config.get_phases(workflow_name)

    def save_planning_deliverables(
        self, issue_number: int, planning_deliverables: dict[str, Any]
    ) -> None:
        """Save planning deliverables to deliverables.json.

        Args:
            issue_number: GitHub issue number
            planning_deliverables: Planning deliverables dict (cycles, validation, etc.)

        Raises:
            ValueError: If project not found, deliverables already exist, or schema invalid.
        """
        if not self.deliverables_file.exists():
            msg = f"Project {issue_number} not found - initialize_project must be called first"
            raise ValueError(msg)

        # Load existing projects
        projects = self._read_projects()

        # Check project exists
        if str(issue_number) not in projects:
            msg = f"Project {issue_number} not found - initialize_project must be called first"
            raise ValueError(msg)

        project = projects[str(issue_number)]

        # Guard: Check if planning_deliverables already exist
        if "planning_deliverables" in project:
            msg = (
                f"Planning deliverables already exist for issue {issue_number}. "
                "Cannot overwrite existing deliverables."
            )
            raise ValueError(msg)

        # Determine if cycle-based validation is required
        workflow_name = project.get("workflow_name")
        workflow = self._contracts_config.workflows.get(workflow_name)
        is_cycle_based = False
        if workflow:
            is_cycle_based = any(phase.cycle_based for phase in workflow.phases)

        try:
            model = CyclePlanningModel.model_validate(planning_deliverables, strict=True)
        except ValidationError as e:
            raise ValueError(f"Invalid planning deliverables schema: {e}") from e

        if is_cycle_based and model.cycles is None:
            raise ValueError(
                "planning_deliverables must contain 'cycles' key for cycle-based workflows"
            )

        # Save to projects
        project["planning_deliverables"] = planning_deliverables

        # Write to file
        self._write_deliverables(projects)

    def update_planning_deliverables(
        self, issue_number: int, planning_deliverables: dict[str, Any]
    ) -> None:
        """Merge incoming planning deliverables into existing ones.

        Args:
            issue_number: GitHub issue number
            planning_deliverables: Partial or full planning deliverables to merge in.

        Raises:
            ValueError: If project not found or planning_deliverables not yet initialised.
        """
        if not self.deliverables_file.exists():
            msg = f"Project {issue_number} not found - initialize_project must be called first"
            raise ValueError(msg)

        projects = self._read_projects()

        if str(issue_number) not in projects:
            msg = f"Project {issue_number} not found - initialize_project must be called first"
            raise ValueError(msg)

        project = projects[str(issue_number)]

        if "planning_deliverables" not in project:
            msg = (
                f"No planning deliverables found for issue {issue_number}. "
                "Call save_planning_deliverables first before updating."
            )
            raise ValueError(msg)

        try:
            UpdatePlanningModel.model_validate(planning_deliverables, strict=True)
        except ValidationError as e:
            raise ValueError(f"Invalid planning deliverables schema: {e}") from e

        existing_pd = project["planning_deliverables"]
        incoming_tc = planning_deliverables.get("cycles", {})
        incoming_cycles = incoming_tc.get("cycles", [])

        # If incoming has cycles, merge them
        if incoming_tc:
            existing_tc = existing_pd.setdefault("cycles", {})
            existing_cycles_list: list[dict[str, Any]] = existing_tc.setdefault("cycles", [])

            # Build lookup: cycle_number → index in existing_cycles_list
            existing_cycle_index: dict[int, int] = {
                c["cycle_number"]: i for i, c in enumerate(existing_cycles_list)
            }

            for incoming_cycle in incoming_cycles:
                cn: int = incoming_cycle["cycle_number"]
                if cn not in existing_cycle_index:
                    # New cycle → append
                    existing_cycles_list.append(incoming_cycle)
                    existing_cycle_index[cn] = len(existing_cycles_list) - 1
                else:
                    # Existing cycle → merge deliverables by id + overwrite exit_criteria
                    target_cycle = existing_cycles_list[existing_cycle_index[cn]]
                    if "exit_criteria" in incoming_cycle:
                        target_cycle["exit_criteria"] = incoming_cycle["exit_criteria"]
                    existing_deliverables: list[dict[str, Any]] = target_cycle.setdefault(
                        "deliverables", []
                    )
                    existing_deliv_index: dict[str, int] = {
                        d["id"]: i for i, d in enumerate(existing_deliverables)
                    }
                    for incoming_deliv in incoming_cycle.get("deliverables", []):
                        d_id: str = incoming_deliv["id"]
                        if d_id in existing_deliv_index:
                            # Overwrite in place
                            existing_deliverables[existing_deliv_index[d_id]] = incoming_deliv
                        else:
                            # Append new deliverable
                            existing_deliverables.append(incoming_deliv)
                            existing_deliv_index[d_id] = len(existing_deliverables) - 1

            # Update total to reflect highest cycle number seen
            if existing_cycles_list:
                highest_cn = max(c["cycle_number"] for c in existing_cycles_list)
                existing_tc["total"] = max(existing_tc.get("total", 0), highest_cn)

        # Merge per-phase keys (design, validation, documentation)
        _phase_keys = {"design", "validation", "documentation"}
        for incoming_phase in _phase_keys:
            if incoming_phase not in planning_deliverables:
                continue
            incoming_phase_data: dict[str, Any] = planning_deliverables[incoming_phase]
            if incoming_phase not in existing_pd:
                # Phase key absent → set from incoming
                existing_pd[incoming_phase] = incoming_phase_data
            else:
                # Phase key present → merge deliverables by id
                existing_phase_delivs: list[dict[str, Any]] = existing_pd[
                    incoming_phase
                ].setdefault("deliverables", [])
                existing_phase_deliv_index: dict[str, int] = {
                    d["id"]: i for i, d in enumerate(existing_phase_delivs)
                }
                for incoming_deliv in incoming_phase_data.get("deliverables", []):
                    d_id = incoming_deliv["id"]
                    if d_id in existing_phase_deliv_index:
                        existing_phase_delivs[existing_phase_deliv_index[d_id]] = incoming_deliv
                    else:
                        existing_phase_delivs.append(incoming_deliv)
                        existing_phase_deliv_index[d_id] = len(existing_phase_delivs) - 1

        self._write_deliverables(projects)

    def get_project_plan(self, issue_number: int) -> dict[str, Any] | None:
        """Get stored project plan with current phase detection.

        Issue #298: state.json is the authoritative source. WorkflowStatusResolver
        reads current_phase from state.json directly. Returns plan without phase
        fields when state is absent or mismatched (graceful degradation).

        Args:
            issue_number: GitHub issue number

        Returns:
            Project plan dict with phase detection fields, or None if not found
        """
        if not self.deliverables_file.exists():
            return None

        projects = self._read_projects()
        plan: dict[str, Any] | None = projects.get(str(issue_number))

        if plan is None:
            return None

        # Use WorkflowStatusResolver to detect current phase (Issue #231 C4)
        try:
            status = self._workflow_status_resolver.resolve_current()
        except (StateNotFoundError, StateBranchMismatchError, OSError):
            return plan
        if status.sub_phase:
            plan["current_phase"] = f"{status.current_phase}:{status.sub_phase}"
        else:
            plan["current_phase"] = status.current_phase
        plan["phase_source"] = status.phase_source
        plan["phase_detection_error"] = status.phase_detection_error
        return plan

    def _read_projects(self) -> dict[str, Any]:
        """Read and validate deliverables envelope (Query).

        Returns:
            Dict of projects nested under "projects" key.
        """
        if not self.deliverables_file.exists():
            return {}

        try:
            self._state_version_validator.validate_file(
                self.deliverables_file, expected_version="1.0.0", is_planning=True
            )
        except (PlanningVersionMismatchError, StateCorruptedError):
            self._state_version_validator.backup_file(self.deliverables_file)
            raise

        content = self.deliverables_file.read_text(encoding="utf-8-sig")
        data = json.loads(content)
        if not isinstance(data, dict):
            return {}
        projects = data.get("projects")
        if projects is None:
            projects = {k: v for k, v in data.items() if k != "schema_version"}
        if not isinstance(projects, dict):
            return {}
        return projects

    def _write_deliverables(self, projects: dict[str, Any]) -> None:
        """Persist deliverables.json via atomic replacement (Command)."""
        payload = {
            "schema_version": "1.0.0",
            "projects": projects,
        }
        self.atomic_json_writer.write_json(self.deliverables_file, payload)

    def _save_project_plan(self, plan: ProjectPlan) -> None:
        """Save project plan to deliverables.json.

        Args:
            plan: ProjectPlan to save
        """
        # Ensure state directory exists
        self.deliverables_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing projects
        projects = self._read_projects()

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
        self._write_deliverables(projects)
