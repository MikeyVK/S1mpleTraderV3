# mcp_server/schemas/contexts/commit.py
# template=schema version=74378193 created=2026-02-18T00:00Z updated=
"""CommitContext schema.

Context schema for Commit tracking artifact scaffolding (user-facing, no lifecycle fields)

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict, Field, field_validator

# Project modules
from mcp_server.schemas.base import BaseContext


class CommitContext(BaseContext):
    """Context schema for Commit tracking artifact scaffolding (user-facing).

    Covers required fields per concrete/commit.txt.jinja2 TEMPLATE_METADATA.
    Lifecycle fields (output_path, version_hash, etc.) added by CommitRenderContext.

    Note: breaking_description is listed as optional (per TEMPLATE_METADATA) even though
    V1 introspector incorrectly marks it required. The V2 schema is the authoritative source.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    # Required fields
    # Note: `type` is a Python builtin but valid as a Pydantic field name
    type: str = Field(description="Commit type (feat, fix, docs, refactor, etc.)")  # noqa: A003
    message: str = Field(description="Commit subject line (imperative mood, ≤50 chars)")

    # Optional fields
    scope: str | None = Field(default=None, description="Component scope (e.g. schemas, workers)")
    body: str | None = Field(default=None, description="Multi-line body (72-char wrap)")
    breaking_change: bool = Field(default=False, description="Whether this is a breaking change")
    breaking_description: str | None = Field(
        default=None, description="BREAKING CHANGE footer description"
    )
    footer: str | None = Field(default=None, description="Additional footer information")
    refs: list[str] = Field(default_factory=list, description="Issue references (e.g., #123)")

    @field_validator("type")
    @classmethod
    def validate_type_not_empty(cls, v: str) -> str:
        """Validate commit type is not empty."""
        if not v or not v.strip():
            raise ValueError("commit type must not be empty")
        return v

    @field_validator("message")
    @classmethod
    def validate_message_not_empty(cls, v: str) -> str:
        """Validate commit message is not empty."""
        if not v or not v.strip():
            raise ValueError("message must not be empty")
        return v
