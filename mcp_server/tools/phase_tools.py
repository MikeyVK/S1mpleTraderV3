# mcp_server/tools/phase_tools.py
"""
TransitionPhaseTool - Phase B: Agent phase control via MCP.

This module provides the TransitionPhaseTool that wraps PhaseStateEngine
to expose phase transitions via MCP protocol.

@layer: Tools
@dependencies: [PhaseStateEngine, BaseTool]
"""
# pylint: disable=import-outside-toplevel
# Standard library
from pathlib import Path

# Third-party
from pydantic import BaseModel, Field

# Project modules
from mcp_server.tools.base import BaseTool, ToolResult


class TransitionPhaseInput(BaseModel):
    """Input model for TransitionPhaseTool."""

    branch: str = Field(description="Branch name to transition (e.g., 'feature/123-name')")
    from_phase: str = Field(description="Current phase the branch is in")
    to_phase: str = Field(description="Target phase to transition to")
    human_approval: str | None = Field(
        default=None,
        description="Optional human approval message for the transition"
    )


class TransitionPhaseTool(BaseTool):
    """MCP tool for transitioning branch phases.

    Wraps PhaseStateEngine to provide phase control via MCP protocol.
    Creates a fresh PhaseStateEngine instance on each execution to load
    the latest state from disk.
    """

    name = "transition_phase"
    description = "Transition a branch to a new phase with validation"
    args_model = TransitionPhaseInput

    def __init__(self, workspace_root: Path | str):
        """Initialize the tool.

        Args:
            workspace_root: Path to workspace root
        """
        super().__init__()
        self.workspace_root = Path(workspace_root)

    async def execute(self, params: TransitionPhaseInput) -> ToolResult:
        """Execute phase transition.

        Args:
            params: TransitionPhaseInput with branch and phase details

        Returns:
            ToolResult with success or error message
        """
        # Import inside method to avoid circular dependency
        from mcp_server.core.phase_state_engine import PhaseStateEngine

        # Create fresh engine to load latest state from disk
        engine = PhaseStateEngine(workspace_root=self.workspace_root)

        # Execute transition
        result = engine.transition(
            branch=params.branch,
            from_phase=params.from_phase,
            to_phase=params.to_phase,
            human_approval=params.human_approval
        )

        # Check result
        if result.success:
            return ToolResult.text(
                f"✅ Successfully transitioned branch '{params.branch}' "
                f"from {params.from_phase} → {result.new_phase}"
            )

        return ToolResult.error(f"❌ Transition failed: {result.reason}")
