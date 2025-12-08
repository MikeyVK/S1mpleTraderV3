"""Tests for QA integration."""
import pytest
from mcp_server.managers.qa_manager import QAManager
from mcp_server.tools.quality_tools import RunQualityGatesTool

def test_qa_manager_run_gates():
    manager = QAManager()
    result = manager.run_quality_gates(["test.py"])

    assert result["overall_pass"] is True
    assert len(result["gates"]) == 2

@pytest.mark.asyncio
async def test_quality_tool():
    manager = QAManager()
    tool = RunQualityGatesTool(manager=manager)

    result = await tool.execute(files=["test.py"])
    assert "Overall Pass: True" in result.content[0]["text"]
