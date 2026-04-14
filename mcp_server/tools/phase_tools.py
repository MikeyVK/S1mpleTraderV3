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

# Standard library
from pathlib import Path
from typing import Any

# Third-party
import anyio
from pydantic import BaseModel, Field, field_validator

# Project modules
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult
from mcp_server.core.operation_notes import NoteContext


class TransitionPhaseInput(BaseModel):
    """Input model for TransitionPhaseTool."""

    branch: str = Field(description="Branch name (e.g., 'feature/123-name')")
    to_phase: str = Field(description="Target phase to transition to")
    human_approval: str | None = Field(default=None, description="Optional human approval message")


class ForcePhaseTransitionInput(BaseModel):
    """Input model for ForcePhaseTransitionTool.

    Requires both skip_reason and human_approval for audit trail.
    """

    branch: str = Field(description="Branch name (e.g., 'feature/123-name')")
    to_phase: str = Field(description="Target phase (can skip phases)")
    skip_reason: str = Field(description="Reason for skipping validation (audit)")
    human_approval: str = Field(description="Human approval message (required)")

    @field_validator("skip_reason", "human_approval")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure skip_reason and human_approval are not empty."""
        if not v or not v.strip():
            msg = "Field cannot be empty"
            raise ValueError(msg)
        return v.strip()


class _BaseTransitionTool(BaseTool):
    """Base class for phase and cycle transition tools."""

    def __init__(
        self,
        workspace_root: Path | str,
        project_manager: ProjectManager | None = None,
        state_engine: PhaseStateEngine | None = None,
    ) -> None:
        """Initialize tool with injected or legacy-created transition dependencies."""
        super().__init__()
        self.workspace_root = Path(workspace_root)
        self._project_manager = project_manager
        self._state_engine = state_engine

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


class TransitionPhaseTool(_BaseTransitionTool):
    """MCP tool for standard sequential phase transitions.

    Validates transitions via PhaseStateEngine against workflow definitions.
    """

    name = "transition_phase"
    description = "Transition branch to next phase (strict sequential)"
    args_model = TransitionPhaseInput
    enforcement_event = "transition_phase"

    async def execute(self, params: TransitionPhaseInput, _context: NoteContext | None = None) -> ToolResult:
        """Execute standard phase transition.

        Uses anyio.to_thread.run_sync() for compatibility with MCP's anyio-based
        server - asyncio.to_thread doesn't work correctly within anyio context
        (Issue #85 fix).

        Args:
            params: TransitionPhaseInput with branch and target phase

        Returns:
            ToolResult with success or error message
        """
        engine = self._create_engine()

        def do_transition() -> dict[str, Any]:
            return engine.transition(
                branch=params.branch, to_phase=params.to_phase, human_approval=params.human_approval
            )

        try:
            result = await anyio.to_thread.run_sync(do_transition)

            return ToolResult.text(
                f"✅ Successfully transitioned '{params.branch}' "
                f"from {result['from_phase']} → {result['to_phase']}"
            )

        except ValueError as e:
            return ToolResult.error(f"❌ Transition failed: {e}")


class ForcePhaseTransitionTool(_BaseTransitionTool):
    """MCP tool for forced non-sequential phase transitions.

    Bypasses workflow validation. Requires skip_reason and human_approval.
    Marks transitions with forced=True flag in state.json audit trail.
    """

    name = "force_phase_transition"
    description = "Force non-sequential phase transition (skip/jump with reason)"
    args_model = ForcePhaseTransitionInput
    enforcement_event = "transition_phase"

    async def execute(self, params: ForcePhaseTransitionInput, _context: NoteContext | None = None) -> ToolResult:
        """Execute forced phase transition.

        Uses anyio.to_thread.run_sync() for compatibility with MCP's anyio-based
        server - asyncio.to_thread doesn't work correctly within anyio context
        (Issue #85 fix).

        Args:
            params: ForcePhaseTransitionInput with branch, phase, reason, approval

        Returns:
            ToolResult with success or error message
        """
        engine = self._create_engine()

        def do_force_transition() -> dict[str, Any]:
            return engine.force_transition(
                branch=params.branch,
                to_phase=params.to_phase,
                skip_reason=params.skip_reason,
                human_approval=params.human_approval,
            )

        try:
            result = await anyio.to_thread.run_sync(do_force_transition)

            blocking = result.get("skipped_gates", [])
            passing = result.get("passing_gates", [])

            lines: list[str] = []

            if blocking:
                lines.append(
                    f"⚠️ ACTION REQUIRED: {len(blocking)} skipped gate(s) would have"
                    " BLOCKED a normal transition:"
                )
                for gate in blocking:
                    lines.append(f"  - {gate}")
                lines.append("  Verify or resolve before proceeding.")

            lines.append(
                f"✅ Forced transition '{params.branch}' "
                f"from {result['from_phase']} → {result['to_phase']} "
                f"(forced=True, reason: {params.skip_reason})"
            )

            if passing:
                lines.append(f"ℹ️ Gates that would have passed: {', '.join(passing)}")

            return ToolResult.text("\n".join(lines))

        except ValueError as e:
            return ToolResult.error(f"❌ Force transition failed: {e}")
