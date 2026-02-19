# mcp_server/schemas/render_contexts/architecture.py
"""ArchitectureRenderContext schema.

System-enriched context with lifecycle fields for Architecture rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.architecture import ArchitectureContext


class ArchitectureRenderContext(BaseRenderContext, ArchitectureContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: ArchitectureContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - title, concepts, purpose, scope_in, scope_out, prerequisites,
          related_docs, constraints, decisions (from ArchitectureContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
