# mcp_server\schemas\presentation_output.py
# template=dto version=c3132e49 created=2026-08-19T19:00Z updated=2026-08-19T19:05Z
"""
Data Transfer Object for presentation_output.

Presentation output and embedded resource DTOs.

@layer: Presentation
@dependencies: [pydantic]
@responsibilities:
    - Define immutable PresentationResource model for embedded client resources
    - Define immutable PresentedOutput model for combined presentation results
"""

from pydantic import BaseModel, ConfigDict, Field


class PresentationResource(BaseModel):
    """Immutable representation of an embedded presentation resource."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    uri: str
    mime_type: str = "application/json"
    content: str


class PresentedOutput(BaseModel):
    """Unified immutable presentation result produced by the presentation layer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    resources: list[PresentationResource] = Field(default_factory=list)
