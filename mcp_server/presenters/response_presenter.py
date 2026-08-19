# mcp_server\presenters\response_presenter.py
# template=generic version=e866e4ff created=2026-08-19T19:00Z updated=2026-08-19T19:05Z
"""Composite presenter coordinating text rendering and resource formatting.

@layer: Presentation
@dependencies: [pydantic, mcp_server.core.interfaces.ipresenter]
@responsibilities:
    - Implement IPresenter protocol via composition
    - Delegate text rendering to ITextPresenter and resource extraction to IResourcePresenter
    - Bundle results into an immutable PresentedOutput DTO
"""

from typing import Any

from pydantic import BaseModel

from mcp_server.core.interfaces.ipresenter import IPresenter, IResourcePresenter, ITextPresenter
from mcp_server.core.operation_notes import NoteEntry
from mcp_server.schemas.cache_publication import CachePublication
from mcp_server.schemas.presentation_output import PresentedOutput


class ResponsePresenter(IPresenter):
    """Composite presenter that coordinates text and resource generation."""

    def __init__(
        self,
        text_presenter: ITextPresenter,
        resource_presenter: IResourcePresenter,
    ) -> None:
        self._text_presenter = text_presenter
        self._resource_presenter = resource_presenter

    def present(
        self,
        tool_name: str,
        data: BaseModel | dict[str, Any],
        notes: list[NoteEntry] | None = None,
        cache_pub: CachePublication | None = None,
        success: bool | None = None,
    ) -> PresentedOutput:
        """Coordinate delegates to produce a unified PresentedOutput."""
        text = self._text_presenter.present_text(
            tool_name=tool_name,
            data=data,
            notes=notes,
            cache_pub=cache_pub,
            success=success,
        )
        resources = self._resource_presenter.present_resources(
            tool_name=tool_name,
            data=data,
        )
        return PresentedOutput(text=text, resources=resources)
