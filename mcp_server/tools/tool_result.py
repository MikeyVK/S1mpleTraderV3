"""Tool execution result model."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Result of a tool execution."""

    content: list[dict[str, Any]] = Field(default_factory=list)
    is_error: bool = False
    error_code: str | None = None
    hints: list[str] | None = None
    file_path: str | None = None

    @classmethod
    def text(cls, text: str) -> ToolResult:
        """Create a text result."""

        return cls(content=[{"type": "text", "text": text}])

    @classmethod
    def json_data(cls, data: dict[str, Any]) -> ToolResult:
        """Create a JSON result with both structured and text content.

        Returns a ToolResult containing two content items:
        1. A JSON object (type: "json") for machine consumption.
        2. A serialized text fallback (type: "text") for clients that
           only support text content.

        Args:
            data: Structured dict to return as JSON.
        """
        text_fallback = json.dumps(data, indent=2, default=str)
        return cls(
            content=[
                {"type": "json", "json": data},
                {"type": "text", "text": text_fallback},
            ]
        )

    @classmethod
    def error(
        cls,
        message: str,
        error_code: str | None = None,
        hints: list[str] | None = None,
        file_path: str | None = None,
    ) -> ToolResult:
        """Create an error result with structured error information."""

        return cls(
            content=[{"type": "text", "text": message}],
            is_error=True,
            error_code=error_code,
            hints=hints,
            file_path=file_path,
        )
