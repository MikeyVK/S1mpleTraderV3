# mcp_server/schemas/render_contexts/unit_test.py
# template=schema version=74378193 created=2026-02-17T00:00Z updated=
"""UnitTestRenderContext schema.

System-enriched context with lifecycle fields for test_unit template rendering (internal use ONLY)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.base import BaseRenderContext
from mcp_server.schemas.contexts.unit_test import UnitTestContext


class UnitTestRenderContext(BaseRenderContext, UnitTestContext):
    """System-enriched context with lifecycle fields (internal use ONLY).

    This schema is NEVER exposed to users. ArtifactManager creates instances
    via _enrich_context transformation: UnitTestContext + lifecycle fields.
    Templates receive this schema for rendering.

    Inherits:
        - module_under_test, test_class_name, test_description, has_mocks,
          has_async_tests, has_pydantic, test_methods (from UnitTestContext)
        - output_path, scaffold_created, template_id, version_hash
          (from LifecycleMixin via BaseRenderContext)
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
    )

    # No additional fields - composition via multiple inheritance
    pass
