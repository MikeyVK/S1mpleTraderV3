# mcp_server/schemas/contexts/dto.py
# template=schema version=74378193 created=2026-02-17T14:09Z updated=
"""DTOContext schema.

Context schema for DTO artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict, Field, field_validator

# Project modules
from mcp_server.schemas.base import BaseContext


class DTOContext(BaseContext):
    """Context schema for DTO artifact scaffolding (user-facing).

    User provides DTO-specific fields when scaffolding DTO artifacts.
    Does NOT include lifecycle fields - those are added by DTORenderContext.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    dto_name: str = Field(
        description="Name of the DTO class (PascalCase required)",
    )
    fields: list[str] = Field(
        default_factory=list,
        description="List of field definitions (format: 'name: type')",
    )

    @field_validator("dto_name")
    @classmethod
    def validate_dto_name_not_empty(cls, v: str) -> str:
        """Validate dto_name is not empty."""
        if not v or not v.strip():
            raise ValueError("dto_name must be non-empty string")
        return v

    @field_validator("fields")
    @classmethod
    def validate_fields_is_list(cls, v: list[str]) -> list[str]:
        """Validate fields is list (catches string input)."""
        if isinstance(v, str):
            raise ValueError("fields must be list[str], not string")
        return v
