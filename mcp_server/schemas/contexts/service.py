# mcp_server/schemas/contexts/service.py
# template=schema version=74378193 created=2026-02-17T00:00Z updated=
"""ServiceContext schema.

Context schema for service_command artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict, Field, field_validator

# Project modules
from mcp_server.schemas.base import BaseContext


class ServiceContext(BaseContext):
    """Context schema for service_command artifact scaffolding (user-facing).

    User provides service-specific fields when scaffolding service command artifacts.
    Does NOT include lifecycle fields - those are added by ServiceRenderContext.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    name: str = Field(
        description="Name of the Service command class (PascalCase required)",
    )
    description: str | None = Field(
        default=None,
        description="Description of the service command's purpose",
    )
    layer: str | None = Field(
        default=None,
        description="Architectural layer of the service",
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="List of service responsibilities",
    )
    parameters: list[str] = Field(
        default_factory=list,
        description="List of parameter definitions (format: 'name: type')",
    )
    return_type: str | None = Field(
        default=None,
        description="Return type annotation for the execute() method",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Validate name is not empty."""
        if not v or not v.strip():
            raise ValueError("name must be non-empty string")
        return v
