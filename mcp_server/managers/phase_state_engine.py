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
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

# Project modules
from mcp_server.config.workflows import workflow_config
from mcp_server.config.workphases_config import WorkphasesConfig
from mcp_server.managers.deliverable_checker import DeliverableChecker
from mcp_server.managers.project_manager import ProjectManager

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

    def __init__(self, workspace_root: Path | str, project_manager: ProjectManager) -> None:
        """Initialize PhaseStateEngine.

        Args:
            workspace_root: Path to workspace root directory
            project_manager: ProjectManager for workflow lookup
        """
        self.workspace_root = Path(workspace_root)
        self.state_file = self.workspace_root / ".st3" / "state.json"
        self.project_manager = project_manager

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

        # Create initial state
        state: dict[str, Any] = {
            "branch": branch,
            "issue_number": issue_number,
            "workflow_name": project["workflow_name"],  # Cache for performance
            "current_phase": initial_phase,
            "parent_branch": parent_branch,  # Store parent_branch
            "transitions": [],
            "created_at": datetime.now(UTC).isoformat(),
            # TDD cycle tracking fields (Issue #146)
            "current_tdd_cycle": None,
            "last_tdd_cycle": None,
            "tdd_cycle_history": [],
        }
        # Save state
        self._save_state(branch, state)

        return {
            "success": True,
            "branch": branch,
            "current_phase": initial_phase,
            "parent_branch": parent_branch,
        }

    def transition(
        self, branch: str, to_phase: str, human_approval: str | None = None
    ) -> dict[str, Any]:
        """Execute strict sequential phase transition.

        Validates transition against workflow via workflow_config.validate_transition().

        Args:
            branch: Branch name
            to_phase: Target phase
            human_approval: Optional approval message

        Returns:
            dict with success, from_phase, to_phase

        Raises:
            ValueError: If transition invalid per workflow
        """
        # Get current state
        state = self.get_state(branch)
        from_phase: str = state["current_phase"]
        workflow_name: str = state["workflow_name"]

        # Validate transition via workflow_config (strict sequential)
        workflow_config.validate_transition(workflow_name, from_phase, to_phase)

        # Planning exit hook: called when leaving planning phase (Issue #229)
        if from_phase == "planning":
            issue_number_exit: int = state["issue_number"]
            self.on_exit_planning_phase(branch, issue_number_exit)

        # TDD exit hook: called when leaving TDD phase (Issue #146)
        if from_phase == "tdd":
            self.on_exit_tdd_phase(branch)
            # Reload state after hook (hook may have modified state)
            state = self.get_state(branch)

        # Record transition (forced=False)
        transition = TransitionRecord(
            from_phase=from_phase,
            to_phase=to_phase,
            timestamp=datetime.now(UTC).isoformat(),
            human_approval=human_approval,
            forced=False,
        )

        # Update state
        state["current_phase"] = to_phase
        state["transitions"].append(self._transition_to_dict(transition))
        self._save_state(branch, state)

        # TDD entry hook: called when entering TDD phase (Issue #146)
        if to_phase == "tdd":
            issue_number: int = state["issue_number"]
            self.on_enter_tdd_phase(branch, issue_number)

        return {"success": True, "from_phase": from_phase, "to_phase": to_phase}

    def force_transition(
        self, branch: str, to_phase: str, skip_reason: str, human_approval: str
    ) -> dict[str, Any]:
        """Execute forced non-sequential phase transition.

        Bypasses workflow validation. Requires explicit skip_reason for audit.

        Args:
            branch: Branch name
            to_phase: Target phase
            skip_reason: Reason for bypassing validation
            human_approval: Required approval message

        Returns:
            dict with success, from_phase, to_phase, forced, skip_reason
        """
        # Get current state (no validation)
        state = self.get_state(branch)
        from_phase: str = state["current_phase"]

        # Warn about skipped gates (GAP-03)
        # Only warn when the deliverable key is actually absent from projects.json.
        workphases_path = self.workspace_root / ".st3" / "workphases.yaml"
        skipped_gates: list[str] = []
        if workphases_path.exists():
            issue_number: int = state["issue_number"]
            plan = self.project_manager.get_project_plan(issue_number)
            wp_config = WorkphasesConfig(workphases_path)
            for entry in wp_config.get_exit_requires(from_phase):
                key = entry["key"]
                if plan is None or key not in plan:
                    skipped_gates.append(f"exit:{from_phase}:{key}")
            for entry in wp_config.get_entry_expects(to_phase):
                key = entry["key"]
                if plan is None or key not in plan:
                    skipped_gates.append(f"entry:{to_phase}:{key}")
            if skipped_gates:
                logger.warning(
                    "force_transition skipped_gates=%s (from=%s, to=%s, skip_reason=%r)",
                    skipped_gates,
                    from_phase,
                    to_phase,
                    skip_reason,
                )

        # Record forced transition (forced=True)
        transition = TransitionRecord(
            from_phase=from_phase,
            to_phase=to_phase,
            timestamp=datetime.now(UTC).isoformat(),
            human_approval=human_approval,
            forced=True,
            skip_reason=skip_reason,
        )

        # Update state
        state["current_phase"] = to_phase
        state["transitions"].append(self._transition_to_dict(transition))
        self._save_state(branch, state)

        return {
            "success": True,
            "from_phase": from_phase,
            "to_phase": to_phase,
            "forced": True,
            "skip_reason": skip_reason,
            "skipped_gates": skipped_gates,
        }

    def get_current_phase(self, branch: str) -> str:
        """Get current phase for branch.

        Args:
            branch: Branch name

        Returns:
            Current phase name
        """
        state = self.get_state(branch)
        current: str = state["current_phase"]
        return current

    def get_state(self, branch: str) -> dict[str, Any]:
        """Get full state for branch with auto-recovery.

        Mode 2 Enhancement: Automatically reconstructs state from projects.json
        + git commits when state.json is missing/empty or branch doesn't match current.

        Args:
            branch: Branch name

        Returns:
            Branch state with workflow_name, current_phase, transitions

        Raises:
            ValueError: If auto-recovery fails (invalid branch, missing project)
        """
        # Check if state.json exists, is not empty, and matches requested branch
        if self.state_file.exists():
            content = self.state_file.read_text(encoding="utf-8").strip()
            if content:
                try:
                    state = cast(dict[str, Any], json.loads(content))
                    if state.get("branch") == branch:
                        return state
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON in state.json, reconstructing")

        # State doesn't exist/empty/invalid or is for different branch - reconstruct
        state = self._reconstruct_branch_state(branch)
        self._save_state(branch, state)
        return state

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

    def _save_state(self, branch: str, state: dict[str, Any]) -> None:
        """Save branch state to state.json.

        Overwrites state.json with only the current branch state.
        Uses atomic write (temp file + rename) to avoid file locking issues
        on Windows (Issue #85).

        Args:
            branch: Branch name
            state: State dict to save
        """
        # Ensure .st3 directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        state["branch"] = branch

        # Atomic write: write to temp file then rename (avoids locking issues)
        content = json.dumps(state, indent=2)
        temp_file = self.state_file.parent / ".state.tmp"
        try:
            temp_file.write_text(content, encoding="utf-8")
            # On Windows, need to remove target first if it exists
            if self.state_file.exists():
                self.state_file.unlink()
            temp_file.rename(self.state_file)
        except OSError:
            # Fallback: direct write if atomic fails
            temp_file.unlink(missing_ok=True)
            self.state_file.write_text(content, encoding="utf-8")

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

    def _reconstruct_branch_state(self, branch: str) -> dict[str, Any]:
        """Reconstruct branch state from projects.json + git commits.

        Mode 2: Cross-machine scenario - state.json missing after git pull.
        Automatically reconstructs state using:
        1. Issue number from branch name
        2. Workflow definition from projects.json
        3. Current phase from phase:label commits
        4. Parent branch from projects.json (Issue #79)

        Args:
            branch: Branch name (e.g., 'fix/39-test')

        Returns:
            Reconstructed state dict with reconstructed=True flag,
            includes parent_branch from projects.json

        Raises:
            ValueError: If branch format invalid or project not found
        """
        logger.info("Reconstructing state for branch '%s'...", branch)

        # Step 1: Extract issue number from branch
        issue_number = self._extract_issue_from_branch(branch)

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

        # Step 5: Create reconstructed state
        state: dict[str, Any] = {
            "branch": branch,
            "issue_number": issue_number,
            "workflow_name": project["workflow_name"],
            "current_phase": current_phase,
            "parent_branch": parent_branch,  # Reconstructed from projects.json
            "transitions": [],  # Cannot reconstruct history
            "created_at": datetime.now(UTC).isoformat(),
            "reconstructed": True,  # Audit flag
            # TDD cycle tracking fields (Issue #146)
            "current_tdd_cycle": None,
            "last_tdd_cycle": None,
            "tdd_cycle_history": [],
        }

        logger.info(
            "Reconstructed state: issue=%s, phase=%s, workflow=%s, parent=%s",
            issue_number,
            current_phase,
            project["workflow_name"],
            parent_branch,
        )

        return state

    def _extract_issue_from_branch(self, branch: str) -> int:
        """Extract issue number from branch name.

        Supports formats: feature/N-title, fix/N-title, etc.

        Args:
            branch: Branch name

        Returns:
            Issue number

        Raises:
            ValueError: If branch format invalid
        """
        # Match: (feature|fix|bug|docs|refactor|hotfix|epic)/(\d+)-(.+)
        match = re.match(r"^(?:feature|fix|bug|docs|refactor|hotfix|epic)/(\d+)-", branch)
        if not match:
            msg = f"Cannot extract issue number from branch '{branch}'. "
            msg += "Expected format: <type>/<number>-<title>"
            raise ValueError(msg)

        return int(match.group(1))

    def _infer_phase_from_git(self, branch: str, workflow_phases: list[str]) -> str:
        """Infer current phase from git commit messages.

        Searches for phase:label patterns in commits, validates against workflow.

        Args:
            branch: Branch name
            workflow_phases: Valid phases from workflow definition

        Returns:
            Current phase (most recent valid phase:label or first phase)
        """
        try:
            commits = self._get_git_commits(branch)
            detected_phase = self._detect_phase_label(commits, workflow_phases)

            if detected_phase:
                logger.info("Detected phase '%s' from git commits", detected_phase)
                return detected_phase

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

    def _detect_phase_label(self, commits: list[str], workflow_phases: list[str]) -> str | None:
        """Detect phase from phase:label patterns in commits.

        Labels.yaml SSOT: Only phase:label format supported (no backwards compat).
        Handles TDD granularity: phase:red/green/refactor → 'tdd' in workflow.

        Args:
            commits: List of commit messages (most recent first)
            workflow_phases: Valid phases from workflow

        Returns:
            Detected phase or None if no valid labels found
        """
        # TDD labels that map to 'tdd' phase
        tdd_labels = {"red", "green", "refactor"}

        for commit in commits:
            # Search for phase:label pattern (case-insensitive)
            match = re.search(r"phase:(\w+)", commit.lower())
            if not match:
                continue

            detected_label = match.group(1)

            # Handle TDD granularity
            if detected_label in tdd_labels:
                if "tdd" in workflow_phases:
                    return "tdd"
                continue

            # Direct phase match
            if detected_label in workflow_phases:
                return detected_label

        return None

    def on_enter_tdd_phase(self, branch: str, issue_number: int) -> None:
        """Hook called when entering TDD phase.

        Auto-initializes TDD cycle 1 in branch state. Planning deliverables
        are validated at planning exit (on_exit_planning_phase) — not here.

        Args:
            branch: Branch name
            issue_number: GitHub issue number
        """
        # Get or create state
        state = self.get_state(branch)

        # Auto-initialize cycle 1 if not already set
        if state.get("current_tdd_cycle") is None:
            state["current_tdd_cycle"] = 1
            state["last_tdd_cycle"] = 0
            if "tdd_cycle_history" not in state:
                state["tdd_cycle_history"] = []

            # Save state
            self._save_state(branch, state)

        logger.info(f"Entered TDD phase for issue {issue_number} on branch {branch}")

    def on_exit_planning_phase(self, branch: str, issue_number: int) -> None:
        """Hook called when exiting planning phase — hard gate (Issue #229, Option B).

        Reads exit_requires from workphases.yaml via WorkphasesConfig, checks that
        each required key exists in projects.json, and runs DeliverableChecker.check()
        on any ``validates`` entries declared directly under the key value.

        Args:
            branch: Branch name
            issue_number: GitHub issue number

        Raises:
            ValueError: If a required key is absent from the project plan
            DeliverableCheckError: If a validates entry fails structural checks
        """
        workphases_path = self.workspace_root / ".st3" / "workphases.yaml"
        wp_config = WorkphasesConfig(workphases_path)
        exit_requires = wp_config.get_exit_requires("planning")

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

        logger.info(f"Planning exit gate passed for branch {branch} (issue {issue_number})")

    def on_exit_tdd_phase(self, branch: str) -> None:
        """Hook called when exiting TDD phase.

        Preserves last_tdd_cycle and clears current_tdd_cycle.
        Logs warning if not all cycles completed.

        Args:
            branch: Branch name
        """
        # Get current state
        state = self.get_state(branch)
        current_cycle = state.get("current_tdd_cycle")

        # Preserve last cycle
        if current_cycle is not None:
            state["last_tdd_cycle"] = current_cycle
            state["current_tdd_cycle"] = None

            # Log warning if incomplete (optional validation)
            # For now, we allow exit but log it
            logger.info(f"Exited TDD phase at cycle {current_cycle} on branch {branch}")

            # Save state
            self._save_state(branch, state)
