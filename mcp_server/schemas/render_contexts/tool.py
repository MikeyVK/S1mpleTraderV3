# mcp_server/schemas/render_contexts/tool.py
# template=schema version=74378193 created=2026-02-17T00:00Z updated=
"""ToolRenderContext schema.

System-enriched context with lifecycle fields for Tool template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.tool import ToolContext


class ToolRenderContext(BaseRenderContext, ToolContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: ToolContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - name, description, layer, responsibilities (from ToolContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
