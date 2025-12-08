"""Code manipulation tools."""
import os
from typing import Any, Dict
from pathlib import Path
from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.core.exceptions import ExecutionError, ValidationError
from mcp_server.config.settings import settings

class CreateFileTool(BaseTool):
    """Tool to create or overwrite a file."""

    name = "create_file"
    description = "Create or overwrite a file with content"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to file"},
                "content": {"type": "string", "description": "File content"}
            },
            "required": ["path", "content"]
        }

    async def execute(self, path: str, content: str, **kwargs: Any) -> ToolResult:
        """Execute the tool."""
        # Security check: ensure path is within workspace
        # This is a basic check. Real implementation should be more robust against traversal.

        full_path = Path(settings.server.workspace_root) / path
        try:
            full_path = full_path.resolve()
            workspace = Path(settings.server.workspace_root).resolve()

            if not str(full_path).startswith(str(workspace)):
                raise ValidationError(f"Access denied: {path} is outside workspace")

            # Create directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w") as f:
                f.write(content)

            return ToolResult.text(f"File created: {path}")

        except ValidationError:
            raise
        except Exception as e:
            raise ExecutionError(f"Failed to create file: {e}") from e
