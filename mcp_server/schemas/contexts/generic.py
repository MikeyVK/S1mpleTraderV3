# mcp_server/schemas/contexts/generic.py
# template=schema version=74378193 created=2026-02-17T00:00Z updated=
"""GenericContext schema.

Context schema for generic artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict, Field, field_validator

# Project modules
from mcp_server.schemas.base import BaseContext


class GenericContext(BaseContext):
    """Context schema for generic artifact scaffolding (user-facing).

    User provides generic-specific fields when scaffolding generic Python class artifacts.
    Does NOT include lifecycle fields - those are added by GenericRenderContext.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    name: str = Field(
        description="Name of the class (PascalCase required)",
    )
    description: str | None = Field(
        default=None,
        description="Description of the class's purpose",
    )
    layer: str | None = Field(
        default=None,
        description="Architectural layer (e.g. 'Backend (Generic)', 'MCP Server')",
    )
    methods: list[str] = Field(
        default_factory=list,
        description="List of method names to scaffold",
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="List of responsibility descriptions",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Validate name is not empty."""
        if not v or not v.strip():
            raise ValueError("name must be non-empty string")
        return v
