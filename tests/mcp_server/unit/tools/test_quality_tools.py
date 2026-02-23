# tests/unit/mcp_server/tools/test_quality_tools.py
"""Tests for quality tools."""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false

# Standard library
from typing import Any
from unittest.mock import MagicMock

# Third-party
import pytest

# Module under test
from mcp_server.tools.quality_tools import RunQualityGatesInput, RunQualityGatesTool
from mcp_server.tools.tool_result import ToolResult


def _summary_text(result: ToolResult) -> str:
    """Extract summary text from content[0] (type='text')."""
    item = result.content[0]
    assert item["type"] == "text", f"Expected content[0] type='text', got '{item['type']}'"
    return item["text"]


def _compact_payload(result: ToolResult) -> dict[str, Any]:
    """Extract compact JSON payload from content[1] (type='json')."""
    item = result.content[1]
    assert item["type"] == "json", f"Expected content[1] type='json', got '{item['type']}'"
    return item["json"]


class TestRunQualityGatesTool:
    """Tests for RunQualityGatesTool."""

    @pytest.mark.asyncio
    async def test_no_files_triggers_project_level(self) -> None:
        """Test files=[] is forwarded to manager and summary text is returned."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "version": "2.0",
            "mode": "project-level",
            "files": [],
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 3,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "gates": [
                {
                    "name": "Tests",
                    "passed": True,
                    "status": "passed",
                    "score": "Pass",
                    "issues": [],
                }
            ],
            "overall_pass": True,
        }
        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(files=[]))

        text = _summary_text(result)
        assert "Quality gates" in text
        mock_manager.run_quality_gates.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_quality_gates_passed(self) -> None:
        """Test clean quality pass returns ✅ summary line."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "overall_pass": True,
            "gates": [
                {
                    "name": "pylint",
                    "passed": True,
                    "status": "passed",
                    "score": 10.0,
                    "issues": [],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        text = _summary_text(result)
        assert "✅" in text

    @pytest.mark.asyncio
    async def test_quality_gates_failed_with_issues(self) -> None:
        """Test failed quality gates returns ❌ summary line."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "total_violations": 1,
                "auto_fixable": 0,
            },
            "overall_pass": False,
            "gates": [
                {
                    "name": "pylint",
                    "passed": False,
                    "status": "failed",
                    "score": 5.0,
                    "issues": [
                        {
                            "file": "foo.py",
                            "line": 10,
                            "column": 4,
                            "code": "C0111",
                            "message": "Missing docstring",
                        }
                    ],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        text = _summary_text(result)
        assert "❌" in text

    @pytest.mark.asyncio
    async def test_quality_gates_failed_prints_hints(self) -> None:
        """Test gate with hints — summary line is still returned."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "total_violations": 1,
                "auto_fixable": 0,
            },
            "overall_pass": False,
            "gates": [
                {
                    "name": "Gate 3: Line Length",
                    "passed": False,
                    "status": "failed",
                    "score": "Fail",
                    "issues": [{"message": "E501"}],
                    "hints": ["Re-run: python -m ruff check file.py"],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        text = _summary_text(result)
        assert "❌" in text
        assert "Quality gates" in text

    @pytest.mark.asyncio
    async def test_quality_gates_issues_missing_fields(self) -> None:
        """Test result with empty issues dict — summary line is returned without crash."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "summary": {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "overall_pass": False,
            "gates": [
                {
                    "name": "check",
                    "passed": False,
                    "status": "failed",
                    "score": 0,
                    "issues": [{}],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        text = _summary_text(result)
        assert "Quality gates" in text

    @pytest.mark.asyncio
    async def test_response_is_native_json_object(self) -> None:
        """Tool returns text summary at content[0], compact JSON at content[1]."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "version": "2.0",
            "mode": "file-specific",
            "files": ["foo.py"],
            "summary": {
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "gates": [
                {
                    "id": 1,
                    "name": "Gate 0: Ruff Format",
                    "passed": True,
                    "status": "passed",
                    "skip_reason": None,
                    "score": "Pass",
                    "issues": [],
                }
            ],
            "overall_pass": True,
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        # content[0] is text summary
        assert result.content[0]["type"] == "text"
        assert isinstance(result.content[0]["text"], str)

        # content[1] is compact JSON payload
        assert result.content[1]["type"] == "json"
        data = result.content[1]["json"]
        assert isinstance(data, dict)
        assert "gates" in data

    def test_schema(self) -> None:
        """Test tool schema has files property."""
        tool = RunQualityGatesTool(manager=MagicMock())
        schema = tool.input_schema
        assert "files" in schema["properties"]
