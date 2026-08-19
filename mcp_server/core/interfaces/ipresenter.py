# mcp_server/core/interfaces/ipresenter.py
# template=interface version=3fb28c28 created=2026-06-19T22:33Z updated=2026-08-19T19:05Z
"""IPresenter module.

Interfaces for translating execution results, operation notes, and presentation resources.

@layer: Backend (Contracts)
"""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from mcp_server.core.operation_notes import NoteEntry
from mcp_server.schemas.cache_publication import CachePublication
from mcp_server.schemas.presentation_output import PresentationResource, PresentedOutput


@runtime_checkable
class ITextPresenter(Protocol):
    """Interface for rendering DTOs and operation notes into Markdown text."""

    def present_text(
        self,
        tool_name: str,
        data: BaseModel | dict[str, Any],
        notes: list[NoteEntry] | None = None,
        cache_pub: CachePublication | None = None,
        success: bool | None = None,
    ) -> str:
        """Format data and notes into a Markdown text string."""
        ...

    def present_notes(
        self,
        tool_name: str,
        notes: list[NoteEntry],
    ) -> str | None:
        """Format operation notes into Markdown text blocks."""
        ...


@runtime_checkable
class IResourcePresenter(Protocol):
    """Interface for extracting and formatting embedded presentation resources."""

    def present_resources(
        self,
        tool_name: str,
        data: BaseModel | dict[str, Any],
    ) -> list[PresentationResource]:
        """Extract and format presentation resources from the execution data."""
        ...


@runtime_checkable
class IPresenter(Protocol):
    """Unified interface for presenting execution results and resources to clients."""

    def present(
        self,
        tool_name: str,
        data: BaseModel | dict[str, Any],
        notes: list[NoteEntry] | None = None,
        cache_pub: CachePublication | None = None,
        success: bool | None = None,
    ) -> PresentedOutput:
        """Present data, notes, and resources as a complete PresentedOutput."""
        ...
