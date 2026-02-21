"""Integration tests for the MCP server."""

import pytest


@pytest.mark.asyncio
async def test_server_initialization(server):
    """Test that the MCP server initializes correctly."""
    assert server.server.name == "st3-workflow"
    assert len(server.resources) > 0


@pytest.mark.asyncio
async def test_list_resources(server):
    """Test that resources are correctly registered."""
    resource_uris = [r.uri_pattern for r in server.resources]
    assert "st3://rules/coding_standards" in resource_uris


@pytest.mark.asyncio
async def test_read_resource(server):
    """Test that resources can be read."""
    resource = next(r for r in server.resources if r.uri_pattern == "st3://rules/coding_standards")
    content = await resource.read("st3://rules/coding_standards")
    assert "python" in content
