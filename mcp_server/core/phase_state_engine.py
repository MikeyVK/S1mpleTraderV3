# mcp_server/core/phase_state_engine.py
"""
PhaseStateEngine for branch phase state management.

Phase A.2: Track current phase per branch and validate transitions.

@layer: Core
@dependencies: [ProjectManager]
"""
# pyright: reportCallIssue=false
# pylint: disable=import-outside-toplevel
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


@dataclass
class TransitionResult:
    """Result of a phase transition attempt."""

    success: bool
    new_phase: str | None = None
    reason: str = ""


@dataclass
class PhaseTransition:
    """Record of a phase transition."""

    from_phase: str
    to_phase: str
    timestamp: str
    human_approval: str | None = None


@dataclass
class BranchState:
    """State for a single branch."""

    current_phase: str
    issue_number: int
    transitions: list[dict[str, Any]] = field(default_factory=list)


class PhaseStateEngine:
    """Engine for managing phase state per branch."""

    def __init__(self, workspace_root: Path | str) -> None:
        """Initialize the phase state engine.

        Args:
            workspace_root: Path to workspace root directory
        """
        self.workspace_root = Path(workspace_root)
        self.state_file = self.workspace_root / ".st3" / "state.json"
        self._state: dict[str, BranchState] = {}
        self._load_state()

    def get_phase(self, branch: str) -> str | None:
        """Get current phase for a branch.

        Args:
            branch: Branch name

        Returns:
            Current phase or None if branch not initialized
        """
        if branch not in self._state:
            return None
        return self._state[branch].current_phase

    def initialize_branch(
        self, branch: str, initial_phase: str, issue_number: int
    ) -> bool:
        """Initialize a new branch with phase tracking.

        Args:
            branch: Branch name
            initial_phase: Starting phase
            issue_number: Linked GitHub issue number

        Returns:
            True if initialized, False if already exists
        """
        if branch in self._state:
            return False

        self._state[branch] = BranchState(
            current_phase=initial_phase,
            issue_number=issue_number,
            transitions=[]
        )
        self._save_state()
        return True

    def get_issue_for_branch(self, branch: str) -> int | None:
        """Get issue number linked to a branch.

        Args:
            branch: Branch name

        Returns:
            Issue number or None if not found
        """
        if branch not in self._state:
            return None
        return self._state[branch].issue_number

    def transition(
        self,
        branch: str,
        from_phase: str,
        to_phase: str,
        human_approval: str | None = None
    ) -> TransitionResult:
        """Transition branch to new phase.

        Args:
            branch: Branch name
            from_phase: Expected current phase
            to_phase: Target phase
            human_approval: Optional approval message

        Returns:
            TransitionResult with success status
        """
        # Check if branch exists
        if branch not in self._state:
            return TransitionResult(
                success=False,
                reason=f"Branch '{branch}' not initialized"
            )

        state = self._state[branch]

        # Validate from_phase matches current
        if state.current_phase != from_phase:
            return TransitionResult(
                success=False,
                reason=f"Phase mismatch: expected '{from_phase}', "
                       f"current is '{state.current_phase}'"
            )

        # Record transition
        transition_record = {
            "from_phase": from_phase,
            "to_phase": to_phase,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if human_approval:
            transition_record["human_approval"] = human_approval

        state.transitions.append(transition_record)
        state.current_phase = to_phase
        self._save_state()

        return TransitionResult(success=True, new_phase=to_phase)

    def get_transition_history(self, branch: str) -> list[dict[str, Any]]:
        """Get transition history for a branch.

        Args:
            branch: Branch name

        Returns:
            List of transition records
        """
        if branch not in self._state:
            return []
        return self._state[branch].transitions

    def get_project_plan(self, branch: str) -> dict[str, Any] | None:
        """Get project plan for a branch via issue mapping.

        Args:
            branch: Branch name

        Returns:
            Project plan dict or None if not found
        """
        issue_number = self.get_issue_for_branch(branch)
        if not issue_number:
            return None

        # Import here to avoid circular dependency at module load time
        from mcp_server.managers.project_manager import ProjectManager

        manager = ProjectManager(workspace_root=self.workspace_root)
        return manager.get_project_plan(issue_number)

    def _load_state(self) -> None:
        """Load state from .st3/state.json."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file, encoding="utf-8") as f:
                data = json.load(f)

            # Deserialize into BranchState objects
            for branch, branch_data in data.items():
                self._state[branch] = BranchState(
                    current_phase=branch_data["current_phase"],
                    issue_number=branch_data["issue_number"],
                    transitions=branch_data.get("transitions", [])
                )
        except (OSError, json.JSONDecodeError, KeyError):
            # If state file is corrupted, start fresh
            self._state = {}

    def _save_state(self) -> None:
        """Save state to .st3/state.json atomically."""
        # Ensure .st3 directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Serialize BranchState objects
        data = {
            branch: {
                "current_phase": state.current_phase,
                "issue_number": state.issue_number,
                "transitions": state.transitions
            }
            for branch, state in self._state.items()
        }

        # Atomic write: write to temp file, then rename
        temp_file = self.state_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.state_file)
        except OSError:
            if temp_file.exists():
                temp_file.unlink()
            raise
