# mcp_server/schemas/render_contexts/planning.py
"""PlanningRenderContext schema.

System-enriched context with lifecycle fields for Planning template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.planning import PlanningContext


class PlanningRenderContext(BaseRenderContext, PlanningContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: PlanningContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - title, summary, tdd_cycles, purpose, scope_in, scope_out,
          prerequisites, dependencies, risks, milestones, related_docs
          (from PlanningContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
