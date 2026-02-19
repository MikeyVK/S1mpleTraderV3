# mcp_server/schemas/contexts/schema.py
# template=schema version=74378193 created=2026-02-17T00:00Z updated=
"""SchemaContext schema.

Context schema for config_schema artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict, Field, field_validator

# Project modules
from mcp_server.schemas.base import BaseContext


class SchemaContext(BaseContext):
    """Context schema for config_schema artifact scaffolding (user-facing).

    User provides schema-specific fields when scaffolding Pydantic config schema artifacts.
    Does NOT include lifecycle fields - those are added by SchemaRenderContext.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    name: str = Field(
        description="Name of the Schema class (PascalCase required)",
    )
    description: str | None = Field(
        default=None,
        description="Description of the schema's purpose",
    )
    layer: str | None = Field(
        default=None,
        description="Architectural layer of the schema",
    )
    fields: list[str] = Field(
        default_factory=list,
        description="List of field definitions (format: 'name: type')",
    )
    frozen: bool = Field(
        default=True,
        description="If True, generate frozen=True in model_config (immutable config)",
    )
    examples: list[str] = Field(
        default_factory=list,
        description="Example values for self-documentation",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Validate name is not empty."""
        if not v or not v.strip():
            raise ValueError("name must be non-empty string")
        return v
