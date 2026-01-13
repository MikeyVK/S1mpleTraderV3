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


def _create_audit_props(
    reason: str,
    event_type: str,
    **extra_props: Any
) -> dict[str, Any]:
    """Create structured props for audit logging.

    Args:
        reason: Restart reason
        event_type: Type of restart event
        **extra_props: Additional properties to include

    Returns:
        Dictionary with standard audit props
    """
    props = {
        "reason": reason,
        "pid": os.getpid(),
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": event_type
    }
    props.update(extra_props)
    return props


def _parse_marker_file(marker_path: Path) -> dict[str, Any]:
    """Parse restart marker file.

    Args:
        marker_path: Path to marker file

    Returns:
        Dictionary with marker data

    Raises:
        OSError: If file cannot be read
        json.JSONDecodeError: If JSON is invalid
    """
    with marker_path.open(encoding="utf-8") as f:
        marker_data: dict[str, Any] = json.load(f)
        return marker_data


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
        5. Server returns success response
        6. Server schedules exit with code 42 (delayed)
        7. Parent process (VS Code) detects exit and restarts server
        8. Agent calls verify_server_restarted() to confirm
        9. Agent continues with testing/next cycle

        Args:
            params: RestartServerInput with reason field

        Returns:
            ToolResult with success message before server exits.

        Note:
            - Development tool only, not for production use
            - Parent process must handle exit code 42 by restarting server
            - All audit logs flushed before exit (zero data loss)
            - Restart marker written to .st3/.restart_marker
            - Server exits 500ms after returning response (graceful)
        """
        logger = get_logger("tools.admin")

        # Audit log: Restart requested
        restart_time = datetime.now(UTC)
        logger.info(
            "Server restart requested",
            extra={
                "props": _create_audit_props(
                    reason=params.reason,
                    event_type="server_restart_requested"
                )
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
                "props": _create_audit_props(
                    reason=params.reason,
                    event_type="restart_marker_written",
                    marker_path=str(marker_path),
                    marker_content=marker_content
                )
            }
        )

        # Schedule delayed restart in background
        async def delayed_restart() -> None:
            """Restart after short delay to allow response to be sent."""
            await asyncio.sleep(0.5)  # 500ms delay for response to be sent

            # Flush all output (ensure audit logs persisted)
            sys.stdout.flush()
            sys.stderr.flush()

            # Force flush logging handlers
            for handler in logging.root.handlers:
                handler.flush()

            # Audit log: Restarting
            logger.info(
                "Server restarting via os.execv",
                extra={
                    "props": _create_audit_props(
                        reason=params.reason,
                        event_type="server_restarting",
                        method="os.execv"
                    )
                }
            )

            # Final flush
            sys.stdout.flush()
            sys.stderr.flush()

            # Replace current process with new Python interpreter instance
            # This preserves PID and stdio connections (no exit code needed)
            python_exe = sys.executable
            args = [python_exe, "-m", "mcp_server"]
            
            # os.execv replaces the current process - no return from this call
            os.execv(python_exe, args)

        # Start background restart task (fire-and-forget)
        asyncio.create_task(delayed_restart())

        # Return success immediately (before restart happens)
        return ToolResult.text(
            f"Server restart scheduled (reason: {params.reason}). "
            f"Server will restart in-process via os.execv() in 500ms."
        )


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


def verify_server_restarted(since_timestamp: float) -> dict[str, Any]:
    """Verify that server restarted after given timestamp.

    **Purpose:** Allow agent to confirm restart completed before continuing.

    Agent workflow:
    1. Record timestamp: before_restart = time.time()
    2. Call restart_server(reason="...")
    3. [Wait for server to restart]
    4. Call verify_server_restarted(since_timestamp=before_restart)
    5. If restarted=True: Continue with testing
    6. If restarted=False: Error - restart failed

    Args:
        since_timestamp: Unix timestamp before restart request.
                         Server must have restarted AFTER this time.

    Returns:
        Dictionary with verification result:
        {
            "restarted": bool,           # True if restart confirmed
            "restart_timestamp": float,  # When restart occurred
            "current_pid": int,          # Current process ID
            "previous_pid": int,         # PID before restart (from marker)
            "reason": str,               # Restart reason (from marker)
            "time_since_restart": float  # Seconds since restart
        }

    Example:
        before = time.time()
        restart_server(reason="Load changes")
        # [Server restarts]
        result = verify_server_restarted(since_timestamp=before)
        if result["restarted"]:
            print(f"Restart confirmed! Reason: {result['reason']}")
            run_tests(...)
        else:
            raise Exception("Server restart failed!")
    """
    import time

    logger = get_logger("tools.admin")

    marker_path = _get_restart_marker_path()

    # Check if marker exists
    if not marker_path.exists():
        return {
            "restarted": False,
            "error": "Restart marker not found",
            "marker_path": str(marker_path)
        }

    # Parse marker
    try:
        marker_data = _parse_marker_file(marker_path)
    except (OSError, json.JSONDecodeError) as e:
        return {
            "restarted": False,
            "error": f"Failed to parse restart marker: {e}"
        }

    restart_timestamp = marker_data["timestamp"]

    # Check if restart happened after since_timestamp
    restarted = restart_timestamp > since_timestamp

    result = {
        "restarted": restarted,
        "restart_timestamp": restart_timestamp,
        "current_pid": os.getpid(),
        "previous_pid": marker_data["pid"],
        "reason": marker_data["reason"],
        "time_since_restart": time.time() - restart_timestamp,
        "iso_time": marker_data["iso_time"]
    }

    # Audit log verification
    logger.info(
        "Server restart verification",
        extra={
            "props": {
                "result": result,
                "since_timestamp": since_timestamp
            }
        }
    )

    return result
