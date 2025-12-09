"""Base class for MCP tools."""
from abc import ABC, abstractmethod
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


class BaseTool(ABC):
    """Abstract base class for all tools.
    
    Subclasses can override execute() with explicit parameters while
    still calling parent signature via **kwargs at runtime.
    """

    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool.
        
        Subclasses may override with explicit parameters, e.g.:
            async def execute(self, issue_number: int, **kwargs: Any) -> ToolResult
        
        The **kwargs ensures compatibility with the abstract method while
        allowing type checkers to permit explicit parameters in subclasses.
        """

    @property
    def input_schema(self) -> dict[str, Any]:
        """Get the JSON schema for input parameters.

        Subclasses should override this to provide specific schema definitions,
        or we can implement automatic schema generation from the execute method
        signature in the future.
        """
        return {
            "type": "object",
            "properties": {},
        }
