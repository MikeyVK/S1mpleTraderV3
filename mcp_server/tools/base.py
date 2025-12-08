"""Base class for MCP tools."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    """Result of a tool execution."""
    content: List[Dict[str, Any]] = Field(default_factory=list)
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
    """Abstract base class for all tools."""

    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool."""
        pass

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for input parameters.

        Subclasses should override this to provide specific schema definitions,
        or we can implement automatic schema generation from the execute method signature
        in the future.
        """
        return {
            "type": "object",
            "properties": {},
        }
