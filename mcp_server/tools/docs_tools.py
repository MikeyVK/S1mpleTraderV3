"""Documentation tools."""
from typing import Any, Dict
from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.managers.doc_manager import DocManager

class ValidateDocTool(BaseTool):
    """Tool to validate documentation."""

    name = "validate_document_structure"
    description = "Validate document structure"

    def __init__(self, manager: DocManager | None = None) -> None:
        self.manager = manager or DocManager()

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "template_type": {"type": "string"}
            },
            "required": ["content", "template_type"]
        }

    async def execute(self, content: str, template_type: str, **kwargs: Any) -> ToolResult:
        result = self.manager.validate_structure(content, template_type)
        return ToolResult.text(f"Validation result: {result}")
