# tests\mcp_server\unit\core\interfaces\test_presenter_interfaces.py
# template=unit_test version=8825c0bb created=2026-08-19T19:00Z updated=2026-08-19T19:05Z
"""
Unit tests for mcp_server.core.interfaces.ipresenter.

Unit tests for ITextPresenter, IResourcePresenter, and IPresenter protocols.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.core.interfaces.ipresenter]
@responsibilities:
    - Test ITextPresenter runtime_checkable protocol compliance
    - Test IResourcePresenter runtime_checkable protocol compliance
    - Test IPresenter runtime_checkable protocol compliance
"""

from typing import Any

from pydantic import BaseModel

from mcp_server.core.interfaces.ipresenter import IPresenter, IResourcePresenter, ITextPresenter
from mcp_server.core.operation_notes import NoteEntry
from mcp_server.schemas.cache_publication import CachePublication
from mcp_server.schemas.presentation_output import PresentationResource, PresentedOutput


class MockTextPresenter:
    """Valid implementation of ITextPresenter."""

    def present_text(
        self,
        tool_name: str,
        data: BaseModel | dict[str, Any],
        notes: list[NoteEntry] | None = None,
        cache_pub: CachePublication | None = None,
        success: bool | None = None,
    ) -> str:
        return "text"

    def present_notes(
        self,
        tool_name: str,
        notes: list[NoteEntry],
    ) -> str | None:
        return "notes"


class MockResourcePresenter:
    """Valid implementation of IResourcePresenter."""

    def present_resources(
        self,
        tool_name: str,
        data: BaseModel | dict[str, Any],
    ) -> list[PresentationResource]:
        return [PresentationResource(uri="schema://validation", content="{}")]


class MockPresenter:
    """Valid implementation of IPresenter."""

    def present(
        self,
        tool_name: str,
        data: BaseModel | dict[str, Any],
        notes: list[NoteEntry] | None = None,
        cache_pub: CachePublication | None = None,
        success: bool | None = None,
    ) -> PresentedOutput:
        return PresentedOutput(text="ok", resources=[])


class IncompletePresenter:
    """Invalid presenter missing required methods."""

    pass


class TestPresenterInterfaces:
    """Test suite for presenter interface protocols."""

    def test_text_presenter_protocol(self) -> None:
        """Verify isinstance check on ITextPresenter."""
        mock = MockTextPresenter()
        assert isinstance(mock, ITextPresenter)
        assert not isinstance(IncompletePresenter(), ITextPresenter)

    def test_resource_presenter_protocol(self) -> None:
        """Verify isinstance check on IResourcePresenter."""
        mock = MockResourcePresenter()
        assert isinstance(mock, IResourcePresenter)
        assert not isinstance(IncompletePresenter(), IResourcePresenter)

    def test_presenter_protocol(self) -> None:
        """Verify isinstance check on IPresenter."""
        mock = MockPresenter()
        assert isinstance(mock, IPresenter)
        assert not isinstance(IncompletePresenter(), IPresenter)
