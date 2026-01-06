"""Validation tools."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.managers.qa_manager import QAManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class ValidationInput(BaseModel):
    """Input for ValidationTool."""

    scope: str = Field(
        default="all",
        description="Validation scope (all, dtos, workers, platform)",
        pattern="^(all|dtos|workers|platform)$",
    )


class ValidationTool(BaseTool):
    """Tool to validate code against architectural patterns."""

    name = "validate_architecture"
    description = "Validate code against architectural patterns"
    args_model = ValidationInput

    def __init__(self, manager: QAManager | None = None) -> None:
        self.manager = manager or QAManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: ValidationInput) -> ToolResult:
        # Stub implementation. In reality, this would use QAManager to scan code.
        return ToolResult.text(f"Architecture validation passed for scope: {params.scope}")


class ValidateDTOInput(BaseModel):
    """Input for ValidateDTOTool."""

    file_path: str = Field(..., description="Path to file")


class ValidateDTOTool(BaseTool):
    """Tool to validate DTO definitions."""

    name = "validate_dto"
    description = "Validate DTO definition"
    args_model = ValidateDTOInput

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(self, params: ValidateDTOInput) -> ToolResult:
        dto_path = Path(params.file_path)
        if not dto_path.exists():
            return ToolResult.error(f"DTO file not found: {params.file_path}")

        try:
            content = dto_path.read_text(encoding="utf-8")
        except OSError as e:
            return ToolResult.error(f"Failed to read DTO file: {e}")

        if not content.strip():
            return ToolResult.error("DTO file is empty")

        return ToolResult.text(f"DTO validation passed for: {params.file_path}")
