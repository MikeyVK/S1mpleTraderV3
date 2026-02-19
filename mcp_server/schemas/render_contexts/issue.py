# mcp_server/schemas/render_contexts/issue.py
"""IssueRenderContext schema.

System-enriched context with lifecycle fields for Issue template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.issue import IssueContext


class IssueRenderContext(BaseRenderContext, IssueContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: IssueContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - title, problem, summary, expected, actual, context, steps_to_reproduce,
          related_docs, labels, milestone, assignees (from IssueContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
