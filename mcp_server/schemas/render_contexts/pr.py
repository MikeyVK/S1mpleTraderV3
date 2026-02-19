# mcp_server/schemas/render_contexts/pr.py
"""PRRenderContext schema.

System-enriched context with lifecycle fields for PR template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.pr import PRContext


class PRRenderContext(BaseRenderContext, PRContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: PRContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - title, changes, summary, testing, checklist_items, related_docs,
          closes_issues, breaking_changes (from PRContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
