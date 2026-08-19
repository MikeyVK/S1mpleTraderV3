"""
Phase transition tools - MCP tools for phase state management.

Provides MCP tools for standard sequential and forced non-sequential
phase transitions via PhaseStateEngine.

@layer: Tools
@dependencies: [PhaseStateEngine, ProjectManager, BaseTool]
@responsibilities:
    - Wrap PhaseStateEngine.transition() for MCP protocol
    - Wrap PhaseStateEngine.force_transition() for MCP protocol
    - Validate input parameters
    - Format success/error messages
"""

from pathlib import Path
from typing import Any, ClassVar, Generic, TypeVar

import anyio
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcp_server.core.exceptions import ConfigError
from mcp_server.core.interfaces import ICoreTool
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.workflow_state_mutator import StateMutationConflictError
from mcp_server.schemas import WorkphasesConfig
from mcp_server.schemas.tool_outputs import ForcePhaseTransitionOutput, PhaseTransitionOutput


class TransitionPhaseInput(BaseModel):
    """Input model for TransitionPhaseTool."""

    model_config = ConfigDict(extra="forbid")

    branch: str = Field(description="Branch name (e.g., 'feature/123-name')")
    to_phase: str = Field(
        description=(
            "Target phase to transition to. "
            "Call get_work_context() to see the valid phase list for this branch."
        )
    )
    human_approval_message: str | None = Field(
        default=None, description="Optional human approval message"
    )

    @field_validator("human_approval_message", mode="before")
    @classmethod
    def reject_boolean_approval(cls, v: Any) -> Any:
        if isinstance(v, bool):
            raise ValueError("human_approval_message cannot be a boolean")
        return v


