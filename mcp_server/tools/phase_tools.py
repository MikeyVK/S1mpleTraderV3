# mcp_server/tools/phase_tools.py
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
# pylint: disable=import-outside-toplevel

# Standard library
from pathlib import Path
from typing import TYPE_CHECKING

# Third-party
from pydantic import BaseModel, Field, field_validator

# Project modules
from mcp_server.tools.base import BaseTool, ToolResult

if TYPE_CHECKING:
    from mcp_server.managers.phase_state_engine import PhaseStateEngine


class TransitionPhaseInput(BaseModel):
    """Input model for TransitionPhaseTool."""

    branch: str = Field(description="Branch name (e.g., 'feature/123-name')")
    to_phase: str = Field(description="Target phase to transition to")
    human_approval: str | None = Field(
        default=None,
        description="Optional human approval message"
    )


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


class _BasePhaseTransitionTool(BaseTool):
    """Base class for phase transition tools.

    Provides common manager creation logic to avoid duplication.
    """

    def __init__(self, workspace_root: Path | str):
        """Initialize tool.

        Args:
            workspace_root: Path to workspace root
        """
        super().__init__()
        self.workspace_root = Path(workspace_root)

    def _create_engine(self) -> "PhaseStateEngine":
        """Create PhaseStateEngine instance.

        Returns:
            PhaseStateEngine instance with initialized managers
        """
        # Import here to avoid circular dependency
        from mcp_server.managers.phase_state_engine import PhaseStateEngine
        from mcp_server.managers.project_manager import ProjectManager

        project_manager = ProjectManager(workspace_root=self.workspace_root)
        return PhaseStateEngine(
            workspace_root=self.workspace_root,
            project_manager=project_manager
        )


class TransitionPhaseTool(_BasePhaseTransitionTool):
    """MCP tool for standard sequential phase transitions.

    Validates transitions via PhaseStateEngine against workflow definitions.
    """

    name = "transition_phase"
    description = "Transition branch to next phase (strict sequential)"
    args_model = TransitionPhaseInput

    async def execute(self, params: TransitionPhaseInput) -> ToolResult:
        """Execute standard phase transition.

        Uses asyncio.to_thread() to prevent blocking the event loop
        during file I/O operations (Issue #85 fix).

        Args:
            params: TransitionPhaseInput with branch and target phase

        Returns:
            ToolResult with success or error message
        """
        import asyncio  # noqa: PLC0415

        engine = self._create_engine()

        def do_transition() -> dict:
            return engine.transition(
                branch=params.branch,
                to_phase=params.to_phase,
                human_approval=params.human_approval
            )

        try:
            result = await asyncio.to_thread(do_transition)

            return ToolResult.text(
                f"✅ Successfully transitioned '{params.branch}' "
                f"from {result['from_phase']} → {result['to_phase']}"
            )

        except ValueError as e:
            return ToolResult.error(f"❌ Transition failed: {e}")


class ForcePhaseTransitionTool(_BasePhaseTransitionTool):
    """MCP tool for forced non-sequential phase transitions.

    Bypasses workflow validation. Requires skip_reason and human_approval.
    Marks transitions with forced=True flag in state.json audit trail.
    """

    name = "force_phase_transition"
    description = "Force non-sequential phase transition (skip/jump with reason)"
    args_model = ForcePhaseTransitionInput

    async def execute(self, params: ForcePhaseTransitionInput) -> ToolResult:
        """Execute forced phase transition.

        Uses asyncio.to_thread() to prevent blocking the event loop
        during file I/O operations (Issue #85 fix).

        Args:
            params: ForcePhaseTransitionInput with branch, phase, reason, approval

        Returns:
            ToolResult with success or error message
        """
        import asyncio  # noqa: PLC0415

        engine = self._create_engine()

        def do_force_transition() -> dict:
            return engine.force_transition(
                branch=params.branch,
                to_phase=params.to_phase,
                skip_reason=params.skip_reason,
                human_approval=params.human_approval
            )

        try:
            result = await asyncio.to_thread(do_force_transition)

            return ToolResult.text(
                f"✅ Forced transition '{params.branch}' "
                f"from {result['from_phase']} → {result['to_phase']} "
                f"(forced=True, reason: {params.skip_reason})"
            )

        except ValueError as e:
            return ToolResult.error(f"❌ Force transition failed: {e}")
