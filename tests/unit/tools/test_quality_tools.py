# tests/unit/mcp_server/tools/test_quality_tools.py
"""Tests for quality tools."""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false

# Standard library
from unittest.mock import MagicMock

# Third-party
import pytest

# Module under test
from mcp_server.tools.quality_tools import RunQualityGatesTool, RunQualityGatesInput


class TestRunQualityGatesTool:
    """Tests for RunQualityGatesTool."""

    @pytest.mark.asyncio
    async def test_no_files_provided(self) -> None:
        """Test error when no files provided."""
        tool = RunQualityGatesTool(manager=MagicMock())
        result = await tool.execute(RunQualityGatesInput(files=[]))
        assert "No files provided" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_quality_gates_passed(self) -> None:
        """Test clean quality pass."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "overall_pass": True,
            "gates": [
                {"name": "pylint", "passed": True, "score": 10.0}
            ]
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        assert "✅ pylint" in result.content[0]["text"]
        assert "Overall Pass: True" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_quality_gates_failed_with_issues(self) -> None:
        """Test failed quality gates with issues."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "overall_pass": False,
            "gates": [
                {
                    "name": "pylint",
                    "passed": False,
                    "score": 5.0,
                    "issues": [
                        {
                            "file": "foo.py",
                            "line": 10,
                            "column": 4,
                            "code": "C0111",
                            "message": "Missing docstring"
                        }
                    ]
                }
            ]
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        text = result.content[0]["text"]
        assert "❌ pylint" in text
        assert "Overall Pass: False" in text
        assert "foo.py:10:4" in text
        assert "[C0111] Missing docstring" in text

    @pytest.mark.asyncio
    async def test_quality_gates_issues_missing_fields(self) -> None:
        """Test issue formatting robustness."""
        mock_manager = MagicMock()
        mock_manager.run_quality_gates.return_value = {
            "overall_pass": False,
            "gates": [
                {
                    "name": "check",
                    "passed": False,
                    "score": 0,
                    "issues": [{}]  # Empty issue dict
                }
            ]
        }

        tool = RunQualityGatesTool(manager=mock_manager)
        result = await tool.execute(RunQualityGatesInput(files=["foo.py"]))

        text = result.content[0]["text"]
        assert "unknown:?:?" in text
        assert "Unknown issue" in text

    def test_schema(self) -> None:
        """Test tool schema."""
        tool = RunQualityGatesTool(manager=MagicMock())
        schema = tool.input_schema
        assert "files" in schema["properties"]
        assert "files" in schema["required"]
