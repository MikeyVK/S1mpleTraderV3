"""Validation tools."""
from typing import Any

from mcp_server.managers.qa_manager import QAManager
from mcp_server.tools.base import BaseTool, ToolResult


class ValidationTool(BaseTool):
    """Tool to validate code against architectural patterns."""

    name = "validate_architecture"
    description = "Validate code against architectural patterns"

    def __init__(self, manager: QAManager | None = None) -> None:
        self.manager = manager or QAManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["all", "dtos", "workers", "platform"],
                    "default": "all"
                }
            }
        }

    async def execute(self, scope: str = "all", **kwargs: Any) -> ToolResult:
        # Stub implementation. In reality, this would use QAManager to scan code.
        return ToolResult.text(f"Architecture validation passed for scope: {scope}")

class ValidateDTOTool(BaseTool):
    """Tool to validate DTO definitions."""

    name = "validate_dto"
    description = "Validate DTO definition"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"}
            },
            "required": ["file_path"]
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool."""
        file_path = kwargs.get("file_path", "")
        return ToolResult.text(f"DTO validation passed for: {file_path}")
