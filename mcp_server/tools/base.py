"""Base class for MCP tools."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from mcp_server.core.error_handling import tool_error_handler
from mcp_server.tools.tool_result import ToolResult


class BaseTool(ABC):
    """Abstract base class for all tools.

    Subclasses must override execute() with a single parameters argument
    typed as their specific Pydantic model (InputModel).

    Error handling is automatically applied via @tool_error_handler decorator.
    """

    name: str
    description: str
    args_model: type[BaseModel] | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Automatically wrap execute() with error handler on subclass creation."""

        super().__init_subclass__(**kwargs)

        # Wrap the execute method with error handler if not already wrapped
        if hasattr(cls.execute, "__wrapped__"):
            return  # Already wrapped

        original_execute = cls.execute
        cls.execute = tool_error_handler(original_execute)  # type: ignore[assignment]

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
