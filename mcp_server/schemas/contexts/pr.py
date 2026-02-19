# mcp_server/schemas/contexts/pr.py
# template=schema version=74378193 created=2026-02-18T00:00Z updated=
"""PRContext schema.

Context schema for Pull Request tracking artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict, Field

# Project modules
from mcp_server.schemas.contexts.titled_base import TitledArtifactContext


class PRContext(TitledArtifactContext):
    """Context schema for Pull Request tracking artifact scaffolding (user-facing).

    Covers required fields per concrete/pr.md.jinja2 TEMPLATE_METADATA.
    Inherits `title` field and `validate_title_not_empty` from TitledArtifactContext.
    Lifecycle fields (output_path, version_hash, etc.) added by PRRenderContext.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    # Required fields (title inherited from TitledArtifactContext)
    changes: str = Field(description="Description of changes in this PR")

    # Optional fields
    summary: str | None = Field(default=None, description="High-level PR summary")
    testing: str | None = Field(default=None, description="Testing strategy and results")
    checklist_items: list[str] = Field(
        default_factory=list, description="Checklist items for PR completion"
    )
    related_docs: list[str] = Field(default_factory=list, description="Related documentation links")
    closes_issues: list[int] = Field(
        default_factory=list, description="Issue numbers closed by this PR"
    )
    breaking_changes: str | None = Field(
        default=None, description="Breaking changes description (⚠️ warning)"
    )
