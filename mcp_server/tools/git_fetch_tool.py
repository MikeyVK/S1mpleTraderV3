"""Git fetch tool.

Fetch updates from a remote.

Responsibilities:
- Execute potentially blocking GitPython network operations via `anyio.to_thread.run_sync`.
- Return a structured ToolResult error instead of raising uncaught exceptions.

Usage example:
- Call `git_fetch` with {"remote": "origin", "prune": false}

@layer: Tools
@dependencies: [GitManager, anyio]
"""

from __future__ import annotations

from typing import Any

import anyio
from pydantic import BaseModel, Field

from mcp_server.core.exceptions import MCPError
from mcp_server.core.logging import get_logger
from mcp_server.managers.git_manager import GitManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult

logger = get_logger("tools.git_fetch")


def _input_schema(args_model: type[BaseModel] | None) -> dict[str, Any]:
    if args_model is None:
        return {}
    return args_model.model_json_schema()


class GitFetchInput(BaseModel):
    """Input for GitFetchTool."""

    remote: str = Field(
        default="origin",
        description="Remote name to fetch from (default: origin)",
    )
    prune: bool = Field(
        default=False,
        description="Prune deleted remote-tracking branches",
    )


class GitFetchTool(BaseTool):
    """Fetch updates from a remote.

    Responsibilities:
    - Offload git fetch to a worker thread (Issue #85 stdio hang prevention).
    - Convert known MCPErrors into ToolResult.error.

    Usage example:
    - Call with {"remote": "origin", "prune": false}
    """

    name = "git_fetch"
    description = "Fetch updates from a remote"
    args_model = GitFetchInput

    def __init__(self, manager: GitManager | None = None) -> None:
        self.manager = manager or GitManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return _input_schema(self.args_model)

    async def execute(self, params: GitFetchInput) -> ToolResult:
        try:
            result = await anyio.to_thread.run_sync(
                lambda: self.manager.fetch(remote=params.remote, prune=params.prune)
            )
            return ToolResult.text(result)
        except MCPError as exc:
            logger.error(
                "git_fetch failed",
                extra={"props": {"remote": params.remote, "error": str(exc)}},
            )
            return ToolResult.error(str(exc))
        except (OSError, ValueError, RuntimeError) as exc:
            logger.error(
                "git_fetch failed (runtime)",
                extra={"props": {"remote": params.remote, "error": str(exc)}},
            )
            return ToolResult.error(f"Fetch failed: {exc}")
