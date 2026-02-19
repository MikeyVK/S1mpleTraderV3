# mcp_server/schemas/contexts/research.py
# template=schema version=74378193 created=2026-02-18T00:00Z updated=
"""ResearchContext schema.

Context schema for Research document artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import Field

# Project modules
from mcp_server.schemas.contexts.doc_base import DocArtifactContext


class ResearchContext(DocArtifactContext):
    """Context schema for Research document artifact scaffolding (user-facing).

    Covers required fields per concrete/research.md.jinja2 TEMPLATE_METADATA.
    Lifecycle fields (output_path, version_hash, etc.) added by ResearchRenderContext.

    Inherits:
        - title (from DocArtifactContext, with non-empty validation)
    """

    problem_statement: str = Field(description="Problem or question being investigated")
    goals: list[str] = Field(description="Research goals / questions to answer")
    purpose: str | None = Field(default=None, description="Purpose of this research document")
    scope_in: str | None = Field(default=None, description="What is in scope")
    scope_out: str | None = Field(default=None, description="What is out of scope")
    prerequisites: list[str] = Field(
        default_factory=list,
        description="Prerequisites or prior knowledge required",
    )
    background: str | None = Field(default=None, description="Background context and prior art")
    findings: str | None = Field(default=None, description="Findings and conclusions so far")
    questions_list: list[str] = Field(
        default_factory=list, description="Open questions remaining after research"
    )
    references: list[str] = Field(default_factory=list, description="External references and links")
    related_docs: list[str] = Field(
        default_factory=list, description="Related documents in the project"
    )
