# mcp_server/schemas/render_contexts/dto.py
# template=schema version=74378193 created=2026-02-17T14:09Z updated=
"""DTORenderContext schema.

System-enriched context with lifecycle fields for DTO template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.dto import DTOContext


class DTORenderContext(BaseRenderContext, DTOContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: DTOContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - dto_name, fields (from DTOContext)
        - output_path, scaffold_created, template_id, version_hash (from LifecycleMixin via BaseRenderContext)

    Note:
        V2 template (dto_v2.py.jinja2) uses {{ dto_name }} directly.
        V1 template (dto.py.jinja2) uses {{ name }}; the TemplateScaffolder injects
        artifact_type, format, timestamp etc. at render time (see scaffold() method).
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
