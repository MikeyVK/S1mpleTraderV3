"""Tests for base resource classes."""

import pytest

from mcp_server.resources.base import BaseResource


class TestResource(BaseResource):
    """Test implementation of BaseResource for unit testing."""

    uri_pattern = "test://resource"

    async def read(self, uri: str) -> str:  # noqa: ARG002
        return "content"


@pytest.mark.asyncio
async def test_base_resource_matching() -> None:
    """Test that resource correctly matches its URI pattern."""
    resource = TestResource()
    assert resource.matches("test://resource")
    assert not resource.matches("test://other")


@pytest.mark.asyncio
async def test_base_resource_read() -> None:
    """Test that resource read method returns expected content."""
    resource = TestResource()
    content = await resource.read("test://resource")
    assert content == "content"
