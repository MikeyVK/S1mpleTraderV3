# mcp_server/tools/cycle_tools.py
# template=tool version=27130d2b created=2026-03-13T12:34Z updated=
"""Cycle transition tools for implementation cycle management.

Provides MCP tools for standard sequential and forced non-sequential
cycle transitions via PhaseStateEngine.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import anyio
from pydantic import BaseModel, Field

from mcp_server.core.interfaces import GateViolation, IWorkflowGateRunner
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.tools.phase_tools import (
    _BaseTransitionTool as BaseTransitionTool,  # pyright: ignore[reportPrivateUsage]  # Shared transition base pending tool consolidation.
)
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


class TransitionCycleTool(BaseTransitionTool):
    """Tool to transition to next implementation cycle with validation."""

    def __init__(
        self,
        workspace_root: Path | str,
        project_manager: ProjectManager | None = None,
        state_engine: PhaseStateEngine | None = None,
        git_manager: GitManager | None = None,
        gate_runner: IWorkflowGateRunner | None = None,
    ) -> None:
        super().__init__(workspace_root, project_manager, state_engine)
        self._git_manager = git_manager
        self._gate_runner = gate_runner

    name = "transition_cycle"
    description = (
        "Transition to next TDD cycle (forward-only, sequential). "
        "Use force_cycle_transition to skip cycles or go backwards."
    )
    args_model = TransitionCycleInput
    enforcement_event = "transition_cycle"

    async def execute(self, params: TransitionCycleInput) -> ToolResult:
        """Execute cycle transition through the shared orchestration path."""
        branch = self._get_current_branch()
        issue_number = params.issue_number or self._extract_issue_number(branch)
        if issue_number is None:
            return ToolResult.error("Cannot detect issue number from branch")

        state_engine = self._create_engine()

        def do_transition() -> dict[str, Any]:
            return state_engine.transition_cycle(
                branch=branch,
                to_cycle=params.to_cycle,
                gate_runner=self._gate_runner,
            )

        try:
            result = await anyio.to_thread.run_sync(do_transition)
            return ToolResult.text(
                f"✅ Transitioned to TDD Cycle {result['to_cycle']}/{result['total_cycles']}: "
                f"{result['cycle_name']}"
            )
        except (GateViolation, OSError, ValueError, RuntimeError, KeyError) as exc:
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


class ForceCycleTransitionTool(BaseTransitionTool):
    """Tool to force implementation cycle transition with audit trail."""

    def __init__(
        self,
        workspace_root: Path | str,
        project_manager: ProjectManager | None = None,
        state_engine: PhaseStateEngine | None = None,
        git_manager: GitManager | None = None,
        gate_runner: IWorkflowGateRunner | None = None,
    ) -> None:
        super().__init__(workspace_root, project_manager, state_engine)
        self._git_manager = git_manager
        self._gate_runner = gate_runner

    name = "force_cycle_transition"
    description = (
        "Force transition to any TDD cycle (backward or skip). "
        "Requires skip_reason and human_approval for audit trail."
    )
    args_model = ForceCycleTransitionInput
    enforcement_event = "transition_cycle"

    async def execute(self, params: ForceCycleTransitionInput) -> ToolResult:
        """Execute forced cycle transition through the shared inspection path."""
        branch = self._get_current_branch()
        issue_number = params.issue_number or self._extract_issue_number(branch)
        if issue_number is None:
            return ToolResult.error("Cannot detect issue number from branch")

        state_engine = self._create_engine()

        def do_force_transition() -> dict[str, Any]:
            return state_engine.force_cycle_transition(
                branch=branch,
                to_cycle=params.to_cycle,
                skip_reason=params.skip_reason,
                human_approval=params.human_approval,
                gate_runner=self._gate_runner,
            )

        try:
            result = await anyio.to_thread.run_sync(do_force_transition)
            blocking = result.get("skipped_gates", [])
            passing = result.get("passing_gates", [])
            direction = "backward" if params.to_cycle < result["from_cycle"] else "skip"

            lines: list[str] = []
            if blocking:
                lines.append(
                    f"⚠️ ACTION REQUIRED: {len(blocking)} skipped gate(s) would have "
                    "BLOCKED a normal cycle transition:"
                )
                for gate in blocking:
                    lines.append(f"  - {gate}")
                lines.append("  Verify or resolve before proceeding.")

            lines.append(
                f"✅ Forced {direction} transition to TDD Cycle "
                f"{result['to_cycle']}/{result['total_cycles']}: {result['cycle_name']}"
            )
            lines.append(f"Reason: {params.skip_reason}")
            lines.append(f"Approval: {params.human_approval}")

            if passing:
                lines.append(f"ℹ️ Gates that would have passed: {', '.join(passing)}")

            return ToolResult.text("\n".join(lines))
        except (GateViolation, OSError, ValueError, RuntimeError, KeyError) as exc:
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
