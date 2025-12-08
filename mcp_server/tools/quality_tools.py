"""Quality tools."""
from typing import Any, Dict
from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.managers.qa_manager import QAManager

class RunQualityGatesTool(BaseTool):
    """Tool to run quality gates."""

    name = "run_quality_gates"
    description = "Run quality gates on files"

    def __init__(self, manager: QAManager | None = None) -> None:
        self.manager = manager or QAManager()

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of files to check"
                }
            },
            "required": ["files"]
        }

    async def execute(self, files: list[str], **kwargs: Any) -> ToolResult:
        result = self.manager.run_quality_gates(files)

        text = "Quality Gates Results:\n"
        text += f"Overall Pass: {result['overall_pass']}\n"
        for gate in result['gates']:
            status = "✅" if gate['passed'] else "❌"
            text += f"{status} {gate['name']}: {gate['score']}\n"

        return ToolResult.text(text)
