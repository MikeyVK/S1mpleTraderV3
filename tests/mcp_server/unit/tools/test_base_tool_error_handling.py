"""
Integration tests for error handling with actual MCP tools.

Tests that @tool_error_handler is automatically applied to all tools
via BaseTool.__init_subclass__.
"""

from typing import Any

import pytest

from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class TestToolErrorHandlingIntegration:
    """Integration tests for error handling with real tool classes."""

    @pytest.mark.asyncio
    async def test_tool_with_value_error_returns_error_result(self) -> None:
        """Tool raising ValueError should return ToolResult.error."""

        class TestTool(BaseTool):
            """Test tool."""

            name = "test_tool"
            description = "Test tool"

            async def execute(self, params: Any) -> ToolResult:  # noqa: ANN401, ARG002
                raise ValueError("Invalid parameter")

        tool = TestTool()
        result = await tool.execute({})

        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "Invalid input" in str(result)

    @pytest.mark.asyncio
    async def test_successful_tool_returns_normal_result(self) -> None:
        """Successful tool execution should return normal ToolResult."""

        class TestTool(BaseTool):
            """Test tool."""

            name = "test_tool"
            description = "Test tool"

            async def execute(self, params: Any) -> ToolResult:  # noqa: ANN401, ARG002
                return ToolResult.text("Success!")

        tool = TestTool()
        result = await tool.execute({})

        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert "Success!" in str(result)

    @pytest.mark.asyncio
    async def test_error_handler_applied_to_multiple_tools(self) -> None:
        """Error handler should be automatically applied to all BaseTool subclasses."""

        class Tool1(BaseTool):
            """Tool 1."""

            name = "tool1"
            description = "Tool 1"

            async def execute(self, params: Any) -> ToolResult:  # noqa: ANN401, ARG002
                raise ValueError("Tool1 error")

        class Tool2(BaseTool):
            """Tool 2."""

            name = "tool2"
            description = "Tool 2"

            async def execute(self, params: Any) -> ToolResult:  # noqa: ANN401, ARG002
                raise FileNotFoundError("Tool2 error")

        tool1 = Tool1()
        tool2 = Tool2()

        result1 = await tool1.execute({})
        result2 = await tool2.execute({})

        # Both should return errors, not raise exceptions
        assert result1.is_error
        assert result2.is_error
