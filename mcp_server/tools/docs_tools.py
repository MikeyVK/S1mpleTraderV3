"""Documentation tools."""
from typing import Any

from mcp_server.managers.doc_manager import DocManager
from mcp_server.tools.base import BaseTool, ToolResult


class ValidateDocTool(BaseTool):
    """Tool to validate documentation."""

    name = "validate_document_structure"
    description = "Validate document structure"

    def __init__(self, manager: DocManager | None = None) -> None:
        self.manager = manager or DocManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "template_type": {"type": "string"}
            },
            "required": ["content", "template_type"]
        }

    async def execute(  # type: ignore[override] # pylint: disable=arguments-differ
        self,
        content: str,
        template_type: str,
        **kwargs: Any
    ) -> ToolResult:
        result = self.manager.validate_structure(content, template_type)
        return ToolResult.text(f"Validation result: {result}")
