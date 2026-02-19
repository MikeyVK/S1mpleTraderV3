# mcp_server/schemas/contexts/issue.py
# template=schema version=74378193 created=2026-02-18T00:00Z updated=
"""IssueContext schema.

Context schema for GitHub Issue tracking artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict, Field

# Project modules
from mcp_server.schemas.contexts.titled_base import TitledArtifactContext


class IssueContext(TitledArtifactContext):
    """Context schema for GitHub Issue tracking artifact scaffolding (user-facing).

    Covers required fields per concrete/issue.md.jinja2 TEMPLATE_METADATA.
    Inherits `title` field and `validate_title_not_empty` from TitledArtifactContext.
    Lifecycle fields (output_path, version_hash, etc.) added by IssueRenderContext.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    # Required fields (title inherited from TitledArtifactContext)
    problem: str = Field(description="Problem description — what is wrong or needed")

    # Optional fields
    summary: str | None = Field(default=None, description="Brief summary of the issue")
    expected: str | None = Field(default=None, description="Expected behavior or outcome")
    actual: str | None = Field(default=None, description="Actual behavior observed")
    context: str | None = Field(default=None, description="Additional context and background")
    steps_to_reproduce: str | None = Field(default=None, description="Steps to reproduce the issue")
    related_docs: list[str] = Field(default_factory=list, description="Related documentation links")
    labels: list[str] = Field(
        default_factory=list, description="GitHub labels to apply (e.g. type:bug)"
    )
    milestone: str | None = Field(default=None, description="Target milestone")
    assignees: list[str] = Field(
        default_factory=list, description="GitHub usernames to assign this issue"
    )
