"""PhaseStateEngine - Workflow-based phase state and transition management.

Issue #50: Integrated with workflows.yaml for transition validation.
Manages branch phase state with strict sequential validation and forced transitions.
"""
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp_server.config.workflows import workflow_config
from mcp_server.managers.project_manager import ProjectManager


@dataclass
class TransitionRecord:
    """Single phase transition record."""

    from_phase: str
    to_phase: str
    timestamp: str
    human_approval: str | None
    forced: bool
    skip_reason: str | None = None


class PhaseStateEngine:
    """Manages phase state and transitions with workflow validation.

    Validates transitions against workflows.yaml definitions.
    Supports both strict sequential and forced (non-sequential) transitions.
    """

    def __init__(self, workspace_root: Path | str, project_manager: ProjectManager):
        """Initialize PhaseStateEngine.

        Args:
            workspace_root: Path to workspace root directory
            project_manager: ProjectManager instance for workflow lookup
        """
        self.workspace_root = Path(workspace_root)
        self.state_file = self.workspace_root / ".st3" / "state.json"
        self.project_manager = project_manager

    def initialize_branch(
        self, branch: str, issue_number: int, initial_phase: str
    ) -> dict[str, Any]:
        """Initialize branch state with workflow caching.

        Args:
            branch: Branch name (e.g., 'feature/42-test')
            issue_number: GitHub issue number
            initial_phase: Starting phase

        Returns:
            dict with success status and branch state
        """
        # Get project plan to cache workflow_name
        project = self.project_manager.get_project_plan(issue_number)
        if not project:
            msg = f"Project {issue_number} not found. Initialize project first."
            raise ValueError(msg)

        # Create initial state
        state = {
            "branch": branch,
            "issue_number": issue_number,
            "workflow_name": project["workflow_name"],  # Cache for performance
            "current_phase": initial_phase,
            "transitions": [],
            "created_at": datetime.now(UTC).isoformat()
        }

        # Save state
        self._save_state(branch, state)

        return {"success": True, "branch": branch, "current_phase": initial_phase}

    def transition(
        self, branch: str, to_phase: str, human_approval: str | None = None
    ) -> dict[str, Any]:
        """Execute strict sequential phase transition.

        Validates transition against workflow definition via workflow_config.

        Args:
            branch: Branch name
            to_phase: Target phase
            human_approval: Optional human approval message

        Returns:
            dict with success, from_phase, to_phase

        Raises:
            ValueError: If transition is invalid per workflow
        """
        # Get current state
        state = self.get_state(branch)
        from_phase: str = state["current_phase"]
        workflow_name: str = state["workflow_name"]

        # Validate transition via workflow_config (strict sequential)
        workflow_config.validate_transition(workflow_name, from_phase, to_phase)

        # Record transition (forced=False)
        transition = TransitionRecord(
            from_phase=from_phase,
            to_phase=to_phase,
            timestamp=datetime.now(UTC).isoformat(),
            human_approval=human_approval,
            forced=False
        )

        # Update state
        state["current_phase"] = to_phase
        state["transitions"].append(self._transition_to_dict(transition))
        self._save_state(branch, state)

        return {
            "success": True,
            "from_phase": from_phase,
            "to_phase": to_phase
        }

    def force_transition(
        self,
        branch: str,
        to_phase: str,
        skip_reason: str,
        human_approval: str
    ) -> dict[str, Any]:
        """Execute forced (non-sequential) phase transition.

        Bypasses workflow validation. Requires explicit skip_reason.

        Args:
            branch: Branch name
            to_phase: Target phase
            skip_reason: Reason for skipping validation
            human_approval: Required human approval message

        Returns:
            dict with success, from_phase, to_phase, forced, skip_reason
        """
        # Get current state (no validation)
        state = self.get_state(branch)
        from_phase: str = state["current_phase"]

        # Record forced transition (forced=True)
        transition = TransitionRecord(
            from_phase=from_phase,
            to_phase=to_phase,
            timestamp=datetime.now(UTC).isoformat(),
            human_approval=human_approval,
            forced=True,
            skip_reason=skip_reason
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
            "skip_reason": skip_reason
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
        """Get full state for branch.

        Args:
            branch: Branch name

        Returns:
            Branch state dict with workflow_name, current_phase, transitions

        Raises:
            ValueError: If branch state not found
        """
        if not self.state_file.exists():
            msg = f"State file not found. Initialize branch '{branch}' first."
            raise ValueError(msg)

        states: dict[str, Any] = json.loads(self.state_file.read_text())
        state: dict[str, Any] | None = states.get(branch)

        if not state:
            msg = f"Branch '{branch}' not found. Initialize branch first."
            raise ValueError(msg)

        return state

    def _save_state(self, branch: str, state: dict[str, Any]) -> None:
        """Save branch state to state.json.

        Args:
            branch: Branch name
            state: State dict to save
        """
        # Ensure .st3 directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing states
        if self.state_file.exists():
            states = json.loads(self.state_file.read_text())
        else:
            states = {}

        # Update branch state
        states[branch] = state

        # Write to file
        self.state_file.write_text(json.dumps(states, indent=2))

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
            "skip_reason": transition.skip_reason
        }
