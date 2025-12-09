"""Tests for standards resource."""
import json

import pytest

from mcp_server.resources.standards import StandardsResource


@pytest.mark.asyncio
async def test_standards_resource_read():
    resource = StandardsResource()
    content = await resource.read("st3://rules/coding_standards")

    data = json.loads(content)
    assert data["python"]["version"] == ">=3.11"
    assert data["testing"]["coverage_min"] == 80

def test_standards_resource_metadata():
    resource = StandardsResource()
    assert resource.uri_pattern == "st3://rules/coding_standards"
    assert "coding standards" in resource.description
