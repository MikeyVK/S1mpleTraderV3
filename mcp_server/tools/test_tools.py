"""Test execution tools."""
import subprocess
import sys
from typing import Any, Dict
from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.core.exceptions import ExecutionError


class RunTestsTool(BaseTool):
    """Tool to run pytest."""

    name = "run_tests"
    description = "Run tests using pytest"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to test file or directory",
                    "default": "tests/"
                },
                "markers": {
                    "type": "string",
                    "description": "Pytest markers to filter by"
                }
            }
        }

    async def execute(
        self, path: str = "tests/", markers: str | None = None, **kwargs: Any
    ) -> ToolResult:
        """Execute the tool."""
        cmd = [sys.executable, "-m", "pytest", path]
        if markers:
            cmd.extend(["-m", markers])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )

            output = result.stdout
            if result.stderr:
                output += "\nSTDERR:\n" + result.stderr

            return ToolResult.text(output)

        except OSError as e:
            raise ExecutionError(f"Failed to run tests: {e}") from e
