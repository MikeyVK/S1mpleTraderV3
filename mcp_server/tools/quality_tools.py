"""Quality tools."""

import json
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
        """Execute quality gates and return schema-first JSON response.

        Returns structured JSON as primary output with a derived text_output field.
        Consumers should parse the JSON structure (gates[], summary) for programmatic use.
        The text_output field provides a human-readable rendering for display purposes.
        """
        files = params.files
        # Project-level test validation mode (files=[]):
        # - Runs pytest gates only (Gate 5: tests, Gate 6: coverage >= 90%)
        # - Skips file-based static gates (Gates 0-4: Ruff, Mypy) - no file list provided
        # - Use case: CI/CD test/coverage enforcement before merge
        #
        # File-specific validation mode (files=[...]):
        # - Runs file-based static gates (Gates 0-4: Ruff, Mypy)
        # - Skips pytest gates (Gate 5-6) - tests run at project-level
        # - Use case: IDE save hooks, pre-commit validation on changed files

        result = self.manager.run_quality_gates(files)

        # Build derived text rendering and attach to response
        text_output = self._render_text_output(result)
        result["text_output"] = text_output

        return ToolResult.text(json.dumps(result, indent=2, default=str))

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
