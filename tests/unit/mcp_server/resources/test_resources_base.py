"""Tests for base resource classes."""
import pytest

from mcp_server.resources.base import BaseResource


class TestResource(BaseResource):
    uri_pattern = "test://resource"
    async def read(self, uri: str) -> str:
        return "content"

@pytest.mark.asyncio
async def test_base_resource_matching():
    resource = TestResource()
    assert resource.matches("test://resource")
    assert not resource.matches("test://other")

@pytest.mark.asyncio
async def test_base_resource_read():
    resource = TestResource()
    content = await resource.read("test://resource")
    assert content == "content"
