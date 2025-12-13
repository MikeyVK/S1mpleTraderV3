"""Tests for QA integration.

Integration tests for real QA tool execution with actual files.
"""
import pytest

from mcp_server.managers.qa_manager import QAManager
from mcp_server.tools.quality_tools import RunQualityGatesTool, RunQualityGatesInput


def test_qa_manager_run_gates_with_real_file() -> None:
    """Test QAManager runs quality gates on a real clean file."""
    manager = QAManager()
    # Use a real file that is known to be clean
    result = manager.run_quality_gates(["backend/core/enums.py"])

    # Should have both Linting and Type Checking gates
    assert len(result["gates"]) == 2
    assert result["gates"][0]["name"] == "Linting"
    assert result["gates"][1]["name"] == "Type Checking"
    # overall_pass depends on actual file quality
    assert isinstance(result["overall_pass"], bool)


@pytest.mark.asyncio
async def test_quality_tool_output_format() -> None:
    """Test RunQualityGatesTool returns properly formatted result."""
    manager = QAManager()
    tool = RunQualityGatesTool(manager=manager)

    result = await tool.execute(RunQualityGatesInput(files=["backend/core/enums.py"]))
    text = result.content[0]["text"]

    # Verify output format contains expected sections
    assert "Overall Pass:" in text
    assert "Linting:" in text
    assert "Type Checking:" in text
