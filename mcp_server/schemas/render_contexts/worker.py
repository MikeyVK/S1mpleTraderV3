# mcp_server/schemas/render_contexts/worker.py
# template=schema version=74378193 created=2026-02-17T00:00Z updated=
"""WorkerRenderContext schema.

System-enriched context with lifecycle fields for Worker template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.worker import WorkerContext


class WorkerRenderContext(BaseRenderContext, WorkerContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: WorkerContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - name, layer, module_description, worker_scope, responsibilities,
          capabilities, use_async (from WorkerContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
