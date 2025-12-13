"""Documentation tools."""
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.managers.doc_manager import DocManager
from mcp_server.tools.base import BaseTool, ToolResult


class ValidateDocInput(BaseModel):
    """Input for ValidateDocTool."""
    content: str = Field(..., description="Document content")
    template_type: str = Field(..., description="Template type")


class ValidateDocTool(BaseTool):
    """Tool to validate documentation."""

    name = "validate_document_structure"
    description = "Validate document structure"
    args_model = ValidateDocInput

    def __init__(self, manager: DocManager | None = None) -> None:
        self.manager = manager or DocManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: ValidateDocInput) -> ToolResult:
        result = self.manager.validate_structure(params.content, params.template_type)
        return ToolResult.text(f"Validation result: {result}")
