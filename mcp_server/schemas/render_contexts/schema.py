# mcp_server/schemas/render_contexts/schema.py
# template=schema version=74378193 created=2026-02-17T00:00Z updated=
"""SchemaRenderContext schema.

System-enriched context with lifecycle fields for config_schema
template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.schema import SchemaContext


class SchemaRenderContext(BaseRenderContext, SchemaContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: SchemaContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - name, description, layer, fields, frozen, examples (from SchemaContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
