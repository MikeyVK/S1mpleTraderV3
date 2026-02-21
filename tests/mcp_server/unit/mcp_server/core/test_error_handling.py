"""
Tests for error_handling decorator.

Tests the @tool_error_handler decorator that prevents VS Code from
disabling MCP tools when exceptions occur.
"""

import pytest

from mcp_server.core.error_handling import tool_error_handler
from mcp_server.tools.tool_result import ToolResult


class TestToolErrorHandler:
    """Tests for @tool_error_handler decorator."""

    @pytest.mark.asyncio
    async def test_value_error_returns_error_result(self) -> None:
        """ValueError should be caught and returned as ToolResult.error (USER error)."""

        @tool_error_handler
        async def failing_tool() -> ToolResult:
            raise ValueError("Invalid input parameter")

        result = await failing_tool()

        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "Invalid input" in str(result)

    @pytest.mark.asyncio
    async def test_file_not_found_returns_error_result(self) -> None:
        """FileNotFoundError should be caught and returned as ToolResult.error (CONFIG error)."""

        @tool_error_handler
        async def failing_tool() -> ToolResult:
            raise FileNotFoundError("Config file missing")

        result = await failing_tool()

        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "Configuration error" in str(result) or "Config file missing" in str(result)

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error_result(self) -> None:
        """Generic exceptions should be caught and returned as ToolResult.error (BUG)."""

        @tool_error_handler
        async def failing_tool() -> ToolResult:
            raise RuntimeError("Unexpected error")

        result = await failing_tool()

        assert isinstance(result, ToolResult)
        assert result.is_error
        assert "Unexpected error" in str(result) or "RuntimeError" in str(result)

    @pytest.mark.asyncio
    async def test_successful_execution_passthrough(self) -> None:
        """Successful tool execution should pass through unchanged."""

        @tool_error_handler
        async def working_tool() -> ToolResult:
            return ToolResult.text("Success!")

        result = await working_tool()

        assert isinstance(result, ToolResult)
        assert not result.is_error
        assert "Success!" in str(result)

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self) -> None:
        """Decorator should preserve function name and docstring."""

        @tool_error_handler
        async def my_tool() -> ToolResult:
            """My tool docstring."""
            return ToolResult.text("OK")

        assert my_tool.__name__ == "my_tool"
        assert "My tool docstring" in (my_tool.__doc__ or "")

    @pytest.mark.asyncio
    async def test_decorator_with_args_and_kwargs(self) -> None:
        """Decorator should work with functions that have args and kwargs."""

        @tool_error_handler
        async def tool_with_params(param1: str, param2: int = 42) -> ToolResult:
            return ToolResult.text(f"{param1}-{param2}")

        result = await tool_with_params("test", param2=99)

        assert isinstance(result, ToolResult)
        assert "test-99" in str(result)
