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
from mcp_server.managers.deliverable_checker import DeliverableChecker, DeliverableCheckError
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
        self.workspace_root = Path(workspace_root)
        self.state_file = self.workspace_root / ".st3" / "state.json"
        self.project_manager = project_manager

        workspace_workphases_path = self.workspace_root / ".st3" / "config" / "workphases.yaml"
        if not workspace_workphases_path.exists():
            relaxed_payload = workphases_config.model_dump()
            for phase_definition in relaxed_payload.get("phases", {}).values():
                if isinstance(phase_definition, dict):
                    phase_definition["exit_requires"] = []
                    phase_definition["entry_expects"] = []
            workphases_config = WorkphasesConfig.model_validate(relaxed_payload)

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
        state = self.get_state(branch)
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

        if from_phase == "implementation":
            self.on_exit_implementation_phase(branch)
            state = self.get_state(branch)

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

        if to_phase == "implementation":
            self.on_enter_implementation_phase(branch, issue_number)

        return {"success": True, "from_phase": from_phase, "to_phase": to_phase}

    def force_transition(
        self, branch: str, to_phase: str, skip_reason: str, human_approval: str
    ) -> dict[str, Any]:
        """Execute forced non-sequential phase transition."""
        state = self.get_state(branch)
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

        if from_phase == "implementation":
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

        if to_phase == "implementation":
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
                cwd=self.workspace_root,
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
        """Get full state for branch with auto-recovery."""
        try:
            loaded_state = self._state_repository.load(branch)
            if loaded_state.branch == branch:
                return loaded_state
        except (FileNotFoundError, OSError, json.JSONDecodeError, ValidationError):
            logger.warning("Invalid or missing state.json, reconstructing", exc_info=True)

        reconstructed_state = self._reconstruct_branch_state(branch)
        self._save_state(branch, reconstructed_state)
        return reconstructed_state

    def _validate_cycle_number_range(self, cycle_number: int, issue_number: int) -> None:
        """Validate cycle_number is within valid range [1..total].

        Args:
            cycle_number: Cycle number to validate
            issue_number: GitHub issue number for context

        Raises:
            ValueError: If cycle_number is out of range or planning deliverables not found

        Issue #146 Cycle 2: Range validation for TDD cycle transitions.
        """
        # Get planning deliverables
        plan = self.project_manager.get_project_plan(issue_number)
        if not plan or "planning_deliverables" not in plan:
            msg = f"Planning deliverables not found for issue {issue_number}"
            raise ValueError(msg)

        # Get total cycles
        total_cycles = plan["planning_deliverables"]["tdd_cycles"]["total"]

        # Validate range [1..total]
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

    # -------------------------------------------------------------------------
    # Mode 2: Auto-recovery methods (Issue #39)
    # -------------------------------------------------------------------------

    def _reconstruct_branch_state(self, branch: str) -> BranchState:
        """Reconstruct branch state from deliverables.json + git commits.

        Mode 2: Cross-machine scenario - state.json missing after git pull.
        Automatically reconstructs state using:
        1. Issue number from branch name
        2. Workflow definition from deliverables.json
        3. Current phase from phase:label commits
        4. Parent branch from deliverables.json (Issue #79)

        Args:
            branch: Branch name (e.g., 'fix/39-test')

        Returns:
            Reconstructed state dict with reconstructed=True flag,
            includes parent_branch from deliverables.json

        Raises:
            ValueError: If branch format invalid or project not found
        """
        logger.info("Reconstructing state for branch '%s'...", branch)

        # Step 1: Extract issue number from branch
        issue_number = self._git_config.extract_issue_number(branch)
        if issue_number is None:
            msg = (
                f"Cannot extract issue number from branch '{branch}'. "
                "Expected format: <type>/<number>-<title>"
            )
            raise ValueError(msg)

        # Step 2: Get project plan (SSOT for workflow)
        project = self.project_manager.get_project_plan(issue_number)
        if not project:
            msg = f"Project plan not found for issue {issue_number}"
            raise ValueError(msg)

        # Step 3: Infer current phase from git commits
        workflow_phases = project["required_phases"]
        current_phase = self._infer_phase_from_git(branch, workflow_phases)

        # Step 4: Extract parent_branch from project
        parent_branch = project.get("parent_branch")

        state = BranchState(
            branch=branch,
            issue_number=issue_number,
            workflow_name=project["workflow_name"],
            current_phase=current_phase,
            current_cycle=None,
            last_cycle=None,
            cycle_history=[],
            required_phases=project.get("required_phases", workflow_phases),
            execution_mode=project.get("execution_mode", "normal"),
            issue_title=project.get("issue_title"),
            parent_branch=parent_branch,
            created_at=datetime.now(UTC).isoformat(),
            transitions=[],
            reconstructed=True,
        )

        logger.info(
            "Reconstructed state: issue=%s, phase=%s, workflow=%s, parent=%s",
            issue_number,
            current_phase,
            project["workflow_name"],
            parent_branch,
        )

        return state

    def _infer_phase_from_git(self, branch: str, workflow_phases: list[str]) -> str:
        """Infer current phase from git commit messages using ScopeDecoder.

        Parses Conventional Commits scope format (e.g., type(P_IMPLEMENTATION_SP_RED): msg)
        to extract the workflow phase. Falls back to the first workflow phase when no
        valid scope is found.

        Args:
            branch: Branch name
            workflow_phases: Valid phases from workflow definition

        Returns:
            Current phase (most recent valid scope-encoded phase, or first phase as fallback)
        """
        try:
            commits = self._get_git_commits(branch)
            for commit in commits:
                result = self._scope_decoder.detect_phase(commit, fallback_to_state=False)
                phase = result["workflow_phase"]
                if phase != "unknown" and phase in workflow_phases:
                    logger.info("Detected phase '%s' from git commits", phase)
                    return phase

        except RuntimeError as e:
            logger.warning("Git command failed during phase detection: %s", e)

        # Fallback: First phase of workflow
        fallback_phase = workflow_phases[0]
        logger.info("No valid phase detected, using fallback: %s", fallback_phase)
        return fallback_phase

    def _get_git_commits(self, branch: str, limit: int = 50) -> list[str]:
        """Get commit messages from git log for branch.

        Args:
            branch: Branch name
            limit: Maximum commits to retrieve

        Returns:
            List of commit messages (most recent first)

        Raises:
            RuntimeError: If git command fails
        """
        try:
            env = os.environ.copy()
            env.setdefault("GIT_TERMINAL_PROMPT", "0")
            env.setdefault("GIT_PAGER", "cat")
            env.setdefault("PAGER", "cat")

            result = subprocess.run(
                ["git", "log", f"--max-count={limit}", "--pretty=%s", branch],
                cwd=self.workspace_root,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=True,
                timeout=2,  # Short timeout to avoid blocking MCP (Issue #85)
                env=env,
            )
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]

        except subprocess.CalledProcessError as e:
            msg = f"Git log failed: {e.stderr}"
            raise RuntimeError(msg) from e
        except subprocess.TimeoutExpired as e:
            msg = "Git log command timed out"
            raise RuntimeError(msg) from e

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

    def _legacy_planning_exit_gate(self, branch: str, issue_number: int) -> None:
        """Hook called when exiting planning phase — hard gate (Issue #229, Option B).

        Reads exit_requires from workphases.yaml via WorkphasesConfig, checks that
        each required key exists in deliverables.json, and runs DeliverableChecker.check()
        on any ``validates`` entries declared directly under the key value.

        Args:
            branch: Branch name
            issue_number: GitHub issue number

        Raises:
            ValueError: If a required key is absent from the project plan
            DeliverableCheckError: If a validates entry fails structural checks
        """
        exit_requires = self._workphases_config.get_exit_requires("planning")

        if not exit_requires:
            logger.info(f"No exit_requires for planning phase; gate skipped for branch {branch}")
            return

        project_plan = self.project_manager.get_project_plan(issue_number)
        checker = DeliverableChecker(workspace_root=self.workspace_root)

        for requirement in exit_requires:
            key = requirement["key"]
            if not project_plan or key not in project_plan:
                msg = (
                    f"{key} not found for issue {issue_number}. "
                    f"Save {key} before leaving the planning phase."
                )
                raise ValueError(msg)

            # Run top-level validates entries declared directly under the key value
            plan_value = project_plan[key]
            if isinstance(plan_value, dict):
                for validate_spec in plan_value.get("validates", []):
                    checker.check(validate_spec.get("id", key), validate_spec)

                # Validate nested cycle deliverables validates specs
                tdd_cycles = plan_value.get("tdd_cycles", {})
                for cycle in tdd_cycles.get("cycles", []):
                    for deliverable in cycle.get("deliverables", []):
                        if not isinstance(deliverable, dict):
                            continue
                        if "validates" in deliverable:
                            checker.check(deliverable.get("id", "?"), deliverable["validates"])

                # Validate phase-key deliverables validates specs (design/validation/documentation)
                for phase_key in ("design", "validation", "documentation"):
                    phase_entry = plan_value.get(phase_key, {})
                    for deliverable in phase_entry.get("deliverables", []):
                        if not isinstance(deliverable, dict):
                            continue
                        if "validates" in deliverable:
                            checker.check(deliverable.get("id", "?"), deliverable["validates"])

        logger.info(f"Planning exit gate passed for branch {branch} (issue {issue_number})")

    def on_exit_research_phase(self, branch: str, issue_number: int) -> None:
        """Hook called when exiting research phase — file_glob gate (Issue #229 C6).

        Reads exit_requires from workphases.yaml for 'research'. For entries with
        ``type: file_glob``, interpolates ``{issue_number}`` and checks that at least
        one file matches the resulting glob pattern.

        Args:
            branch: Branch name
            issue_number: GitHub issue number

        Raises:
            DeliverableCheckError: If a file_glob gate finds no matching files.
            ValueError: If a key-type gate key is absent from deliverables.json.
        """
        exit_requires = self._workphases_config.get_exit_requires("research")

        if not exit_requires:
            logger.info(f"No exit_requires for research phase; gate skipped for branch {branch}")
            return

        for requirement in exit_requires:
            req_type = requirement.get("type", "key")
            if req_type == "file_glob":
                pattern = requirement["file"].format(issue_number=issue_number)
                matches = list(self.workspace_root.glob(pattern))
                if not matches:
                    description = requirement.get("description", f"file_glob: {pattern}")
                    raise DeliverableCheckError(
                        f"[research.exit_requires] {description}: "
                        f"no files matching '{pattern}' in workspace root"
                    )
            else:
                key = requirement["key"]
                plan = self.project_manager.get_project_plan(issue_number)
                if not plan or key not in plan:
                    msg = (
                        f"{key} not found for issue {issue_number}. "
                        f"Save {key} before leaving the research phase."
                    )
                    raise ValueError(msg)

        logger.info(f"Research exit gate passed for branch {branch} (issue {issue_number})")

    def on_exit_design_phase(self, branch: str, issue_number: int) -> None:
        """Hook called when exiting design phase — per-phase deliverable gate (Issue #229 C7).

        Reads ``planning_deliverables.design.deliverables`` from state.json. For entries
        that include a ``validates`` spec, runs ``DeliverableChecker.check()``.
        Gate is optional: if no design key is present, the check is skipped silently.

        Args:
            branch: Branch name
            issue_number: GitHub issue number

        Raises:
            DeliverableCheckError: If a validates spec is not satisfied.
        """
        plan = self.project_manager.get_project_plan(issue_number)
        phase_delivs: dict[str, Any] = (
            (plan or {}).get("planning_deliverables", {}).get("design", {})
        )
        deliverables: list[dict[str, Any]] = phase_delivs.get("deliverables", [])

        if not deliverables:
            logger.info(f"No design deliverables gate defined; skipped for branch {branch}")
            return

        checker = DeliverableChecker(workspace_root=self.workspace_root)
        for deliverable in deliverables:
            if "validates" in deliverable:
                checker.check(deliverable["id"], deliverable["validates"])

        logger.info(f"Design exit gate passed for branch {branch} (issue {issue_number})")

    def on_exit_validation_phase(self, branch: str, issue_number: int) -> None:
        """Hook called when exiting validation phase — per-phase deliverable gate (Issue #229 C9).

        Reads ``planning_deliverables.validation.deliverables`` from state.json. For entries
        that include a ``validates`` spec, runs ``DeliverableChecker.check()``.
        Gate is optional: if no validation key is present, the check is skipped silently.

        Args:
            branch: Branch name
            issue_number: GitHub issue number

        Raises:
            DeliverableCheckError: If a validates spec is not satisfied.
        """
        plan = self.project_manager.get_project_plan(issue_number)
        phase_delivs: dict[str, Any] = (
            (plan or {}).get("planning_deliverables", {}).get("validation", {})
        )
        deliverables: list[dict[str, Any]] = phase_delivs.get("deliverables", [])

        if not deliverables:
            logger.info(f"No validation deliverables gate defined; skipped for branch {branch}")
            return

        checker = DeliverableChecker(workspace_root=self.workspace_root)
        for deliverable in deliverables:
            if "validates" in deliverable:
                checker.check(deliverable["id"], deliverable["validates"])

        logger.info(f"Validation exit gate passed for branch {branch} (issue {issue_number})")

    def on_exit_documentation_phase(self, branch: str, issue_number: int) -> None:
        """Hook called when exiting documentation phase — deliverable gate (Issue #229 C9).

        Reads ``planning_deliverables.documentation.deliverables`` from state.json. For entries
        that include a ``validates`` spec, runs ``DeliverableChecker.check()``.
        Gate is optional: if no documentation key is present, the check is skipped silently.

        Args:
            branch: Branch name
            issue_number: GitHub issue number

        Raises:
            DeliverableCheckError: If a validates spec is not satisfied.
        """
        plan = self.project_manager.get_project_plan(issue_number)
        phase_delivs: dict[str, Any] = (
            (plan or {}).get("planning_deliverables", {}).get("documentation", {})
        )
        deliverables: list[dict[str, Any]] = phase_delivs.get("deliverables", [])

        if not deliverables:
            logger.info(f"No documentation deliverables gate defined; skipped for branch {branch}")
            return

        checker = DeliverableChecker(workspace_root=self.workspace_root)
        for deliverable in deliverables:
            if "validates" in deliverable:
                checker.check(deliverable["id"], deliverable["validates"])

        logger.info(f"Documentation exit gate passed for branch {branch} (issue {issue_number})")

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
