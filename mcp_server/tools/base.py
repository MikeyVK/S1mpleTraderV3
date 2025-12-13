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
    
    Subclasses must override execute() with a single parameters argument
    typed as their specific Pydantic model (InputModel).
    """

    name: str
    description: str
    args_model: type[BaseModel] | None = None

    @abstractmethod
    async def execute(self, params: Any) -> ToolResult:
        """Execute the tool.
        
        Args:
            params: Validated Pydantic model instance containing arguments.
        """

    @property
    def input_schema(self) -> dict[str, Any]:
        """Get the JSON schema for input parameters."""
        # Retrieve schema from args_model if available
        if self.args_model:
            return self.args_model.model_json_schema()
            
        return {
            "type": "object",
            "properties": {},
        }
