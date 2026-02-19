# mcp_server/schemas/contexts/tool.py
# template=schema version=74378193 created=2026-02-17T00:00Z updated=
"""ToolContext schema.

Context schema for Tool artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict, Field, field_validator

# Project modules
from mcp_server.schemas.base import BaseContext


class ToolContext(BaseContext):
    """Context schema for Tool artifact scaffolding (user-facing).

    User provides tool-specific fields when scaffolding MCP tool artifacts.
    Does NOT include lifecycle fields - those are added by ToolRenderContext.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    name: str = Field(
        description="Name of the Tool class (PascalCase required)",
    )
    description: str | None = Field(
        default=None,
        description="Description of the tool's purpose",
    )
    layer: str | None = Field(
        default=None,
        description="Architectural layer of the tool",
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="List of tool responsibilities",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Validate name is not empty."""
        if not v or not v.strip():
            raise ValueError("name must be non-empty string")
        return v
