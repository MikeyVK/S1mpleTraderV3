# tests/unit/mcp_server/resources/test_standards.py
"""Tests for standards resource."""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false

# Standard library
import json

# Third-party
import pytest

# Module under test
from mcp_server.resources.standards import StandardsResource


@pytest.mark.asyncio
async def test_standards_resource_read() -> None:
    """Test that standards resource returns valid JSON with required fields."""
    resource = StandardsResource()
    content = await resource.read("st3://rules/coding_standards")

    data = json.loads(content)
    assert data["python"]["version"] == ">=3.11"
    assert data["testing"]["coverage_min"] == 80


def test_standards_resource_metadata() -> None:
    """Test that standards resource has correct URI pattern and description."""
    resource = StandardsResource()
    assert resource.uri_pattern == "st3://rules/coding_standards"
    assert "coding standards" in resource.description
