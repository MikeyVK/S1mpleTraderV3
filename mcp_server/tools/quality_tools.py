"""Quality tools."""
from typing import Any

from mcp_server.managers.qa_manager import QAManager
from mcp_server.tools.base import BaseTool, ToolResult


class RunQualityGatesTool(BaseTool):
    """Tool to run quality gates."""

    name = "run_quality_gates"
    description = "Run quality gates on files"

    def __init__(self, manager: QAManager | None = None) -> None:
        self.manager = manager or QAManager()

    @property
    def input_schema(self) -> dict[str, Any]:
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

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute quality gates."""
        files = kwargs.get("files", [])
        if not files:
            return ToolResult.text("❌ No files provided")

        result = self.manager.run_quality_gates(files)

        text = "Quality Gates Results:\n"
        text += f"Overall Pass: {result['overall_pass']}\n"
        for gate in result['gates']:
            status = "✅" if gate['passed'] else "❌"
            text += f"\n{status} {gate['name']}: {gate['score']}\n"
            if not gate['passed'] and gate.get('issues'):
                text += "  Issues:\n"
                for issue in gate['issues']:
                    # Format: ❌ file.py:10: [CODE] Message
                    loc = (
                        f"{issue.get('file', 'unknown')}:"
                        f"{issue.get('line', '?')}:"
                        f"{issue.get('column', '?')}"
                    )
                    code = f"[{issue.get('code', 'MISC')}] " if 'code' in issue else ""
                    msg = issue.get('message', 'Unknown issue')
                    text += f"  - {loc} {code}{msg}\n"

        return ToolResult.text(text)
