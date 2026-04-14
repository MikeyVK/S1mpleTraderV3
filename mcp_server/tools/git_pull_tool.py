"""Git pull tool.

Pull updates from a remote into the current branch.

Responsibilities:
- Execute potentially blocking GitPython network operations via `anyio.to_thread.run_sync`.
- Enforce safe-by-default behavior via GitManager preflight.
- Re-sync PhaseStateEngine state after a successful pull.

Usage example:
- Call `git_pull` with {"remote": "origin", "rebase": false}

@layer: Tools
@dependencies: [GitManager, PhaseStateEngine, anyio]
"""

from __future__ import annotations

from typing import Any

import anyio
from pydantic import BaseModel, Field

from mcp_server.core.exceptions import MCPError
from mcp_server.core.logging import get_logger
from mcp_server.managers import phase_state_engine
from mcp_server.managers.git_manager import GitManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult
from mcp_server.core.operation_notes import NoteContext

logger = get_logger("tools.git_pull")


def _input_schema(args_model: type[BaseModel] | None) -> dict[str, Any]:
    if args_model is None:
        return {}
    return args_model.model_json_schema()


class GitPullInput(BaseModel):
    """Input for GitPullTool."""

    remote: str = Field(
        default="origin",
        description="Remote name to pull from (default: origin)",
    )
    rebase: bool = Field(
        default=False,
        description="Use --rebase instead of merge",
    )


class GitPullTool(BaseTool):
    """Pull updates from a remote into the current branch.

    Responsibilities:
    - Offload git pull to a worker thread (Issue #85 stdio hang prevention).
    - Re-sync PhaseStateEngine after pull to reduce state drift.

    Usage example:
    - Call with {"remote": "origin", "rebase": false}
    """

    name = "git_pull"
    description = "Pull updates from a remote"
    args_model = GitPullInput

    def __init__(
        self,
        manager: GitManager,
        state_engine: phase_state_engine.PhaseStateEngine | None = None,
    ) -> None:
        self.manager = manager
        self._state_engine = state_engine

    def _get_state_engine(self) -> phase_state_engine.PhaseStateEngine:
        if self._state_engine is None:
            raise ValueError("PhaseStateEngine must be injected for git_pull")
        return self._state_engine

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitPullInput, _context: NoteContext | None = None) -> ToolResult:
        try:
            pull_result = await anyio.to_thread.run_sync(
                lambda: self.manager.pull(remote=params.remote, rebase=params.rebase)
            )
        except MCPError as exc:
            logger.error(
                "git_pull failed",
                extra={"props": {"remote": params.remote, "error": str(exc)}},
            )
            return ToolResult.error(str(exc))
        except (OSError, ValueError, RuntimeError) as exc:
            logger.error(
                "git_pull failed (runtime)",
                extra={"props": {"remote": params.remote, "error": str(exc)}},
            )
            return ToolResult.error(f"Pull failed: {exc}")

        # Sync phase state after pull (commits may have changed).
        try:
            current_branch = self.manager.get_current_branch()
            await anyio.to_thread.run_sync(self._get_state_engine().get_state, current_branch)
        except (MCPError, ValueError, OSError) as exc:
            logger.warning(
                "Phase state sync failed after pull",
                extra={"props": {"error": str(exc)}},
            )

        return ToolResult.text(pull_result)
