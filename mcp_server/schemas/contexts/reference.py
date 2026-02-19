# mcp_server/schemas/contexts/reference.py
# template=schema version=74378193 created=2026-02-18T00:00Z updated=
"""ReferenceContext schema.

Context schema for Reference document artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import Field

# Project modules
from mcp_server.schemas.contexts.doc_base import DocArtifactContext


class ReferenceContext(DocArtifactContext):
    """Context schema for Reference document artifact scaffolding (user-facing).

    Covers required fields per concrete/reference.md.jinja2 TEMPLATE_METADATA.
    Lifecycle fields (output_path, version_hash, etc.) added by ReferenceRenderContext.

    Inherits:
        - title (from DocArtifactContext, with non-empty validation)
    """

    source_file: str = Field(description="Path to the implementation source file")
    test_file: str = Field(description="Path to the test file")
    api_reference: list[dict[str, str]] = Field(
        description="API reference items (each has 'name' and 'description' keys)"
    )
    usage_examples: str | None = Field(default=None, description="Usage examples and code snippets")
    test_count: int | None = Field(default=None, description="Number of tests for this component")
