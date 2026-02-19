# mcp_server/schemas/contexts/design.py
# template=schema version=74378193 created=2026-02-18T00:00Z updated=
"""DesignContext schema.

Context schema for Design document artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import Field

# Project modules
from mcp_server.schemas.contexts.doc_base import DocArtifactContext


class DesignContext(DocArtifactContext):
    """Context schema for Design document artifact scaffolding (user-facing).

    Covers required fields per concrete/design.md.jinja2 TEMPLATE_METADATA.
    Lifecycle fields (output_path, version_hash, etc.) added by DesignRenderContext.

    Inherits:
        - title (from DocArtifactContext, with non-empty validation)
    """

    status: str = Field(description="Document status (DRAFT|APPROVED|DEFINITIVE)")
    version: str = Field(description="Document version (e.g. 1.0, 2.3)")
    problem_statement: str = Field(description="Problem being solved by this design")
    requirements_functional: list[str] = Field(
        description="Functional requirements the design must satisfy"
    )
    requirements_nonfunctional: list[str] = Field(
        description="Non-functional requirements (performance, maintainability, etc.)"
    )
    decision: str = Field(description="The chosen design decision")
    rationale: str = Field(description="Rationale for the chosen decision")
    purpose: str | None = Field(default=None, description="Purpose of this design document")
    scope_in: str | None = Field(default=None, description="What is in scope")
    scope_out: str | None = Field(default=None, description="What is out of scope")
    prerequisites: list[str] = Field(
        default_factory=list, description="Prerequisites for this design"
    )
    related_docs: list[str] = Field(
        default_factory=list, description="Related documents in the project"
    )
    constraints: list[str] = Field(
        default_factory=list, description="Technical or business constraints"
    )
