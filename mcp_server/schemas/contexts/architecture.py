# mcp_server/schemas/contexts/architecture.py
# template=schema version=74378193 created=2026-02-18T00:00Z updated=
"""ArchitectureContext schema.

Context schema for Architecture document artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import Field

# Project modules
from mcp_server.schemas.contexts.doc_base import DocArtifactContext


class ArchitectureContext(DocArtifactContext):
    """Context schema for Architecture document artifact scaffolding (user-facing).

    Covers required fields per concrete/architecture.md.jinja2 TEMPLATE_METADATA.
    Lifecycle fields (output_path, version_hash, etc.) added by ArchitectureRenderContext.

    Inherits:
        - title (from DocArtifactContext, with non-empty validation)
    """

    concepts: list[str] = Field(
        description="Architectural concepts to document (WHAT and WHY, not HOW)"
    )
    purpose: str | None = Field(default=None, description="Purpose of this architecture document")
    scope_in: str | None = Field(default=None, description="What is in scope")
    scope_out: str | None = Field(default=None, description="What is out of scope")
    prerequisites: list[str] = Field(
        default_factory=list, description="Prerequisites and background knowledge"
    )
    related_docs: list[str] = Field(
        default_factory=list, description="Related documents in the project"
    )
    constraints: list[str] = Field(
        default_factory=list, description="Architectural constraints and boundaries"
    )
    decisions: list[str] = Field(
        default_factory=list, description="Key architectural decisions made"
    )
