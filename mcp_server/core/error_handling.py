"""
Global error handling infrastructure for MCP tools.

Provides @tool_error_handler decorator that catches exceptions and converts them
to ToolResult.error() responses, preventing VS Code from disabling tools.

@layer: Core Infrastructure
@dependencies: [functools, logging, mcp_server.tools.base]
@responsibilities:
    - Catch all tool exceptions
    - Classify errors (USER/CONFIG/SYSTEM/BUG)
    - Return structured error responses
    - Log errors appropriately
"""

import functools
import logging
from typing import Any, Awaitable, Callable, TypeVar, cast

from mcp_server.tools.base import ToolResult

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
        except Exception as e:  # pylint: disable=broad-exception-caught
            # SYSTEM/BUG - unexpected error (intentionally catch all)
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.exception("[BUG] %s: %s", func.__name__, error_msg)
            return cast(T, ToolResult.error(error_msg))

    return cast(Callable[..., Awaitable[T]], wrapper)
