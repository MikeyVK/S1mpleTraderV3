# tests/unit/mcp_server/resources/test_base.py
"""Tests for base resource."""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false

# Third-party
import pytest

# Module under test
from mcp_server.resources.base import BaseResource


class ConcreteResource(BaseResource):
    """Concrete implementation for testing."""

    uri_pattern = "test://resource"

    async def read(self, uri: str) -> str:  # noqa: ARG002
        return "content"


class TestBaseResource:
    """Tests for BaseResource."""

    @pytest.mark.asyncio
    async def test_matches_exact(self) -> None:
        """Test exact URI matching."""
        resource = ConcreteResource()
        assert resource.matches("test://resource") is True
        assert resource.matches("test://other") is False

    @pytest.mark.asyncio
    async def test_attributes(self) -> None:
        """Test default attributes."""
        resource = ConcreteResource()
        assert resource.mime_type == "application/json"
        assert not resource.description

    @pytest.mark.asyncio
    async def test_abstract_class_instantiation(self) -> None:
        """Test BaseResource cannot be instantiated."""
        with pytest.raises(TypeError):
            # pylint: disable=abstract-class-instantiated
            BaseResource()  # type: ignore
