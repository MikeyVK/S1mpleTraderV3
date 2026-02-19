# mcp_server/schemas/contexts/worker.py
# template=schema version=74378193 created=2026-02-17T00:00Z updated=
"""WorkerContext schema.

Context schema for Worker artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict, Field, field_validator

# Project modules
from mcp_server.schemas.base import BaseContext


class WorkerContext(BaseContext):
    """Context schema for Worker artifact scaffolding (user-facing).

    User provides worker-specific fields when scaffolding worker artifacts.
    Does NOT include lifecycle fields - those are added by WorkerRenderContext.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    name: str = Field(
        description="Name of the Worker class (PascalCase required)",
    )
    layer: str = Field(
        description="Architectural layer (platform|strategy|platform_within_strategy)",
    )
    module_description: str | None = Field(
        default=None,
        description="Description of the worker module",
    )
    worker_scope: str | None = Field(
        default=None,
        description="Worker scope (platform|strategy|platform_within_strategy)",
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="List of worker responsibilities",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of required capabilities (dependency injection)",
    )
    use_async: bool = Field(
        default=False,
        description="If True, scaffold async warmup example",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Validate name is not empty."""
        if not v or not v.strip():
            raise ValueError("name must be non-empty string")
        return v

    @field_validator("layer")
    @classmethod
    def validate_layer_not_empty(cls, v: str) -> str:
        """Validate layer is not empty."""
        if not v or not v.strip():
            raise ValueError("layer must be non-empty string")
        return v
