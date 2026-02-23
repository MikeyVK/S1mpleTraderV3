# tests/mcp_server/unit/tools/test_tool_result_contract.py
"""
C27: ToolResult content contract for RunQualityGatesTool.

Contract (planning.md Cycle 27):
  content[0] = {"type": "text", "text": <summary_line>}   — human-readable one-liner
  content[1] = {"type": "json", "json": <compact_payload>} — structured gate results
  len(content) == 2 — exactly two items, no more
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from mcp_server.tools.quality_tools import RunQualityGatesInput, RunQualityGatesTool


def _make_qg_result(
    passed: int = 1,
    failed: int = 0,
    skipped: int = 0,
    gate_name: str = "Gate 0: Ruff Format",
) -> dict[str, Any]:
    """Build a minimal run_quality_gates result dict."""
    status = "failed" if failed > 0 else ("skipped" if skipped > 0 else "passed")
    return {
        "version": "2.0",
        "mode": "file-specific",
        "files": ["foo.py"],
        "summary": {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total_violations": 0,
            "auto_fixable": 0,
        },
        "gates": [
            {
                "id": 1,
                "name": gate_name,
                "passed": status != "failed",
                "status": status,
                "skip_reason": None,
                "score": "Pass" if status == "passed" else "Fail",
                "issues": [],
            }
        ],
        "overall_pass": failed == 0,
    }


class TestToolResultContentContract:
    """content[0] must be text; content[1] must be json; exactly two items."""

    @pytest.mark.asyncio
    async def test_content_has_exactly_two_items(self) -> None:
        """ToolResult must contain exactly two content items."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = _make_qg_result()
        tool = RunQualityGatesTool(manager=mock_manager)

        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        assert len(result.content) == 2, f"Expected 2 content items, got {len(result.content)}"

    @pytest.mark.asyncio
    async def test_content_zero_is_text(self) -> None:
        """content[0] must be type='text' (human-readable summary line)."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = _make_qg_result()
        tool = RunQualityGatesTool(manager=mock_manager)

        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        assert result.content[0]["type"] == "text", (
            f"content[0] must be 'text', got '{result.content[0]['type']}'"
        )

    @pytest.mark.asyncio
    async def test_content_one_is_json(self) -> None:
        """content[1] must be type='json' (compact structured payload)."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = _make_qg_result()
        tool = RunQualityGatesTool(manager=mock_manager)

        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        assert result.content[1]["type"] == "json", (
            f"content[1] must be 'json', got '{result.content[1]['type']}'"
        )

    @pytest.mark.asyncio
    async def test_text_item_contains_summary_line(self) -> None:
        """content[0].text must be the one-line summary from _format_summary_line."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = _make_qg_result(
            passed=1, failed=0, skipped=0
        )
        tool = RunQualityGatesTool(manager=mock_manager)

        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        text = result.content[0]["text"]
        assert "✅" in text or "❌" in text or "⚠️" in text, (
            f"Summary line must start with status emoji, got: {text!r}"
        )
        assert "Quality gates" in text

    @pytest.mark.asyncio
    async def test_json_item_has_compact_schema(self) -> None:
        """content[1].json must have compact schema: {'gates': [...]}."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = _make_qg_result()
        tool = RunQualityGatesTool(manager=mock_manager)

        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        payload = result.content[1]["json"]
        assert isinstance(payload, dict)
        assert "gates" in payload, f"Compact payload must have 'gates' key, got: {payload.keys()}"

    @pytest.mark.asyncio
    async def test_compact_json_gate_has_no_debug_fields(self) -> None:
        """content[1].json gates must not contain debug fields like command or duration_ms."""
        mock_manager = MagicMock()
        result_data = _make_qg_result()
        result_data["gates"][0]["command"] = {"executable": "ruff"}
        result_data["gates"][0]["duration_ms"] = 145
        mock_manager.run_quality_gates.return_value = result_data
        tool = RunQualityGatesTool(manager=mock_manager)

        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        gate = result.content[1]["json"]["gates"][0]
        assert "command" not in gate, "command must not appear in compact payload"
        assert "duration_ms" not in gate, "duration_ms must not appear in compact payload"