class ForcePhaseTransitionInput(BaseModel):
    """Input model for ForcePhaseTransitionTool.

    Requires both skip_reason and human_approval_message for audit trail.
    """

    model_config = ConfigDict(extra="forbid")

    branch: str = Field(description="Branch name (e.g., 'feature/123-name')")
    to_phase: str = Field(
        description=(
            "Target phase (can skip phases). "
            "Call get_work_context() to see the valid phase list for this branch."
        )
    )
    skip_reason: str = Field(description="Reason for skipping validation (audit)", min_length=1)
    human_approval_message: str = Field(
        description="Human approval message (required)", min_length=1
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
            msg = "Field cannot be empty"
            raise ValueError(msg)
        return v.strip()


TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class _BaseTransitionTool(ICoreTool[TInput, TOutput], Generic[TInput, TOutput]):
    """Base class for phase transition tools implementing ILegacyTool."""

    enforcement_event = "transition_phase"

    def __init__(
        self,
        workspace_root: Path | str,
        project_manager: ProjectManager | None = None,
        state_engine: PhaseStateEngine | None = None,
        server_root: Path | None = None,
        workphases_config: WorkphasesConfig | None = None,
    ) -> None:
        """Initialize tool with injected or legacy-created transition dependencies."""
        self.workspace_root = Path(workspace_root)
        if server_root is None:
            raise ValueError(
                "_BaseTransitionTool requires server_root. "
                "Pass server_root=workspace_root / settings.server.server_root_dir from server.py."
            )
        self.server_root = server_root
        self._project_manager = project_manager
        self._state_engine = state_engine
        self._workphases_config = workphases_config

    @property
    def input_schema(self) -> dict[str, Any]:
        if self.args_model:
            from mcp_server.utils.schema_utils import resolve_schema_refs  # noqa: PLC0415

            schema = resolve_schema_refs(self.args_model.model_json_schema())
            if self._workphases_config is not None:
                schema["properties"]["to_phase"]["enum"] = list(
                    self._workphases_config.phases.keys()
                )
            return schema
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


class TransitionPhaseTool(_BaseTransitionTool[TransitionPhaseInput, PhaseTransitionOutput]):
    """MCP tool for standard sequential phase transitions.

    Validates transitions via PhaseStateEngine against workflow definitions.
    """

    output_model: ClassVar[type[BaseModel]] = PhaseTransitionOutput

    @property
    def name(self) -> str:
        return "transition_phase"

    @property
    def description(self) -> str:
        return "Transition branch to next phase (strict sequential)"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return TransitionPhaseInput

    async def execute(
        self, params: TransitionPhaseInput, context: NoteContext
    ) -> PhaseTransitionOutput:
        """Execute standard phase transition.

        Args:
            params: TransitionPhaseInput with branch and target phase

        Returns:
            PhaseTransitionOutput DTO
        """
        engine = self._create_engine()

        def do_transition() -> dict[str, Any]:
            return engine.transition(
                branch=params.branch,
                to_phase=params.to_phase,
                human_approval_message=params.human_approval_message,
            )

        try:
            result = await anyio.to_thread.run_sync(do_transition)

            return PhaseTransitionOutput(
                success=True,
                branch=params.branch,
                from_phase=result["from_phase"],
                to_phase=result["to_phase"],
                passing_gates=result.get("passing_gates", []),
                skipped_gates=result.get("skipped_gates", []),
                passing_gates_count=len(result.get("passing_gates", [])),
                skipped_gates_count=len(result.get("skipped_gates", [])),
            )

        except StateMutationConflictError as e:
            context.produce(
                Note(key="transition_conflict_recovery", params={"recovery_steps": e.recovery})
            )
            return PhaseTransitionOutput(
                success=False,
                error_message=e.diagnostic,
                branch=params.branch,
                from_phase="",
                to_phase=params.to_phase,
            )
        except (ValueError, OSError, RuntimeError, KeyError, ConfigError) as e:
            return PhaseTransitionOutput(
                success=False,
                error_message=f"Transition failed: {e}",
                branch=params.branch,
                from_phase="",
                to_phase=params.to_phase,
            )


class ForcePhaseTransitionTool(
    _BaseTransitionTool[ForcePhaseTransitionInput, ForcePhaseTransitionOutput]
):
    """MCP tool for forced non-sequential phase transitions.

    Bypasses workflow validation. Requires skip_reason and human_approval_message.
    Marks transitions with forced=True flag in state.json audit trail.
    """

    output_model: ClassVar[type[BaseModel]] = ForcePhaseTransitionOutput

    @property
    def name(self) -> str:
        return "force_phase_transition"

    @property
    def description(self) -> str:
        return "Force non-sequential phase transition (skip/jump with reason)"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return ForcePhaseTransitionInput

    async def execute(
        self, params: ForcePhaseTransitionInput, context: NoteContext
    ) -> ForcePhaseTransitionOutput:
        """Execute forced phase transition.

        Args:
            params: ForcePhaseTransitionInput with branch, phase, reason, approval

        Returns:
            ForcePhaseTransitionOutput DTO
        """
        engine = self._create_engine()

        def do_force_transition() -> dict[str, Any]:
            return engine.force_transition(
                branch=params.branch,
                to_phase=params.to_phase,
                skip_reason=params.skip_reason,
                human_approval_message=params.human_approval_message,
            )

        try:
            result = await anyio.to_thread.run_sync(do_force_transition)

            blocking = result.get("skipped_gates", [])
            passing = result.get("passing_gates", [])

            skipped_gates_warning = ""
            if blocking:
                lines = [
                    f"⚠️ ACTION REQUIRED: {len(blocking)} skipped gate(s) would have"
                    " BLOCKED a normal transition:"
                ]
                for gate in blocking:
                    lines.append(f"  - {gate}")
                lines.append("  Verify or resolve before proceeding.")
                skipped_gates_warning = "\n".join(lines) + "\n"

            passing_gates_info = ""
            if passing:
                passing_gates_info = f"\nℹ️ Gates that would have passed: {', '.join(passing)}"

            return ForcePhaseTransitionOutput(
                success=True,
                branch=params.branch,
                from_phase=result["from_phase"],
                to_phase=result["to_phase"],
                passing_gates=passing,
                skipped_gates=blocking,
                passing_gates_count=len(passing),
                skipped_gates_count=len(blocking),
                skip_reason=params.skip_reason,
                human_approval_message=params.human_approval_message,
                skipped_gates_warning=skipped_gates_warning,
                passing_gates_info=passing_gates_info,
            )
        except StateMutationConflictError as e:
            context.produce(
                Note(key="transition_conflict_recovery", params={"recovery_steps": e.recovery})
            )
            return ForcePhaseTransitionOutput(
                success=False,
                error_message=e.diagnostic,
                branch=params.branch,
                from_phase="",
                to_phase=params.to_phase,
                skip_reason=params.skip_reason,
                human_approval_message=params.human_approval_message,
            )
        except (ValueError, OSError, RuntimeError, KeyError, ConfigError) as e:
            return ForcePhaseTransitionOutput(
                success=False,
                error_message=f"Force transition failed: {e}",
                branch=params.branch,
                from_phase="",
                to_phase=params.to_phase,
                skip_reason=params.skip_reason,
                human_approval_message=params.human_approval_message,
            )
