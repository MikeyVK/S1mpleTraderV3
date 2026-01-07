"""Code manipulation tools."""
import warnings
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.config.settings import settings
from mcp_server.core.exceptions import ExecutionError, ValidationError
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class CreateFileInput(BaseModel):
    """Input for CreateFileTool."""
    path: str = Field(..., description="Relative path to file")
    content: str = Field(..., description="File content")


class CreateFileTool(BaseTool):
    """Tool to create or overwrite a file.

    .. deprecated::
        Use scaffold_component or scaffold_design_doc tools instead.
        This tool bypasses project templates and coding standards.
    """

    name = "create_file"
    description = (
        "[DEPRECATED] Create or overwrite a file with content. "
        "Prefer scaffold_component for code generation."
    )
    args_model = CreateFileInput

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: CreateFileInput) -> ToolResult:
        """Execute the tool."""
        # Emit deprecation warning
        warnings.warn(
            "create_file is deprecated. Use scaffold_component or scaffold_design_doc instead.",
            DeprecationWarning,
            stacklevel=2
        )

        path = params.path
        content = params.content

        # Security check: ensure path is within workspace
        # pylint: disable=no-member
        full_path = Path(settings.server.workspace_root) / path
        try:
            full_path = full_path.resolve()
            workspace = Path(settings.server.workspace_root).resolve()

            if not str(full_path).startswith(str(workspace)):
                raise ValidationError(f"Access denied: {path} is outside workspace")

            # Create directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            return ToolResult.text(f"File created: {path}")

        except ValidationError:
            raise
        except Exception as e:
            raise ExecutionError(f"Failed to create file: {e}") from e
