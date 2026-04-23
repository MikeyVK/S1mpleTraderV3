# mcp_server/managers/phase_state_engine.py
"""
Phase state engine - Workflow-based phase transition management.

Manages branch phase state with strict sequential validation via workflows.yaml.
Supports both standard sequential transitions and forced non-sequential transitions
with audit trail.

@layer: Platform
@dependencies: [workflow_config, project_manager]
@responsibilities:
    - Initialize branch state with workflow caching
    - Validate phase transitions against workflow definitions
    - Execute standard sequential transitions
    - Execute forced non-sequential transitions with skip_reason
    - Maintain transition history with forced flag audit
    - Persist state to .st3/state.json
"""

# Standard library
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Project modules
from pydantic import ValidationError

from mcp_server.core.interfaces import (
    GateReport,
    IStateReconstructor,
    IStateRepository,
    IWorkflowGateRunner,
)
from mcp_server.core.phase_detection import ScopeDecoder
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.state_repository import BranchState
from mcp_server.schemas import GitConfig, WorkflowConfig, WorkphasesConfig

logger = logging.getLogger(__name__)


@dataclass
class TransitionRecord:
    """Phase transition record for audit trail.

    Field order: identifier → data → flags → optional
    """

    # Core transition data
    from_phase: str
    to_phase: str
    timestamp: str

    # Metadata
    human_approval: str | None
    forced: bool

    # Optional fields
    skip_reason: str | None = None


