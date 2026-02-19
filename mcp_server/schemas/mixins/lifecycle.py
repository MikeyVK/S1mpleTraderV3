# mcp_server/schemas/mixins/lifecycle.py
# template=schema version=74378193 created=2026-02-17T09:37Z updated=
"""LifecycleMixin schema.

System-managed lifecycle fields for scaffolded artifacts (4 required fields, NEVER user-provided)

@layer: Schema Infrastructure
"""

# Standard library
from datetime import datetime
from pathlib import Path

# Third-party
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Project modules


class LifecycleMixin(BaseModel):
    """System-managed lifecycle fields for scaffolded artifacts.

    This mixin provides 4 required fields that are NEVER user-provided:
    - output_path: Where the artifact was written
    - scaffold_created: When the artifact was scaffolded
    - template_id: Which template was used
    - version_hash: Template version for provenance tracking

    Usage:
        class WorkerRenderContext(LifecycleMixin, WorkerContext):
            pass  # Inherits all lifecycle fields + artifact-specific fields
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        validate_default=True,
    )

    output_path: Path = Field(
        description="Absolute path where artifact was written",
    )
    scaffold_created: datetime = Field(
        description="Timestamp of artifact creation",
    )
    template_id: str = Field(
        description="Template identifier (e.g., 'dto', 'worker')",
    )
    version_hash: str = Field(
        description="Template version hash (8-char lowercase hex [0-9a-f])",
    )

    @field_validator("version_hash")
    @classmethod
    def validate_version_hash(cls, v: str) -> str:
        """Validate version_hash is 8-char lowercase hex string."""
        if not isinstance(v, str):
            raise ValueError(f"version_hash must be str, got {type(v).__name__}")
        if len(v) != 8:
            raise ValueError(f"version_hash must be 8 chars, got {len(v)}")
        if not all(c in "0123456789abcdef" for c in v):
            raise ValueError(f"version_hash must be lowercase hex [0-9a-f], got: {v}")
        return v
