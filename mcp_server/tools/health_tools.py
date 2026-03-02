"""Health check tools."""
from typing import Any

from pydantic import BaseModel

from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class HealthCheckInput(BaseModel):
    """Input for HealthCheckTool."""


class HealthCheckTool(BaseTool):
    """Tool to check server health."""

    name = "health_check"
    description = "Check server health status"
    args_model = HealthCheckInput

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, _params: HealthCheckInput) -> ToolResult:
        return ToolResult.text("OK")