class PhaseStateEngine:
    """Phase state and transition manager with workflow validation.

    Validates transitions against workflows.yaml definitions.
    Supports standard sequential and forced non-sequential transitions.
    """

    def __init__(
        self,
        workspace_root: Path | str,
        project_manager: ProjectManager,
        git_config: GitConfig,
        workflow_config: WorkflowConfig,
        workphases_config: WorkphasesConfig,
        state_repository: IStateRepository,
        scope_decoder: ScopeDecoder,
        workflow_gate_runner: IWorkflowGateRunner,
        state_reconstructor: IStateReconstructor,
    ) -> None:
        """Initialize PhaseStateEngine."""
        workspace_path = Path(workspace_root)
        self.state_file = workspace_path / ".st3" / "state.json"
        self.project_manager = project_manager

        self._workflow_config = workflow_config
        self._git_config = git_config
        self._workphases_config = workphases_config
        self._state_repository = state_repository
        self._scope_decoder = scope_decoder
        self._workflow_gate_runner = workflow_gate_runner
        self._state_reconstructor = state_reconstructor

    def initialize_branch(
        self, branch: str, issue_number: int, initial_phase: str, parent_branch: str | None = None
    ) -> dict[str, Any]:
        """Initialize branch state with workflow caching.

        Caches workflow_name in state.json for performance optimization.

        Args:
            branch: Branch name (e.g., 'feature/42-test')
            issue_number: GitHub issue number
            initial_phase: Starting phase
            parent_branch: Optional parent branch - if None, inherits from project

        Returns:
            dict with success, branch, current_phase, parent_branch

        Raises:
            ValueError: If project not initialized
        """
        # Get project plan to cache workflow_name
        project = self.project_manager.get_project_plan(issue_number)
        if not project:
            msg = f"Project {issue_number} not found. Initialize project first."
            raise ValueError(msg)

        # Determine parent_branch: explicit param or inherit from project
        if parent_branch is None:
            parent_branch = project.get("parent_branch")

        warnings: list[str] = []
        if self._has_uncommitted_state_changes():
            warnings.append("state.json has uncommitted local changes")

        state = BranchState(
            branch=branch,
            issue_number=issue_number,
            workflow_name=project["workflow_name"],
            current_phase=initial_phase,
            current_cycle=None,
            last_cycle=None,
            cycle_history=[],
            required_phases=project.get("required_phases", []),
            execution_mode=project.get("execution_mode", "normal"),
            issue_title=project.get("issue_title"),
            parent_branch=parent_branch,
            created_at=datetime.now(UTC).isoformat(),
            transitions=[],
        )
        self._save_state(branch, state)

        return {
            "success": True,
            "branch": branch,
            "current_phase": initial_phase,
            "parent_branch": parent_branch,
            "warnings": warnings,
        }

    def transition(
        self, branch: str, to_phase: str, human_approval: str | None = None
    ) -> dict[str, Any]:
        """Execute strict sequential phase transition."""
        state = self._load_state_or_reconstruct(branch)
        from_phase = state.current_phase
        workflow_name = state.workflow_name

        self._workflow_config.validate_transition(workflow_name, from_phase, to_phase)

        issue_number = state.issue_number
        if issue_number is None:
            raise ValueError(f"Branch '{branch}' has no issue_number in state")

        self._workflow_gate_runner.enforce(
            workflow_name=workflow_name,
            phase=from_phase,
            cycle_number=state.current_cycle,
        )

        if self._is_cycle_based_phase(workflow_name, from_phase):
            self.on_exit_implementation_phase(branch)
            state = self._load_state_or_reconstruct(branch)

        transition = TransitionRecord(
            from_phase=from_phase,
            to_phase=to_phase,
            timestamp=datetime.now(UTC).isoformat(),
            human_approval=human_approval,
            forced=False,
        )

        updated_state = state.with_updates(
            current_phase=to_phase,
            transitions=[*state.transitions, self._transition_to_dict(transition)],
        )
        self._save_state(branch, updated_state)

        if self._is_cycle_based_phase(workflow_name, to_phase):
            self.on_enter_implementation_phase(branch, issue_number)

        return {"success": True, "from_phase": from_phase, "to_phase": to_phase}

    def force_transition(
        self, branch: str, to_phase: str, skip_reason: str, human_approval: str
    ) -> dict[str, Any]:
        """Execute forced non-sequential phase transition."""
        state = self._load_state_or_reconstruct(branch)
        from_phase = state.current_phase
        workflow_name = state.workflow_name
        issue_number = state.issue_number
        if issue_number is None:
            raise ValueError(f"Branch '{branch}' has no issue_number in state")

        report = self._workflow_gate_runner.inspect(
            workflow_name=workflow_name,
            phase=from_phase,
            cycle_number=state.current_cycle,
        )
        skipped_gates = list(report.blocking)
        passing_gates = list(report.passing)
        report_payload = self._gate_report_to_payload(report)

        if not skipped_gates and not passing_gates:
            skipped_gates, passing_gates = self._legacy_workphases_gate_summary(
                issue_number=issue_number,
                from_phase=from_phase,
                to_phase=to_phase,
            )
            report_payload = {
                "passing": passing_gates,
                "blocking": skipped_gates,
                "details": {},
            }

        if skipped_gates:
            logger.warning(
                "force_transition skipped_gates=%s (from=%s, to=%s, skip_reason=%r)",
                skipped_gates,
                from_phase,
                to_phase,
                skip_reason,
            )

        if self._is_cycle_based_phase(workflow_name, from_phase):
            self.on_exit_implementation_phase(branch)
            state = self.get_state(branch)

        transition = TransitionRecord(
            from_phase=from_phase,
            to_phase=to_phase,
            timestamp=datetime.now(UTC).isoformat(),
            human_approval=human_approval,
            forced=True,
            skip_reason=skip_reason,
        )

        updated_state = state.with_updates(
            current_phase=to_phase,
            transitions=[*state.transitions, self._transition_to_dict(transition)],
            skip_reason=skip_reason,
        )
        self._save_state(branch, updated_state)

        if self._is_cycle_based_phase(workflow_name, to_phase):
            self.on_enter_implementation_phase(branch, issue_number)

        return {
            "success": True,
            "from_phase": from_phase,
            "to_phase": to_phase,
            "forced": True,
            "skip_reason": skip_reason,
            "skipped_gates": skipped_gates,
            "passing_gates": passing_gates,
            "gate_report": report_payload,
        }

    def transition_cycle(
        self,
        branch: str,
        to_cycle: int,
        gate_runner: IWorkflowGateRunner | None = None,
    ) -> dict[str, Any]:
        """Execute one strict sequential cycle transition inside the active cycle-based phase."""
        state = self._load_state_or_reconstruct(branch)
        issue_number = self._require_issue_number(branch, state)
        cycles, total_cycles = self._get_tdd_cycles(issue_number)
        runner = gate_runner or self._workflow_gate_runner
        self._validate_cycle_phase(
            workflow_name=state.workflow_name,
            current_phase=state.current_phase,
            gate_runner=runner,
        )
        self._validate_cycle_number_range(to_cycle, issue_number)
        self._validate_strict_cycle_progression(state.current_cycle, to_cycle)
        self._validate_current_cycle_exit_criteria(state.current_cycle, cycles)

        if state.current_cycle is not None:
            runner.enforce(
                workflow_name=state.workflow_name,
                phase=state.current_phase,
                cycle_number=state.current_cycle,
            )

        from_cycle = state.current_cycle or 0
        cycle_name = self._get_cycle_name(cycles, to_cycle)
        history_entry = {
            "cycle_number": to_cycle,
            "name": cycle_name,
            "forced": False,
            "entered": datetime.now(UTC).isoformat(),
        }
        updated_state = state.with_updates(
            last_cycle=from_cycle,
            current_cycle=to_cycle,
            cycle_history=[*state.cycle_history, history_entry],
        )
        self._save_state(branch, updated_state)

        return {
            "success": True,
            "from_cycle": from_cycle,
            "to_cycle": to_cycle,
            "total_cycles": total_cycles,
            "cycle_name": cycle_name,
        }

    def force_cycle_transition(
        self,
        branch: str,
        to_cycle: int,
        skip_reason: str,
        human_approval: str,
        gate_runner: IWorkflowGateRunner | None = None,
    ) -> dict[str, Any]:
        """Execute one forced cycle transition inside the active cycle-based phase."""
        if not skip_reason or not skip_reason.strip():
            raise ValueError(
                "skip_reason is required for forced transitions. "
                "Provide justification for backward/skip transition."
            )
        if not human_approval or not human_approval.strip():
            raise ValueError(
                "human_approval is required for forced transitions. "
                "Provide approval (e.g., 'John approved on 2026-02-17')."
            )

        state = self._load_state_or_reconstruct(branch)
        issue_number = self._require_issue_number(branch, state)
        cycles, total_cycles = self._get_tdd_cycles(issue_number)
        runner = gate_runner or self._workflow_gate_runner
        self._validate_cycle_phase(
            workflow_name=state.workflow_name,
            current_phase=state.current_phase,
            gate_runner=runner,
        )
        self._validate_cycle_number_range(to_cycle, issue_number)

        report = runner.inspect(
            workflow_name=state.workflow_name,
            phase=state.current_phase,
            cycle_number=state.current_cycle,
        )

        from_cycle = state.current_cycle or 0
        cycle_name = self._get_cycle_name(cycles, to_cycle)
        skipped_cycles = list(range(min(from_cycle, to_cycle) + 1, max(from_cycle, to_cycle)))
        history_entry = {
            "cycle_number": to_cycle,
            "name": cycle_name,
            "entered": datetime.now(UTC).isoformat(),
            "forced": True,
            "skip_reason": skip_reason,
            "human_approval": human_approval,
            "skipped_cycles": skipped_cycles,
        }
        updated_state = state.with_updates(
            last_cycle=from_cycle,
            current_cycle=to_cycle,
            cycle_history=[*state.cycle_history, history_entry],
        )
        self._save_state(branch, updated_state)

        return {
            "success": True,
            "from_cycle": from_cycle,
            "to_cycle": to_cycle,
            "total_cycles": total_cycles,
            "cycle_name": cycle_name,
            "forced": True,
            "skip_reason": skip_reason,
            "skipped_gates": list(report.blocking),
            "passing_gates": list(report.passing),
            "gate_report": self._gate_report_to_payload(report),
        }

    def get_current_phase(self, branch: str) -> str:
        """Get current phase for branch."""
        return self.get_state(branch).current_phase

    def _gate_report_to_payload(self, report: GateReport) -> dict[str, Any]:
        """Serialize one gate report into plain Python collections."""
        return {
            "passing": list(report.passing),
            "blocking": list(report.blocking),
            "details": dict(report.details),
        }

    def _legacy_workphases_gate_summary(
        self,
        issue_number: int,
        from_phase: str,
        to_phase: str,
    ) -> tuple[list[str], list[str]]:
        """Fallback skipped-gate summary for workspaces without phase contracts."""
        skipped_gates: list[str] = []
        passing_gates: list[str] = []
        plan = self.project_manager.get_project_plan(issue_number)

        for entry in self._workphases_config.get_exit_requires(from_phase):
            key = entry.get("key")
            if not key:
                continue
            gate_id = f"exit:{from_phase}:{key}"
            if plan is None or key not in plan:
                skipped_gates.append(gate_id)
            else:
                passing_gates.append(gate_id)

        for entry in self._workphases_config.get_entry_expects(to_phase):
            key = entry.get("key")
            if not key:
                continue
            gate_id = f"entry:{to_phase}:{key}"
            if plan is None or key not in plan:
                skipped_gates.append(gate_id)
            else:
                passing_gates.append(gate_id)

        return skipped_gates, passing_gates

    def _has_uncommitted_state_changes(self) -> bool:
        """Check whether tracked state.json has local git changes."""
        if not self.state_file.exists():
            return False

        try:
            env = os.environ.copy()
            env.setdefault("GIT_TERMINAL_PROMPT", "0")
            env.setdefault("GIT_PAGER", "cat")
            env.setdefault("PAGER", "cat")

            result = subprocess.run(
                ["git", "status", "--porcelain", "--", ".st3/state.json"],
                cwd=self._workspace_root_path(),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
                env=env,
            )
            return bool(result.stdout.strip())
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            logger.warning(
                "Unable to check state.json git status during initialize_branch: %s",
                exc,
            )
            return False

    def get_state(self, branch: str) -> BranchState:
        """Get persisted state for one branch without reconstruction side effects."""
        loaded_state = self._state_repository.load(branch)
        if loaded_state.branch != branch:
            msg = f"Branch state for '{branch}' not found"
            raise FileNotFoundError(msg)
        return loaded_state

    def _load_state_or_reconstruct(self, branch: str) -> BranchState:
        """Load persisted state or reconstruct it explicitly for transition flows."""
        try:
            return self.get_state(branch)
        except (FileNotFoundError, OSError, json.JSONDecodeError, ValidationError):
            logger.warning("Invalid or missing state.json, reconstructing", exc_info=True)

        reconstructed_state = self._state_reconstructor.reconstruct(branch)
        self._save_state(branch, reconstructed_state)
        return reconstructed_state

    def _require_issue_number(self, branch: str, state: BranchState) -> int:
        """Return the persisted issue number or raise a descriptive error."""
        issue_number = state.issue_number
        if issue_number is None:
            raise ValueError(f"Branch '{branch}' has no issue_number in state")
        return issue_number

    def _get_tdd_cycles(self, issue_number: int) -> tuple[list[dict[str, Any]], int]:
        """Return planned TDD cycles and total count for one issue."""
        self._validate_planning_deliverables_exist(issue_number)
        plan = self.project_manager.get_project_plan(issue_number)
        assert plan is not None
        planning_deliverables = plan["planning_deliverables"]
        tdd_cycles = planning_deliverables.get("tdd_cycles", {})
        cycles = tdd_cycles.get("cycles", [])
        total_cycles = tdd_cycles.get("total", 0)
        return cycles, total_cycles

    def _is_cycle_based_phase(
        self,
        workflow_name: str,
        phase: str,
        gate_runner: IWorkflowGateRunner | None = None,
    ) -> bool:
        """Return whether one workflow phase is configured for cycle transitions."""
        runner = gate_runner or self._workflow_gate_runner
        return runner.is_cycle_based_phase(workflow_name, phase)

    def _validate_cycle_phase(
        self,
        workflow_name: str,
        current_phase: str,
        gate_runner: IWorkflowGateRunner | None = None,
    ) -> None:
        """Ensure cycle transitions only run inside phases marked cycle_based."""
        if not self._is_cycle_based_phase(workflow_name, current_phase, gate_runner):
            raise ValueError(
                "Cycle transitions only allowed during cycle-based phases "
                f"(current: {current_phase})."
            )

    def _validate_strict_cycle_progression(
        self,
        current_cycle: int | None,
        to_cycle: int,
    ) -> None:
        """Validate forward-only, sequential strict cycle movement."""
        if current_cycle is not None and to_cycle <= current_cycle:
            raise ValueError(
                f"Backwards transition not allowed (current: {current_cycle}, "
                f"target: {to_cycle}). Use force_cycle_transition for backwards transitions."
            )
        if current_cycle is not None and to_cycle != current_cycle + 1:
            raise ValueError(
                f"Non-sequential transition not allowed (current: {current_cycle}, "
                f"target: {to_cycle}). Use force_cycle_transition to skip cycles."
            )

    def _validate_current_cycle_exit_criteria(
        self,
        current_cycle: int | None,
        cycles: list[dict[str, Any]],
    ) -> None:
        """Ensure the current cycle defines exit criteria before a strict move."""
        if current_cycle is None:
            return

        current_cycle_data = next(
            (
                cycle
                for cycle in cycles
                if isinstance(cycle, dict) and cycle.get("cycle_number") == current_cycle
            ),
            None,
        )
        if current_cycle_data is None:
            return

        exit_criteria = current_cycle_data.get("exit_criteria", "")
        if not isinstance(exit_criteria, str) or not exit_criteria.strip():
            raise ValueError(
                f"Cycle {current_cycle} exit criteria not defined. "
                "Define exit_criteria in planning deliverables before transitioning."
            )

    def _get_cycle_name(self, cycles: list[dict[str, Any]], to_cycle: int) -> str:
        """Resolve the display name for one target cycle."""
        cycle_details = next(
            (
                cycle
                for cycle in cycles
                if isinstance(cycle, dict) and cycle.get("cycle_number") == to_cycle
            ),
            None,
        )
        if cycle_details is None:
            return "Unknown"
        name = cycle_details.get("name")
        return name if isinstance(name, str) and name else "Unknown"

    def _validate_cycle_number_range(self, cycle_number: int, issue_number: int) -> None:
        """Validate cycle_number is within valid range [1..total].

        Args:
            cycle_number: Cycle number to validate
            issue_number: GitHub issue number for context

        Raises:
            ValueError: If cycle_number is out of range or planning deliverables not found

        Issue #146 Cycle 2: Range validation for TDD cycle transitions.
        """
        _cycles, total_cycles = self._get_tdd_cycles(issue_number)

        if cycle_number < 1 or cycle_number > total_cycles:
            msg = f"cycle_number must be in range [1..{total_cycles}], got {cycle_number}"
            raise ValueError(msg)

    def _validate_planning_deliverables_exist(self, issue_number: int) -> None:
        """Validate that planning deliverables exist for issue.

        Args:
            issue_number: GitHub issue number

        Raises:
            ValueError: If planning deliverables not found

        Issue #146 Cycle 2: Existence check before cycle transitions.
        """
        plan = self.project_manager.get_project_plan(issue_number)
        if not plan or "planning_deliverables" not in plan:
            msg = f"Planning deliverables not found for issue {issue_number}"
            raise ValueError(msg)

    def _save_state(self, branch: str, state: BranchState) -> None:
        """Save branch state to state.json through the configured repository."""
        validated_state = state if state.branch == branch else state.with_updates(branch=branch)
        self._state_repository.save(validated_state)

    def _transition_to_dict(self, transition: TransitionRecord) -> dict[str, Any]:
        """Convert TransitionRecord to dict for JSON serialization.

        Args:
            transition: TransitionRecord instance

        Returns:
            dict representation
        """
        return {
            "from_phase": transition.from_phase,
            "to_phase": transition.to_phase,
            "timestamp": transition.timestamp,
            "human_approval": transition.human_approval,
            "forced": transition.forced,
            "skip_reason": transition.skip_reason,
        }

    def _workspace_root_path(self) -> Path:
        """Return the workspace root derived from the tracked state file location."""
        return self.state_file.parent.parent

    def on_enter_implementation_phase(self, branch: str, issue_number: int) -> None:
        """Hook called when entering implementation phase.

        Auto-initializes TDD cycle 1 in branch state. Planning deliverables
        are validated at planning exit (on_exit_planning_phase) — not here.

        Args:
            branch: Branch name
            issue_number: GitHub issue number
        """
        state = self.get_state(branch)

        if state.current_cycle is None:
            updated_state = state.with_updates(
                current_cycle=1,
                last_cycle=0,
                cycle_history=[*state.cycle_history],
            )
            self._save_state(branch, updated_state)

        logger.info(f"Entered implementation phase for issue {issue_number} on branch {branch}")

    def on_exit_implementation_phase(self, branch: str) -> None:
        """Hook called when exiting implementation phase.

        Preserves last_cycle and clears current_cycle.
        Logs warning if not all cycles completed.

        Args:
            branch: Branch name
        """
        state = self.get_state(branch)
        current_cycle = state.current_cycle

        if current_cycle is not None:
            updated_state = state.with_updates(last_cycle=current_cycle, current_cycle=None)
            logger.info(f"Exited implementation phase at cycle {current_cycle} on branch {branch}")
            self._save_state(branch, updated_state)
