"""
Global error handling infrastructure for MCP tools.

Provides @tool_error_handler decorator that catches exceptions and converts them
to ToolResult.error() responses, preventing VS Code from disabling tools.

## Problem Solved

When MCP tools raise uncaught exceptions, VS Code's MCP client interprets this as
a tool crash and permanently disables the tool for the session. This decorator
ensures all exceptions are caught and converted to structured error responses,
keeping tools available.

## Automatic Application

All tools inheriting from BaseTool automatically have this decorator applied via
the __init_subclass__ hook. No manual decoration needed.

## Error Classification

Exceptions are classified into categories for appropriate logging:
- ValueError → USER error (warning level) - invalid user input
- FileNotFoundError → CONFIG error (error level) - configuration issue
- Other exceptions → BUG (exception level) - unexpected errors

@layer: Core Infrastructure
@dependencies: [functools, logging, mcp_server.tools.base]
@responsibilities:
    - Catch all tool exceptions
    - Classify errors (USER/CONFIG/SYSTEM/BUG)
    - Return structured error responses
    - Log errors appropriately

Example:
    # Tool implementation - no explicit error handling needed
    class MyTool(BaseTool):
        async def execute(self, params: MyInput) -> ToolResult:
            if not params.value:
                raise ValueError("value is required")  # Caught automatically
            return ToolResult.text("Success!")

    # The decorator is automatically applied by BaseTool.__init_subclass__
    # Exceptions are caught and returned as ToolResult.error()
    # Tools remain "enabled" in VS Code
"""

import functools
import logging
from typing import Any, Awaitable, Callable, TypeVar, cast


logger = logging.getLogger(__name__)

T = TypeVar('T')


def tool_error_handler(
    func: Callable[..., Awaitable[T]]
) -> Callable[..., Awaitable[T]]:
    """Decorator that catches all tool exceptions and returns structured errors.

    Prevents VS Code from disabling tools by converting exceptions into
    valid ToolResult.error() responses.

    Usage:
        @tool_error_handler
        async def execute(self, params: SomeInput) -> ToolResult:
            # Tool implementation
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        # Import here to avoid circular import at module load time.
        from mcp_server.tools.base import ToolResult  # noqa: PLC0415

        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            # USER error - invalid input
            error_msg = f"Invalid input: {str(e)}"
            logger.warning("[USER ERROR] %s: %s", func.__name__, error_msg)
            return cast(T, ToolResult.error(error_msg))
        except FileNotFoundError as e:
            # CONFIG error - missing file
            error_msg = f"Configuration error: {str(e)}"
            logger.error("[CONFIG ERROR] %s: %s", func.__name__, error_msg)
            return cast(T, ToolResult.error(error_msg))
        except Exception as e:
            # SYSTEM/BUG - unexpected error (intentionally catch all)
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.exception("[BUG] %s: %s", func.__name__, error_msg)
            return cast(T, ToolResult.error(error_msg))

    return cast(Callable[..., Awaitable[T]], wrapper)
