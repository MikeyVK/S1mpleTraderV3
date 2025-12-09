"""Tests for base tool classes."""
import pytest

from mcp_server.tools.base import BaseTool, ToolResult


class TestTool(BaseTool):
    name = "test_tool"
    description = "A test tool"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult.text(f"Executed with {kwargs}")

def test_tool_result_helpers():
    # Test text helper
    result = ToolResult.text("Hello")
    assert result.content[0]["text"] == "Hello"
    assert not result.is_error

    # Test error helper
    error = ToolResult.error("Failed")
    assert error.content[0]["text"] == "Failed"
    assert error.is_error

@pytest.mark.asyncio
async def test_base_tool_execution():
    tool = TestTool()
    result = await tool.execute(param="value")
    assert "value" in result.content[0]["text"]
    assert not result.is_error

def test_base_tool_schema():
    tool = TestTool()
    assert tool.input_schema["type"] == "object"
