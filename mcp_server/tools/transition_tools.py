"""Transition tools for TDD cycle management.

Issue #146 Cycle 4: transition_cycle and force_cycle_transition tools.
"""

import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from mcp_server.config.settings import settings
from mcp_server.managers.deliverable_checker import DeliverableChecker
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class TransitionCycleInput(BaseModel):
    """Input for transition_cycle tool."""

    to_cycle: int = Field(..., description="Target cycle number (forward-only)")
    issue_number: int | None = Field(
        default=None, description="Issue number (auto-detected from branch if omitted)"
    )


class TransitionCycleTool(BaseTool):
    """Tool to transition to next TDD cycle with validation."""

    name = "transition_cycle"
    description = (
        "Transition to next TDD cycle (forward-only, sequential). "
        "Use force_cycle_transition to skip cycles or go backwards."
    )
    args_model = TransitionCycleInput

    async def execute(self, params: TransitionCycleInput) -> ToolResult:
        """Execute cycle transition with validation."""
        try:
            # Get workspace root
            workspace_root = Path(settings.server.workspace_root)

            # Auto-detect issue number from branch if not provided
            git_manager = GitManager()
            branch = git_manager.get_current_branch()

            issue_number = params.issue_number
            if issue_number is None:
                issue_number = self._extract_issue_number(branch)
                if issue_number is None:
                    return ToolResult.error("Cannot detect issue number from branch")

            # Initialize managers
            project_manager = ProjectManager(workspace_root=workspace_root)
            state_engine = PhaseStateEngine(
                workspace_root=workspace_root, project_manager=project_manager
            )

            # Get current state
            state = state_engine.get_state(branch)
            current_phase = state.get("current_phase")
            current_cycle = state.get("current_tdd_cycle")

            # Validation 1: Check TDD phase
            if current_phase != "tdd":
                return ToolResult.error(
                    f"Not in TDD phase (current: {current_phase}). "
                    "Cycle transitions only allowed during TDD phase."
                )

            # Validation 2: Check planning deliverables exist
            project_plan = project_manager.get_project_plan(issue_number)
            if project_plan is None:
                return ToolResult.error("Project plan not found")

            planning_deliverables = project_plan.get("planning_deliverables")
            if not planning_deliverables:
                return ToolResult.error(
                    "Planning deliverables not found. "
                    "Create planning deliverables before transitioning cycles."
                )

            tdd_cycles = planning_deliverables.get("tdd_cycles", {})
            total_cycles = tdd_cycles.get("total", 0)

            # Validation 3: Check valid cycle range
            if params.to_cycle < 1 or params.to_cycle > total_cycles:
                return ToolResult.error(
                    f"Invalid cycle number {params.to_cycle}. Valid range: 1-{total_cycles}"
                )

            # Validation 4: Check forward-only
            if current_cycle is not None and params.to_cycle <= current_cycle:
                return ToolResult.error(
                    f"Backwards transition not allowed (current: {current_cycle}, "
                    f"target: {params.to_cycle}). "
                    "Use force_cycle_transition for backwards transitions."
                )

            # Validation 5: Check sequential
            if current_cycle is not None and params.to_cycle != current_cycle + 1:
                return ToolResult.error(
                    f"Non-sequential transition not allowed (current: {current_cycle}, "
                    f"target: {params.to_cycle}). "
                    "Use force_cycle_transition to skip cycles."
                )

            # Validation 6: Check exit criteria of current cycle
            if current_cycle is not None:
                cycles_list = tdd_cycles.get("cycles", [])
                current_cycle_data = next(
                    (c for c in cycles_list if c.get("cycle_number") == current_cycle), None
                )
                if current_cycle_data is not None:
                    exit_criteria = current_cycle_data.get("exit_criteria", "")
                    if not exit_criteria or not exit_criteria.strip():
                        return ToolResult.error(
                            f"Cycle {current_cycle} exit criteria not defined. "
                            "Define exit_criteria in planning deliverables before transitioning."
                        )

            # Execute transition
            from_cycle = current_cycle or 0
            state["last_tdd_cycle"] = from_cycle
            state["current_tdd_cycle"] = params.to_cycle

            # Update history (if not exists, create empty list)
            if "tdd_cycle_history" not in state:
                state["tdd_cycle_history"] = []

            history_entry = {
                "cycle_number": params.to_cycle,
                "forced": False,
                "entered": datetime.now(UTC).isoformat(),
            }
            state["tdd_cycle_history"].append(history_entry)

            # Save state
            state_engine._save_state(branch, state)

            # Get cycle name for message
            cycles = tdd_cycles.get("cycles", [])
            cycle_details = next(
                (c for c in cycles if c.get("cycle_number") == params.to_cycle), None
            )
            cycle_name = cycle_details.get("name") if cycle_details else "Unknown"

            # Success message
            message = f"✅ Transitioned to TDD Cycle {params.to_cycle}/{total_cycles}: {cycle_name}"

            return ToolResult.text(message)

        except (OSError, ValueError, RuntimeError, KeyError) as e:
            return ToolResult.error(f"Transition failed: {e}")

    def _extract_issue_number(self, branch: str) -> int | None:
        """Extract issue number from branch name."""
        patterns = [
            r"(?:feature|fix|refactor|docs)/(\d+)-",
            r"issue-(\d+)",
            r"#(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, branch)
            if match:
                return int(match.group(1))

        return None


class ForceCycleTransitionInput(BaseModel):
    """Input for force_cycle_transition tool."""

    to_cycle: int = Field(..., description="Target cycle number (any direction)")
    skip_reason: str = Field(..., description="Reason for forced transition (backward/skip)")
    human_approval: str = Field(
        ..., description="Human approval (name + date, e.g., 'John approved on 2026-02-17')"
    )
    issue_number: int | None = Field(
        default=None, description="Issue number (auto-detected from branch if omitted)"
    )


class ForceCycleTransitionTool(BaseTool):
    """Tool to force TDD cycle transition (backward/skip) with human approval."""

    name = "force_cycle_transition"
    description = (
        "Force transition to any TDD cycle (backward or skip). "
        "Requires skip_reason and human_approval for audit trail."
    )
    args_model = ForceCycleTransitionInput

    async def execute(self, params: ForceCycleTransitionInput) -> ToolResult:
        """Execute forced cycle transition with audit trail."""
        try:
            # Validation 1: Check skip_reason not empty
            if not params.skip_reason or params.skip_reason.strip() == "":
                return ToolResult.error(
                    "skip_reason is required for forced transitions. "
                    "Provide justification for backward/skip transition."
                )

            # Validation 2: Check human_approval not empty
            if not params.human_approval or params.human_approval.strip() == "":
                return ToolResult.error(
                    "human_approval is required for forced transitions. "
                    "Provide approval (e.g., 'John approved on 2026-02-17')."
                )

            # Get workspace root
            workspace_root = Path(settings.server.workspace_root)

            # Auto-detect issue number from branch if not provided
            git_manager = GitManager()
            branch = git_manager.get_current_branch()

            issue_number = params.issue_number
            if issue_number is None:
                issue_number = TransitionCycleTool()._extract_issue_number(branch)
                if issue_number is None:
                    return ToolResult.error("Cannot detect issue number from branch")

            # Initialize managers
            project_manager = ProjectManager(workspace_root=workspace_root)
            state_engine = PhaseStateEngine(
                workspace_root=workspace_root, project_manager=project_manager
            )

            # Get current state
            state = state_engine.get_state(branch)
            current_phase = state.get("current_phase")
            current_cycle = state.get("current_tdd_cycle")

            # Validation 3: Check TDD phase
            if current_phase != "tdd":
                return ToolResult.error(
                    f"Not in TDD phase (current: {current_phase}). "
                    "Cycle transitions only allowed during TDD phase."
                )

            # Validation 4: Check planning deliverables exist
            project_plan = project_manager.get_project_plan(issue_number)
            if project_plan is None:
                return ToolResult.error("Project plan not found")

            planning_deliverables = project_plan.get("planning_deliverables")
            if not planning_deliverables:
                return ToolResult.error(
                    "Planning deliverables not found. "
                    "Create planning deliverables before transitioning cycles."
                )

            tdd_cycles = planning_deliverables.get("tdd_cycles", {})
            total_cycles = tdd_cycles.get("total", 0)

            # Validation 5: Check valid cycle range
            if params.to_cycle < 1 or params.to_cycle > total_cycles:
                return ToolResult.error(
                    f"Invalid cycle number {params.to_cycle}. Valid range: 1-{total_cycles}"
                )

            # Execute forced transition
            from_cycle = current_cycle or 0
            state["last_tdd_cycle"] = from_cycle
            state["current_tdd_cycle"] = params.to_cycle

            # Get cycle name (needed for audit entry)
            cycles = tdd_cycles.get("cycles", [])
            cycle_details = next(
                (c for c in cycles if c.get("cycle_number") == params.to_cycle), None
            )
            cycle_name = cycle_details.get("name") if cycle_details else "Unknown"

            # Create audit trail entry (spec: cycle_number, forced, skipped_cycles)
            if "tdd_cycle_history" not in state:
                state["tdd_cycle_history"] = []

            skipped_cycles = list(
                range(min(from_cycle, params.to_cycle) + 1, max(from_cycle, params.to_cycle))
            )
            audit_entry = {
                "cycle_number": params.to_cycle,
                "name": cycle_name,
                "entered": datetime.now(UTC).isoformat(),
                "forced": True,
                "skip_reason": params.skip_reason,
                "human_approval": params.human_approval,
                "skipped_cycles": skipped_cycles,
            }
            state["tdd_cycle_history"].append(audit_entry)

            # Save state
            state_engine._save_state(branch, state)

            # Check deliverables in skipped cycles: split blocking vs validated (C10/GAP-17)
            checker = DeliverableChecker(workspace_root=workspace_root)
            unvalidated: list[str] = []
            validated: list[str] = []
            for cycle_num in skipped_cycles:
                cycle_data = next((c for c in cycles if c.get("cycle_number") == cycle_num), None)
                if cycle_data is None:
                    continue
                for deliverable in cycle_data.get("deliverables", []):
                    if not isinstance(deliverable, dict):
                        continue  # Skip plain-string deliverables (backward compat)
                    validates = deliverable.get("validates")
                    if validates is None:
                        continue
                    d_id = deliverable.get("id", "?")
                    d_desc = deliverable.get("description", "")
                    label = f"cycle:{cycle_num}:{d_id} ({d_desc})"
                    try:
                        checker.check(d_id, validates)
                        validated.append(label)
                    except Exception:
                        unvalidated.append(label)

            # Build response: blocking BEFORE ✅, informational AFTER ✅ (C10/GAP-17)
            direction = "backward" if params.to_cycle < from_cycle else "skip"
            success_line = (
                f"✅ Forced {direction} transition to TDD Cycle "
                f"{params.to_cycle}/{total_cycles}: {cycle_name}\n"
                f"Reason: {params.skip_reason}\n"
                f"Approval: {params.human_approval}"
            )

            parts: list[str] = []
            if unvalidated:
                parts.append(f"⚠️ Unvalidated cycle deliverables: {', '.join(unvalidated)}")
            parts.append(success_line)
            if validated:
                parts.append(f"ℹ️ Validated skipped deliverables: {', '.join(validated)}")
            message = "\n".join(parts)

            return ToolResult.text(message)

        except (OSError, ValueError, RuntimeError, KeyError) as e:
            return ToolResult.error(f"Forced transition failed: {e}")
