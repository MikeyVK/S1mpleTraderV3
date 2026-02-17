"""Transition tools for TDD cycle management.

Issue #146 Cycle 4: transition_cycle and force_cycle_transition tools.
"""

from typing import Any

from pydantic import BaseModel, Field

from mcp_server.config.settings import settings
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
        # RED: Minimal implementation to make tests fail
        return ToolResult.error("Not implemented yet")
