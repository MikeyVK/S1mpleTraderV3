"""Quality tools."""

from typing import Any

from pydantic import BaseModel, Field

from mcp_server.managers.qa_manager import QAManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class RunQualityGatesInput(BaseModel):
    """Input for RunQualityGatesTool."""

    files: list[str] = Field(
        default=[],
        description=(
            "List of files to check. Empty list [] = project-level test validation "
            "(pytest/coverage only, Gates 5-6). Populated list = file-specific validation "
            "(static analysis Gates 0-4, skip pytest)."
        ),
    )


class RunQualityGatesTool(BaseTool):
    """Tool to run quality gates."""

    name = "run_quality_gates"
    description = (
        "Run quality gates. Use files=[] for project-level test validation (pytest/coverage), "
        "files=[...] for file-specific validation (static analysis on specified files)."
    )
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
        """Execute quality gates and return contract-compliant response.

        Returns exactly two content items (design.md §4.8, planning.md C27):
        1. ``{"type": "text", "text": <summary_line>}`` — one-line human-readable status
        2. ``{"type": "json", "json": <compact_payload>}`` — structured gate results

        Args:
            params: Tool input parameters.

        Returns:
            ToolResult with content[0]=text summary, content[1]=compact JSON payload.
        """
        result = self.manager.run_quality_gates(params.files)
        summary_line = QAManager._format_summary_line(result)
        compact_payload = QAManager._build_compact_result(result)
        return ToolResult(
            content=[
                {"type": "text", "text": summary_line},
                {"type": "json", "json": compact_payload},
            ]
        )

    @staticmethod
    def _render_text_output(result: dict[str, Any]) -> str:
        """Render structured result as human-readable text (derived view)."""
        mode = result.get("mode", "unknown")
        summary = result.get("summary", {})

        text = f"Quality Gates Results (mode: {mode}):\n"
        text += (
            f"Summary: {summary.get('passed', 0)} passed, "
            f"{summary.get('failed', 0)} failed, "
            f"{summary.get('skipped', 0)} skipped"
        )
        total_v = summary.get("total_violations", 0)
        auto_f = summary.get("auto_fixable", 0)
        if total_v:
            text += f" | {total_v} violations ({auto_f} auto-fixable)"
        text += "\n"
        text += f"Overall Pass: {result.get('overall_pass', False)}\n"

        for gate in result.get("gates", []):
            status = gate.get("status", "passed" if gate.get("passed") else "failed")
            if status == "skipped":
                icon = "⏭️"
            elif status == "passed":
                icon = "✅"
            else:
                icon = "❌"
            text += f"\n{icon} {gate['name']}: {gate.get('score', 'N/A')}\n"

            if status == "failed" and gate.get("issues"):
                text += "  Issues:\n"
                for issue in gate["issues"]:
                    loc = (
                        f"{issue.get('file', 'unknown')}:"
                        f"{issue.get('line', '?')}:"
                        f"{issue.get('column', '?')}"
                    )
                    code = f"[{issue.get('code', 'MISC')}] " if "code" in issue else ""
                    msg = issue.get("message", "Unknown issue")
                    text += f"  - {loc} {code}{msg}\n"

            if status == "failed" and gate.get("hints"):
                text += "  Hints:\n"
                for hint in gate["hints"]:
                    text += f"  - {hint}\n"

        return text
