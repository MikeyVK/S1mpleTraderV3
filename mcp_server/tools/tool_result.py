"""Tool execution result model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Result of a tool execution."""

    content: list[dict[str, Any]] = Field(default_factory=list)
    is_error: bool = False

    @classmethod
    def text(cls, text: str) -> "ToolResult":
        """Create a text result."""

        return cls(content=[{"type": "text", "text": text}])

    @classmethod
    def error(cls, message: str) -> "ToolResult":
        """Create an error result."""

        return cls(content=[{"type": "text", "text": message}], is_error=True)
