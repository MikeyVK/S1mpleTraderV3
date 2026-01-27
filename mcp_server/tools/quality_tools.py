"""Quality tools."""
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.managers.qa_manager import QAManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class RunQualityGatesInput(BaseModel):
    """Input for RunQualityGatesTool."""
    files: list[str] = Field(..., description="List of files to check")


class RunQualityGatesTool(BaseTool):
    """Tool to run quality gates."""

    name = "run_quality_gates"
    description = "Run quality gates on files"
    args_model = RunQualityGatesInput

    def __init__(self, manager: QAManager | None = None) -> None:
        self.manager = manager or QAManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        """Get input schema for the tool."""
        if self.args_model is None:
            return {}
        return self.args_model.model_json_schema()

    async def execute(self, params: RunQualityGatesInput) -> ToolResult:
        """Execute quality gates."""
        files = params.files
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
