"""Code manipulation tools."""

import warnings
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.config.settings import Settings
from mcp_server.core.exceptions import ExecutionError, ValidationError
from mcp_server.core.operation_notes import NoteContext
from mcp_server.tools.base import BranchMutatingTool
from mcp_server.tools.tool_result import ToolResult


class CreateFileInput(BaseModel):
    """Input for CreateFileTool."""

    path: str = Field(..., description="Relative path to file")
    content: str = Field(..., description="File content")


class CreateFileTool(BranchMutatingTool):
    """Tool to create or overwrite a file.

    .. deprecated::
        Use scaffold_artifact tool instead.
        This tool bypasses project templates and coding standards.
    """

    name = "create_file"
    description = (
        "[DEPRECATED] Create or overwrite a file with content. "
        "Prefer scaffold_artifact for code/document generation."
    )
    args_model = CreateFileInput

    def __init__(
        self,
        settings: Settings | None = None,
        workspace_root: str | Path | None = None,
    ) -> None:
        super().__init__()
        base_workspace = workspace_root or (
            settings.server.workspace_root if settings else Path.cwd()
        )
        self._workspace_root = Path(base_workspace).resolve()

    @property
    def input_schema(self) -> dict[str, Any]:
        if self.args_model is None:
            return {}
        return self.args_model.model_json_schema()

    async def execute(self, params: CreateFileInput, context: NoteContext) -> ToolResult:
        """Execute the tool."""
        del context  # Deprecated tool — context unused
        warnings.warn(
            "create_file is deprecated. Use scaffold_artifact instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        path = params.path
        content = params.content
        full_path = self._workspace_root / path
        try:
            full_path = full_path.resolve()
            if not str(full_path).startswith(str(self._workspace_root)):
                raise ValidationError(f"Access denied: {path} is outside workspace")

            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            return ToolResult.text(f"File created: {path}")

        except ValidationError:
            raise
        except Exception as e:
            raise ExecutionError(f"Failed to create file: {e}") from e
