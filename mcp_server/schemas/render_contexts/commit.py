# mcp_server/schemas/render_contexts/commit.py
"""CommitRenderContext schema.

System-enriched context with lifecycle fields for Commit template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.commit import CommitContext


class CommitRenderContext(BaseRenderContext, CommitContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: CommitContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - type, message, scope, body, breaking_change, breaking_description,
          footer, refs (from CommitContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        populate_by_name=True,
    )

    # No additional fields - composition via multiple inheritance
    pass
