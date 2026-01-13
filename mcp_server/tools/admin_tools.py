"""Administrative tools for server management.

Development tools for agent-driven workflows. Enables agents to:
- Restart server to load code changes
- Verify restart occurred
- Maintain audit trail of server lifecycle events
"""

import asyncio
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.core.logging import get_logger
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


# Constants
RESTART_MARKER_PATH = Path(".st3/.restart_marker")


# Helper functions
def _get_restart_marker_path() -> Path:
    """Get the restart marker file path.

    Returns:
        Path to .st3/.restart_marker file
    """
    return RESTART_MARKER_PATH


class RestartServerInput(BaseModel):
    """Input for RestartServerTool."""

    reason: str = Field(
        default="code changes",
        description="Description of why restart is needed (for audit logging)"
    )


class RestartServerTool(BaseTool):
    """Tool to restart MCP server to reload code changes.

    **Purpose:** Enable agent autonomy during TDD workflows.

    Agent can implement code changes and restart server without human
    intervention, allowing fully autonomous test-driven development cycles.
    """

    name = "restart_server"
    description = "Restart MCP server to reload code changes"
    args_model = RestartServerInput

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return the input schema for the tool."""
        if self.args_model is None:
            return {}
        return self.args_model.model_json_schema()

    async def execute(self, params: RestartServerInput) -> ToolResult:
        """Execute server restart.

        **Workflow:**
        1. Agent makes code changes (via safe_edit_file)
        2. Agent calls restart_server(reason="...")
        3. Server logs restart to audit trail
        4. Server writes restart marker file
        5. Server exits with code 42 (restart requested)
        6. Parent process (VS Code) restarts server
        7. Agent calls verify_server_restarted() to confirm
        8. Agent continues with testing/next cycle

        Args:
            params: RestartServerInput with reason field

        Returns:
            ToolResult (may not be delivered if exit is immediate).
            Agent should use verify_server_restarted() to confirm restart.

        Note:
            - Development tool only, not for production use
            - Parent process must handle exit code 42 by restarting server
            - All audit logs flushed before exit (zero data loss)
            - Restart marker written to .st3/.restart_marker
        """
        logger = get_logger("tools.admin")

        # Audit log: Restart requested
        restart_time = datetime.now(UTC)
        logger.info(
            "Server restart requested",
            extra={
                "props": {
                    "reason": params.reason,
                    "pid": os.getpid(),
                    "timestamp": restart_time.isoformat(),
                    "event_type": "server_restart_requested"
                }
            }
        )

        # Write restart marker file (for verification)
        marker_path = _get_restart_marker_path()
        marker_path.parent.mkdir(exist_ok=True)
        marker_content = {
            "timestamp": restart_time.timestamp(),
            "pid": os.getpid(),
            "reason": params.reason,
            "iso_time": restart_time.isoformat()
        }

        marker_path.write_text(
            json.dumps(marker_content, indent=2),
            encoding="utf-8"
        )

        # Audit log: Marker written
        logger.info(
            "Restart marker written",
            extra={
                "props": {
                    "marker_path": str(marker_path),
                    "marker_content": marker_content
                }
            }
        )

        # Flush all output (ensure audit logs persisted)
        sys.stdout.flush()
        sys.stderr.flush()

        # Force flush logging handlers
        for handler in logging.root.handlers:
            handler.flush()

        # Audit log: Exiting
        logger.info(
            "Server exiting for restart",
            extra={
                "props": {
                    "exit_code": 42,
                    "reason": params.reason
                }
            }
        )

        # Final flush
        sys.stdout.flush()
        sys.stderr.flush()

        # Exit with code 42 = "please restart me"
        # Parent process should detect this and restart server
        sys.exit(42)


# Convenience function for backward compatibility and testing
def restart_server(reason: str = "code changes") -> None:
    """Restart MCP server (convenience function).

    This is a simple wrapper around RestartServerTool for easier testing.
    In production, use the tool via MCP protocol.

    Args:
        reason: Description of why restart is needed
    """
    tool = RestartServerTool()
    params = RestartServerInput(reason=reason)
    asyncio.run(tool.execute(params))
