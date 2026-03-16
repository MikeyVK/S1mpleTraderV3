# mcp_server/tools/cycle_tools.py
# template=tool version=27130d2b created=2026-03-13T12:34Z updated=
"""Cycle transition tools for implementation cycle management.

Provides MCP tools for standard sequential and forced non-sequential
cycle transitions via PhaseStateEngine.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from mcp_server.managers.deliverable_checker import DeliverableChecker
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.tools.phase_tools import _BaseTransitionTool
from mcp_server.tools.tool_result import ToolResult

__all__ = [
    "ForceCycleTransitionInput",
    "ForceCycleTransitionTool",
    "TransitionCycleInput",
    "TransitionCycleTool",
]


class TransitionCycleInput(BaseModel):
    """Input for transition_cycle tool."""

    to_cycle: int = Field(..., description="Target cycle number (forward-only)")
    issue_number: int | None = Field(
        default=None,
        description="Issue number (auto-detected from branch if omitted)",
    )


class TransitionCycleTool(_BaseTransitionTool):
    """Tool to transition to next implementation cycle with validation."""

    def __init__(
        self,
        workspace_root: Path | str,
        project_manager: ProjectManager | None = None,
        state_engine: PhaseStateEngine | None = None,
        git_manager: GitManager | None = None,
    ) -> None:
        super().__init__(workspace_root, project_manager, state_engine)
        self._git_manager = git_manager

    name = "transition_cycle"
    description = (
        "Transition to next TDD cycle (forward-only, sequential). "
        "Use force_cycle_transition to skip cycles or go backwards."
    )
    args_model = TransitionCycleInput
    enforcement_event = "transition_cycle"

    async def execute(self, params: TransitionCycleInput) -> ToolResult:
        """Execute cycle transition with validation."""
        try:
            branch = self._get_current_branch()
            issue_number = params.issue_number or self._extract_issue_number(branch)
            if issue_number is None:
                return ToolResult.error("Cannot detect issue number from branch")

            project_manager = self._create_project_manager()
            state_engine = self._create_engine()
            state = state_engine.get_state(branch)
            current_phase = state.current_phase
            current_cycle = state.current_cycle

            if current_phase != "implementation":
                return ToolResult.error(
                    f"Not in implementation phase (current: {current_phase}). "
                    "Cycle transitions only allowed during implementation phase."
                )

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
            if params.to_cycle < 1 or params.to_cycle > total_cycles:
                return ToolResult.error(
                    f"Invalid cycle number {params.to_cycle}. Valid range: 1-{total_cycles}"
                )

            if current_cycle is not None and params.to_cycle <= current_cycle:
                return ToolResult.error(
                    f"Backwards transition not allowed (current: {current_cycle}, "
                    f"target: {params.to_cycle}). "
                    "Use force_cycle_transition for backwards transitions."
                )

            if current_cycle is not None and params.to_cycle != current_cycle + 1:
                return ToolResult.error(
                    f"Non-sequential transition not allowed (current: {current_cycle}, "
                    f"target: {params.to_cycle}). "
                    "Use force_cycle_transition to skip cycles."
                )

            if current_cycle is not None:
                cycles_list = tdd_cycles.get("cycles", [])
                current_cycle_data = next(
                    (cycle for cycle in cycles_list if cycle.get("cycle_number") == current_cycle),
                    None,
                )
                if current_cycle_data is not None:
                    exit_criteria = current_cycle_data.get("exit_criteria", "")
                    if not exit_criteria or not exit_criteria.strip():
                        return ToolResult.error(
                            f"Cycle {current_cycle} exit criteria not defined. "
                            "Define exit_criteria in planning deliverables before transitioning."
                        )

            from_cycle = current_cycle or 0
            history_entry = {
                "cycle_number": params.to_cycle,
                "forced": False,
                "entered": datetime.now(UTC).isoformat(),
            }
            updated_state = state.with_updates(
                last_cycle=from_cycle,
                current_cycle=params.to_cycle,
                cycle_history=[*state.cycle_history, history_entry],
            )
            state_engine._save_state(branch, updated_state)

            cycles = tdd_cycles.get("cycles", [])
            cycle_details = next(
                (cycle for cycle in cycles if cycle.get("cycle_number") == params.to_cycle),
                None,
            )
            cycle_name = cycle_details.get("name") if cycle_details else "Unknown"
            return ToolResult.text(
                f"✅ Transitioned to TDD Cycle {params.to_cycle}/{total_cycles}: {cycle_name}"
            )
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            return ToolResult.error(f"Transition failed: {exc}")

    def _get_git_manager(self) -> GitManager:
        """Return the injected GitManager."""
        if self._git_manager is None:
            raise ValueError("GitManager must be injected for cycle transition tools")
        return self._git_manager

    def _extract_issue_number(self, branch: str) -> int | None:
        """Extract issue number from git config when available, else from branch syntax."""
        extracted = None
        with_config = getattr(self._get_git_manager(), "git_config", None)
        if with_config is not None:
            extract = getattr(with_config, "extract_issue_number", None)
            if callable(extract):
                extracted = extract(branch)
                if isinstance(extracted, int):
                    return extracted

        match = re.search(r"/(\d+)(?:-|$)", branch)
        return int(match.group(1)) if match else None

    def _get_current_branch(self) -> str:
        """Resolve the active branch, falling back to a single saved state entry."""
        branch: str | None = None
        try:
            branch = self._get_git_manager().get_current_branch()
        except Exception:
            branch = None

        state_file = self.workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(state_data, dict):
                state_branch = state_data.get("branch")
                if isinstance(state_branch, str) and state_branch:
                    return state_branch

        if branch is None:
            raise RuntimeError("Unable to determine current branch")
        return branch


class ForceCycleTransitionInput(BaseModel):
    """Input for force_cycle_transition tool."""

    to_cycle: int = Field(..., description="Target cycle number (any direction)")
    skip_reason: str = Field(..., description="Reason for forced transition (backward/skip)")
    human_approval: str = Field(
        ...,
        description="Human approval (name + date, e.g., 'John approved on 2026-02-17')",
    )
    issue_number: int | None = Field(
        default=None,
        description="Issue number (auto-detected from branch if omitted)",
    )


class ForceCycleTransitionTool(_BaseTransitionTool):
    """Tool to force implementation cycle transition with audit trail."""

    def __init__(
        self,
        workspace_root: Path | str,
        project_manager: ProjectManager | None = None,
        state_engine: PhaseStateEngine | None = None,
        git_manager: GitManager | None = None,
    ) -> None:
        super().__init__(workspace_root, project_manager, state_engine)
        self._git_manager = git_manager

    name = "force_cycle_transition"
    description = (
        "Force transition to any TDD cycle (backward or skip). "
        "Requires skip_reason and human_approval for audit trail."
    )
    args_model = ForceCycleTransitionInput
    enforcement_event = "transition_cycle"

    async def execute(self, params: ForceCycleTransitionInput) -> ToolResult:
        """Execute forced cycle transition with audit trail."""
        try:
            if not params.skip_reason or params.skip_reason.strip() == "":
                return ToolResult.error(
                    "skip_reason is required for forced transitions. "
                    "Provide justification for backward/skip transition."
                )
            if not params.human_approval or params.human_approval.strip() == "":
                return ToolResult.error(
                    "human_approval is required for forced transitions. "
                    "Provide approval (e.g., 'John approved on 2026-02-17')."
                )

            branch = self._get_current_branch()
            issue_number = params.issue_number or self._extract_issue_number(branch)
            if issue_number is None:
                return ToolResult.error("Cannot detect issue number from branch")

            project_manager = self._create_project_manager()
            state_engine = self._create_engine()
            state = state_engine.get_state(branch)
            current_phase = state.current_phase
            current_cycle = state.current_cycle

            if current_phase != "implementation":
                return ToolResult.error(
                    f"Not in implementation phase (current: {current_phase}). "
                    "Cycle transitions only allowed during implementation phase."
                )

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
            if params.to_cycle < 1 or params.to_cycle > total_cycles:
                return ToolResult.error(
                    f"Invalid cycle number {params.to_cycle}. Valid range: 1-{total_cycles}"
                )

            from_cycle = current_cycle or 0
            cycles = tdd_cycles.get("cycles", [])
            cycle_details = next(
                (cycle for cycle in cycles if cycle.get("cycle_number") == params.to_cycle),
                None,
            )
            cycle_name = cycle_details.get("name") if cycle_details else "Unknown"

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
            updated_state = state.with_updates(
                last_cycle=from_cycle,
                current_cycle=params.to_cycle,
                cycle_history=[*state.cycle_history, audit_entry],
            )
            state_engine._save_state(branch, updated_state)

            checker = DeliverableChecker(workspace_root=self.workspace_root)
            unvalidated: list[str] = []
            validated: list[str] = []
            for cycle_num in skipped_cycles:
                cycle_data = next(
                    (cycle for cycle in cycles if cycle.get("cycle_number") == cycle_num),
                    None,
                )
                if cycle_data is None:
                    continue
                for deliverable in cycle_data.get("deliverables", []):
                    if not isinstance(deliverable, dict):
                        continue
                    validates = deliverable.get("validates")
                    if validates is None:
                        continue
                    deliverable_id = deliverable.get("id", "?")
                    deliverable_desc = deliverable.get("description", "")
                    label = f"cycle:{cycle_num}:{deliverable_id} ({deliverable_desc})"
                    try:
                        checker.check(deliverable_id, validates)
                        validated.append(label)
                    except Exception:
                        unvalidated.append(label)

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
            return ToolResult.text("\n".join(parts))
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            return ToolResult.error(f"Forced transition failed: {exc}")

    def _get_git_manager(self) -> GitManager:
        """Return the injected GitManager."""
        if self._git_manager is None:
            raise ValueError("GitManager must be injected for cycle transition tools")
        return self._git_manager

    def _extract_issue_number(self, branch: str) -> int | None:
        """Extract issue number from git config when available, else from branch syntax."""
        extracted = None
        with_config = getattr(self._get_git_manager(), "git_config", None)
        if with_config is not None:
            extract = getattr(with_config, "extract_issue_number", None)
            if callable(extract):
                extracted = extract(branch)
                if isinstance(extracted, int):
                    return extracted

        match = re.search(r"/(\d+)(?:-|$)", branch)
        return int(match.group(1)) if match else None

    def _get_current_branch(self) -> str:
        """Resolve the active branch, falling back to a single saved state entry."""
        branch: str | None = None
        try:
            branch = self._get_git_manager().get_current_branch()
        except Exception:
            branch = None

        state_file = self.workspace_root / ".st3" / "state.json"
        if state_file.exists():
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(state_data, dict):
                state_branch = state_data.get("branch")
                if isinstance(state_branch, str) and state_branch:
                    return state_branch

        if branch is None:
            raise RuntimeError("Unable to determine current branch")
        return branch
