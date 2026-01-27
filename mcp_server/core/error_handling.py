"""Global error handling infrastructure for MCP tools.

Provides @tool_error_handler decorator that catches exceptions and converts them
to ToolResult.error() responses with preserved MCPError contract.

Note: this handler intentionally catches only expected/known exception types.
Unexpected exceptions still propagate (so we don't blanket-catch everything).
"""

import functools
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from mcp_server.core.exceptions import (
    ConfigError,
    ExecutionError,
    MCPError,
    MCPSystemError,
    PreflightError,
    ValidationError,
)
from mcp_server.tools.tool_result import ToolResult

logger = logging.getLogger(__name__)

T = TypeVar("T")


def tool_error_handler(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Catch expected tool exceptions and return structured errors."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            result: T = await func(*args, **kwargs)
        except (
            ValidationError,
            PreflightError,
            ExecutionError,
            MCPSystemError,
            ConfigError,
            MCPError,
            ValueError,
            FileNotFoundError,
        ) as exc:
            message = ""
            error_code: str | None = None
            hints: list[str] | None = None
            file_path: str | None = None

            # Preserve MCPError contract
            if isinstance(exc, MCPError):
                message = exc.message
                error_code = exc.code
                hints = exc.hints if exc.hints else None
                # Only ConfigError has file_path attribute
                if isinstance(exc, ConfigError):
                    file_path = exc.file_path

                if isinstance(exc, (ValidationError, PreflightError)):
                    logger.warning("[VALIDATION ERROR] %s: %s", func.__name__, message)
                elif isinstance(exc, ExecutionError):
                    logger.error("[EXECUTION ERROR] %s: %s", func.__name__, message)
                else:
                    logger.exception("[MCP ERROR] %s: %s", func.__name__, message)
            elif isinstance(exc, ValueError):
                message = f"Invalid input: {exc}"
                logger.warning("[USER ERROR] %s: %s", func.__name__, message)
            else:
                # FileNotFoundError
                message = f"Configuration error: {exc}"
                logger.error("[CONFIG ERROR] %s: %s", func.__name__, message)

            # Special handling for ValidationError with schema
            if isinstance(exc, ValidationError) and hasattr(exc, "schema") and exc.schema:
                # Create ToolResult with resource content containing schema
                content: list[dict[str, Any]] = [
                    {"type": "text", "text": message},
                    {
                        "type": "resource",
                        "resource": {
                            "uri": "schema://validation",
                            "mimeType": "application/json",
                            "text": json.dumps(exc.schema.to_dict(), indent=2)
                        }
                    }
                ]
                result = cast(
                    T,
                    ToolResult(
                        content=content,
                        is_error=True,
                        error_code=error_code,
                        hints=hints,
                        file_path=file_path,
                    ),
                )
            else:
                result = cast(
                    T,
                    ToolResult.error(
                        message=message,
                        error_code=error_code,
                        hints=hints,
                        file_path=file_path,
                    ),
                )
        except Exception as exc:  # noqa: BLE001
            message = f"Unexpected error: {type(exc).__name__}: {exc}"
            logger.exception("[BUG] %s: %s", func.__name__, message)
            result = cast(T, ToolResult.error(message))

        return result

    return cast(Callable[..., Awaitable[T]], wrapper)
