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
from typing import Any, ClassVar, Generic, TypeVar

import anyio
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcp_server.core.interfaces import GateViolation, ICoreTool, IWorkflowGateRunner
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.workflow_state_mutator import StateMutationConflictError
from mcp_server.schemas.tool_outputs import CycleTransitionOutput, ForceCycleTransitionOutput
from mcp_server.utils.schema_utils import resolve_schema_refs

__all__ = [
    "ForceCycleTransitionInput",
    "ForceCycleTransitionTool",
    "TransitionCycleInput",
    "TransitionCycleTool",
]


TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class _BaseIToolTransition(ICoreTool[TInput, TOutput], Generic[TInput, TOutput]):
    """Base class for cycle transition tools implementing ILegacyTool."""

    def __init__(
        self,
        workspace_root: Path | str,
        project_manager: ProjectManager | None = None,
        state_engine: PhaseStateEngine | None = None,
        git_manager: GitManager | None = None,
        gate_runner: IWorkflowGateRunner | None = None,
        server_root: Path | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        if server_root is None:
            raise ValueError("_BaseIToolTransition requires server_root.")
        self.server_root = server_root
        self._project_manager = project_manager
        self._state_engine = state_engine
        self._git_manager = git_manager
        self._gate_runner = gate_runner

    @property
    def input_schema(self) -> dict[str, Any]:
        if self.args_model:
            return resolve_schema_refs(self.args_model.model_json_schema())
        return {
            "type": "object",
            "properties": {},
        }

    def _create_project_manager(self) -> ProjectManager:
        """Return the injected ProjectManager."""
        if self._project_manager is None:
            raise ValueError("ProjectManager must be injected for transition tools")
        return self._project_manager

    def _create_engine(self) -> PhaseStateEngine:
        """Return the injected PhaseStateEngine instance."""
        if self._state_engine is None:
            raise ValueError("PhaseStateEngine must be injected for transition tools")
        return self._state_engine

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
        except (ValueError, OSError, RuntimeError):  # git unavailable — fall back to state file
            branch = None

        # NOTE: IStateReader requires a known branch as input; raw state.json read retained
        # intentionally here because this method's purpose is to discover the branch itself.
        state_file = self.server_root / "state.json"
        if state_file.exists():
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(state_data, dict):
                state_branch = state_data.get("branch")
                if isinstance(state_branch, str) and state_branch:
                    return state_branch

        if branch is None:
            raise RuntimeError("Unable to determine current branch")
        return branch


class TransitionCycleInput(BaseModel):
    """Input for transition_cycle tool."""

    model_config = ConfigDict(extra="forbid")

    to_cycle: int = Field(..., description="Target cycle number (forward-only)")
    issue_number: int | None = Field(
        default=None,
        description="Issue number (auto-detected from branch if omitted)",
    )


class TransitionCycleTool(_BaseIToolTransition[TransitionCycleInput, CycleTransitionOutput]):
    """Tool to transition to next implementation cycle with validation."""

    output_model: ClassVar[type[BaseModel]] = CycleTransitionOutput
    enforcement_event = "transition_cycle"

    @property
    def name(self) -> str:
        return "transition_cycle"

    @property
    def description(self) -> str:
        return (
            "Transition to next TDD cycle (forward-only, sequential). "
            "Use force_cycle_transition to skip cycles or go backwards."
        )

    @property
    def args_model(self) -> type[BaseModel] | None:
        return TransitionCycleInput

    async def execute(
        self, params: TransitionCycleInput, context: NoteContext
    ) -> CycleTransitionOutput:
        """Execute cycle transition through the shared orchestration path."""
        branch = self._get_current_branch()
        issue_number = params.issue_number or self._extract_issue_number(branch)
        if issue_number is None:
            return CycleTransitionOutput(
                success=False,
                error_message="Cannot detect issue number from branch",
                branch=branch,
                to_cycle=params.to_cycle,
                total_cycles=0,
                cycle_name="",
            )

        state_engine = self._create_engine()

        def do_transition() -> dict[str, Any]:
            return state_engine.transition_cycle(
                branch=branch,
                to_cycle=params.to_cycle,
                gate_runner=self._gate_runner,
            )

        try:
            result = await anyio.to_thread.run_sync(do_transition)
            return CycleTransitionOutput(
                success=True,
                branch=branch,
                from_cycle=result.get("from_cycle"),
                to_cycle=result["to_cycle"],
                total_cycles=result["total_cycles"],
                cycle_name=result["cycle_name"],
                passing_gates=result.get("passing_gates", []),
                skipped_gates=result.get("skipped_gates", []),
                passing_gates_count=len(result.get("passing_gates", [])),
                skipped_gates_count=len(result.get("skipped_gates", [])),
            )
        except StateMutationConflictError as e:
            context.produce(
                Note(key="transition_conflict_recovery", params={"recovery_steps": e.recovery})
            )
            return CycleTransitionOutput(
                success=False,
                error_message=e.diagnostic,
                branch=branch,
                to_cycle=params.to_cycle,
                total_cycles=0,
                cycle_name="",
            )
        except (GateViolation, OSError, ValueError, RuntimeError, KeyError) as exc:
            return CycleTransitionOutput(
                success=False,
                error_message=f"Transition failed: {exc}",
                branch=branch,
                to_cycle=params.to_cycle,
                total_cycles=0,
                cycle_name="",
            )


class ForceCycleTransitionInput(BaseModel):
    """Input for force_cycle_transition tool."""

    model_config = ConfigDict(extra="forbid")

    to_cycle: int = Field(..., description="Target cycle number (any direction)")
    skip_reason: str = Field(
        ..., description="Reason for forced transition (backward/skip)", min_length=1
    )
    human_approval_message: str = Field(
        ...,
        description="Human approval (name + date, e.g., 'John approved on 2026-02-17')",
        min_length=1,
    )
    issue_number: int | None = Field(
        default=None,
        description="Issue number (auto-detected from branch if omitted)",
    )

    @field_validator("human_approval_message", mode="before")
    @classmethod
    def reject_boolean_approval(cls, v: Any) -> Any:
        if isinstance(v, bool):
            raise ValueError("human_approval_message cannot be a boolean")
        return v

    @field_validator("skip_reason", "human_approval_message")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure skip_reason and human_approval_message are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class ForceCycleTransitionTool(
    _BaseIToolTransition[ForceCycleTransitionInput, ForceCycleTransitionOutput]
):
    """Tool to force TDD cycle transition with audit trail."""

    output_model: ClassVar[type[BaseModel]] = ForceCycleTransitionOutput
    enforcement_event = "transition_cycle"

    @property
    def name(self) -> str:
        return "force_cycle_transition"

    @property
    def description(self) -> str:
        return (
            "Force transition to any TDD cycle (backward or skip). "
            "Requires skip_reason and human_approval_message for audit trail."
        )

    @property
    def args_model(self) -> type[BaseModel] | None:
        return ForceCycleTransitionInput

    async def execute(
        self, params: ForceCycleTransitionInput, context: NoteContext
    ) -> ForceCycleTransitionOutput:
        """Execute forced cycle transition through the shared inspection path."""
        branch = self._get_current_branch()
        issue_number = params.issue_number or self._extract_issue_number(branch)
        if issue_number is None:
            return ForceCycleTransitionOutput(
                success=False,
                error_message="Cannot detect issue number from branch",
                branch=branch,
                to_cycle=params.to_cycle,
                total_cycles=0,
                cycle_name="",
                skip_reason=params.skip_reason,
                human_approval_message=params.human_approval_message,
            )

        state_engine = self._create_engine()

        def do_force_transition() -> dict[str, Any]:
            return state_engine.force_cycle_transition(
                branch=branch,
                to_cycle=params.to_cycle,
                skip_reason=params.skip_reason,
                human_approval_message=params.human_approval_message,
                gate_runner=self._gate_runner,
            )

        try:
            result = await anyio.to_thread.run_sync(do_force_transition)
            return ForceCycleTransitionOutput(
                success=True,
                branch=branch,
                from_cycle=result.get("from_cycle"),
                to_cycle=result["to_cycle"],
                total_cycles=result["total_cycles"],
                cycle_name=result["cycle_name"],
                passing_gates=result.get("passing_gates", []),
                skipped_gates=result.get("skipped_gates", []),
                passing_gates_count=len(result.get("passing_gates", [])),
                skipped_gates_count=len(result.get("skipped_gates", [])),
                skip_reason=params.skip_reason,
                human_approval_message=params.human_approval_message,
            )
        except StateMutationConflictError as e:
            context.produce(
                Note(key="transition_conflict_recovery", params={"recovery_steps": e.recovery})
            )
            return ForceCycleTransitionOutput(
                success=False,
                error_message=e.diagnostic,
                branch=branch,
                to_cycle=params.to_cycle,
                total_cycles=0,
                cycle_name="",
                skip_reason=params.skip_reason,
                human_approval_message=params.human_approval_message,
            )
        except (GateViolation, OSError, ValueError, RuntimeError, KeyError) as exc:
            return ForceCycleTransitionOutput(
                success=False,
                error_message=f"Forced transition failed: {exc}",
                branch=branch,
                to_cycle=params.to_cycle,
                total_cycles=0,
                cycle_name="",
                skip_reason=params.skip_reason,
                human_approval_message=params.human_approval_message,
            )
