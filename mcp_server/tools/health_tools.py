"""Health check tools."""
from typing import Any
from mcp_server.tools.base import BaseTool, ToolResult

class HealthCheckTool(BaseTool):
    """Tool to check server health."""

    name = "health_check"
    description = "Check server health status"

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult.text("OK")
