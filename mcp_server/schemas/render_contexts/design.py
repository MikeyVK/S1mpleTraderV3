# mcp_server/schemas/render_contexts/design.py
"""DesignRenderContext schema.

System-enriched context with lifecycle fields for Design template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.design import DesignContext


class DesignRenderContext(BaseRenderContext, DesignContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: DesignContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - title, status, version, problem_statement, requirements_functional,
          requirements_nonfunctional, decision, rationale, purpose, scope_in,
          scope_out, prerequisites, related_docs, constraints (from DesignContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
