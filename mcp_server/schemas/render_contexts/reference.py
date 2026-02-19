# mcp_server/schemas/render_contexts/reference.py
"""ReferenceRenderContext schema.

System-enriched context with lifecycle fields for Reference template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.reference import ReferenceContext


class ReferenceRenderContext(BaseRenderContext, ReferenceContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: ReferenceContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - title, source_file, test_file, api_reference, usage_examples,
          test_count (from ReferenceContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
