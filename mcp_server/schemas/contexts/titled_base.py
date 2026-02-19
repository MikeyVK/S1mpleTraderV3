# mcp_server/schemas/contexts/titled_base.py
"""TitledArtifactContext base schema for all titled artifacts.

Common base for any artifact context that carries a required `title` field:
document artifacts (research, planning, design, architecture, reference) and
tracking artifacts (pr, issue). Eliminates title/validator duplication.

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict, Field, field_validator

# Project modules
from mcp_server.schemas.base import BaseContext


class TitledArtifactContext(BaseContext):
    """Base context class for all artifact types that carry a required title.

    Provides the shared `title` field and non-empty validation. Subclasses
    inherit `title` and do NOT redefine it or duplicate `validate_title_not_empty`.

    Used by:
        - DocArtifactContext (doc artifacts: research, planning, design, …)
        - PRContext (tracking artifact)
        - IssueContext (tracking artifact)
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    title: str = Field(description="Artifact title")

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        """Validate title is not empty."""
        if not v or not v.strip():
            raise ValueError("title must not be empty")
        return v
