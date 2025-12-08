"""Integration tests for the MCP server."""
import pytest
import asyncio
from mcp_server.server import MCPServer

@pytest.fixture
def server():
    return MCPServer()

@pytest.mark.asyncio
async def test_server_initialization(server):
    assert server.server.name == "st3-workflow"
    assert len(server.resources) > 0

@pytest.mark.asyncio
async def test_list_resources(server):
    # Depending on how we can test the internal server handlers without running the full stdio server
    # We might need to access the handlers directly if they were exposed or use an MCP client for testing
    # But for now, we can check the internal state

    resource_uris = [r.uri_pattern for r in server.resources]
    assert "st3://rules/coding_standards" in resource_uris

@pytest.mark.asyncio
async def test_read_resource(server):
    # Testing the handler logic directly if possible or simulating it
    # Since handlers are decorated, we can try to find them in the server object, but it's internal

    # We can test the resource object directly which we already did in unit tests
    # Or we can verify that the server has the correct resource loaded

    resource = next(r for r in server.resources if r.uri_pattern == "st3://rules/coding_standards")
    content = await resource.read("st3://rules/coding_standards")
    assert "python" in content
