"""Tests for base tool classes."""

import pytest

from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class TestTool(BaseTool):
    """Test implementation of BaseTool for unit testing."""

    name = "test_tool"
    description = "A test tool"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult.text(f"Executed with {kwargs}")


def test_tool_result_helpers() -> None:
    """Test ToolResult.text and ToolResult.error helper methods."""
    # Test text helper
    result = ToolResult.text("Hello")
    assert result.content[0]["text"] == "Hello"
    assert not result.is_error

    # Test error helper
    error = ToolResult.error("Failed")
    assert error.content[0]["text"] == "Failed"
    assert error.is_error


@pytest.mark.asyncio
async def test_base_tool_execution() -> None:
    """Test that BaseTool execute method works correctly."""
    tool = TestTool()
    result = await tool.execute(param="value")
    assert "value" in result.content[0]["text"]
    assert not result.is_error


def test_base_tool_schema() -> None:
    """Test that BaseTool provides default input schema."""
    tool = TestTool()
    assert tool.input_schema["type"] == "object"
