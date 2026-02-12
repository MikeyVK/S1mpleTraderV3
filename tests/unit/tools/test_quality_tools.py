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


def _extract_json(result: ToolResult) -> dict[str, Any]:
    """Extract structured JSON from ToolResult (content[0] type=json)."""
    json_item = result.content[0]
    assert json_item["type"] == "json", (
        f"Expected content[0] type='json', got '{json_item['type']}'"
    )
    return json_item["json"]


class TestRunQualityGatesTool:
    """Tests for RunQualityGatesTool."""

    @pytest.mark.asyncio
    async def test_no_files_triggers_project_level(self) -> None:
        """Test files=[] triggers project-level mode (not error)."""
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

        data = _extract_json(result)
        assert data["mode"] == "project-level"
        assert "text_output" in data
        mock_manager.run_quality_gates.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_quality_gates_passed(self) -> None:
        """Test clean quality pass returns JSON with text_output."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "overall_pass": True,
            "gates": [
                {
                    "name": "pylint",
                    "passed": True,
                    "score": 10.0,
                    "issues": [],
                }
            ],
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        data = _extract_json(result)
        assert data["overall_pass"] is True
        assert "text_output" in data
        assert "✅ pylint" in data["text_output"]

    @pytest.mark.asyncio
    async def test_quality_gates_failed_with_issues(self) -> None:
        """Test failed quality gates with issues in JSON output."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
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

        data = _extract_json(result)
        assert data["overall_pass"] is False
        assert "❌ pylint" in data["text_output"]
        assert "foo.py:10:4" in data["text_output"]
        assert "[C0111] Missing docstring" in data["text_output"]

    @pytest.mark.asyncio
    async def test_quality_gates_failed_prints_hints(self) -> None:
        """Test gate hints are surfaced in text_output."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
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

        data = _extract_json(result)
        assert "Hints:" in data["text_output"]
        assert "Re-run:" in data["text_output"]

    @pytest.mark.asyncio
    async def test_quality_gates_issues_missing_fields(self) -> None:
        """Test issue formatting robustness with empty issues."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
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

        data = _extract_json(result)
        assert "unknown:?:?" in data["text_output"]
        assert "Unknown issue" in data["text_output"]

    @pytest.mark.asyncio
    async def test_response_is_native_json_object(self) -> None:
        """Test tool returns native JSON object, not JSON-in-text (P0-AC1)."""
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

        # Content[0] is native JSON object (not merely serialized text)
        assert result.content[0]["type"] == "json"
        data = result.content[0]["json"]
        assert isinstance(data, dict)

        # Content[1] is text fallback for legacy clients
        assert result.content[1]["type"] == "text"
        assert isinstance(result.content[1]["text"], str)

        # Structured fields present in JSON
        assert data["version"] == "2.0"
        assert data["mode"] == "file-specific"
        assert "summary" in data
        assert "gates" in data
        assert "text_output" in data

        # Gate has enriched schema
        gate = data["gates"][0]
        assert "id" in gate
        assert "status" in gate
        assert "skip_reason" in gate

    def test_schema(self) -> None:
        """Test tool schema has files property."""
        tool = RunQualityGatesTool(manager=MagicMock())
        schema = tool.input_schema
        assert "files" in schema["properties"]
