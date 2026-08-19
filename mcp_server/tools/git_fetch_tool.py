"""Git fetch tool.

Fetch updates from a remote.

Responsibilities:
- Execute potentially blocking GitPython network operations via `anyio.to_thread.run_sync`.
- Return GitFetchOutput instead of raising uncaught exceptions.

Usage example:
- Call `git_fetch` with {"remote": "origin", "prune": false}

@layer: Tools
@dependencies: [GitManager, anyio]
"""

from __future__ import annotations

from typing import Any

import anyio
from pydantic import BaseModel, ConfigDict, Field

from mcp_server.core.exceptions import MCPError
from mcp_server.core.interfaces import ICoreTool
from mcp_server.core.logging import get_logger
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.git_manager import GitManager
from mcp_server.schemas.tool_outputs import GitFetchOutput

logger = get_logger("tools.git_fetch")


class GitFetchInput(BaseModel):
    """Input for GitFetchTool."""

    model_config = ConfigDict(extra="forbid")

    remote: str = Field(
        default="origin",
        description="Remote name to fetch from (default: origin)",
    )
    prune: bool = Field(
        default=False,
        description="Prune deleted remote-tracking branches",
    )


class GitFetchTool(ICoreTool[GitFetchInput, GitFetchOutput]):
    """Fetch updates from a remote.

    Responsibilities:
    - Offload git fetch to a worker thread (Issue #85 stdio hang prevention).
    - Convert known MCPErrors into GitFetchOutput.

    Usage example:
    - Call with {"remote": "origin", "prune": false}
    """

    @property
    def name(self) -> str:
        return "git_fetch"

    @property
    def description(self) -> str:
        return "Fetch updates from a remote"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return GitFetchInput

    def __init__(self, manager: GitManager) -> None:
        self.manager = manager

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitFetchInput, context: NoteContext) -> GitFetchOutput:
        del context  # Read-only fetch — context unused
        try:
            result = await anyio.to_thread.run_sync(
                lambda: self.manager.fetch(remote=params.remote, prune=params.prune)
            )
            return GitFetchOutput(
                success=True,
                remote=params.remote,
                raw_output=result,
                prune=params.prune,
            )
        except MCPError as exc:
            logger.error(
                "git_fetch failed",
                extra={"props": {"remote": params.remote, "error": str(exc)}},
            )
            return GitFetchOutput(
                success=False,
                error_message=str(exc),
                remote=params.remote,
                raw_output="",
                prune=params.prune,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            logger.error(
                "git_fetch failed (runtime)",
                extra={"props": {"remote": params.remote, "error": str(exc)}},
            )
            return GitFetchOutput(
                success=False,
                error_message=f"Fetch failed: {exc}",
                remote=params.remote,
                raw_output="",
                prune=params.prune,
            )


def _input_schema(model: type[BaseModel] | None) -> dict[str, Any]:
    if model is None:
        return {}
    return model.model_json_schema()
