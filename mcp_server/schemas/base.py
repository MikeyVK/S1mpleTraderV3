# mcp_server/schemas/base.py
# template=schema version=74378193 created=2026-02-17T09:38Z updated=
"""Base schema classes for Context and RenderContext hierarchies.

Contains:
- BaseContext: Abstract base for all Context schemas (user-facing, artifact-specific)
- BaseRenderContext: Abstract base for all RenderContext schemas (system-enriched with lifecycle)

@layer: Schema Infrastructure
"""

# Third-party
from pydantic import BaseModel, ConfigDict

# Project modules
from mcp_server.schemas.mixins.lifecycle import LifecycleMixin


class BaseContext(BaseModel):
    """Abstract base class for all Context schemas (user-facing, artifact-specific).

    Context schemas define artifact-specific fields that users provide when
    scaffolding artifacts. They do NOT include lifecycle fields (output_path,
    scaffold_created, template_id, version_hash) - those are added by
    BaseRenderContext via LifecycleMixin.

    Usage:
        class WorkerContext(BaseContext):
            worker_name: str
            scope: str
            capabilities: list[str]
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )


class BaseRenderContext(LifecycleMixin, BaseContext):
    """Abstract base class for all RenderContext schemas (system-enriched).

    RenderContext schemas combine artifact-specific fields (from BaseContext)
    with lifecycle fields (from LifecycleMixin). These schemas are NEVER
    user-facing - they are created by ArtifactManager during template scaffolding.

    Inherits:
        - output_path, scaffold_created, template_id, version_hash (from LifecycleMixin)
        - model_config (from BaseContext)

    Usage:
        class WorkerRenderContext(BaseRenderContext, WorkerContext):
            pass  # Inherits all fields from both parents
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )
