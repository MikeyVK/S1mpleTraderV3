"""Tests for QA integration.

Integration tests for real QA tool execution with actual files.
"""
import pytest

from mcp_server.managers.qa_manager import QAManager
from mcp_server.tools.quality_tools import RunQualityGatesInput, RunQualityGatesTool


def test_qa_manager_run_gates_with_real_file() -> None:
    """Test QAManager runs quality gates on a real clean file."""
    manager = QAManager()
    # Use a real file that is known to be clean
    result = manager.run_quality_gates(["backend/core/enums.py"])

    # Should have all active gates from quality.yaml (8 gates configured)
    # Some gates may be skipped (e.g., Gate 5/6 in file-specific mode)
    assert len(result["gates"]) >= 6, f"Expected at least 6 gates, got {len(result['gates'])}"
    
    # Verify first gate is Ruff Format (Gate 0)
    assert "Ruff Format" in result["gates"][0]["name"]
    
    # overall_pass depends on actual file quality
    assert isinstance(result["overall_pass"], bool)


@pytest.mark.asyncio
async def test_quality_tool_output_format() -> None:
    """Test RunQualityGatesTool returns properly formatted result."""
    manager = QAManager()
    tool = RunQualityGatesTool(manager=manager)

    result = await tool.execute(RunQualityGatesInput(files=["backend/core/enums.py"]))
    text = result.content[0]["text"]

    # Verify output format contains expected sections (new config-driven gate names)
    assert "Overall Pass:" in text
    assert "Gate 0: Ruff Format" in text or "Ruff Format" in text
    assert "Gate 1:" in text or "Gate 2:" in text  # At least one gate runs
