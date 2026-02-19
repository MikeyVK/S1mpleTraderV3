# mcp_server/schemas/render_contexts/research.py
"""ResearchRenderContext schema.

System-enriched context with lifecycle fields for Research template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.research import ResearchContext


class ResearchRenderContext(BaseRenderContext, ResearchContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: ResearchContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - title, problem_statement, goals, purpose, scope_in, scope_out,
          prerequisites, background, findings, questions_list, references,
          related_docs (from ResearchContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
