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


@pytest.mark.asyncio
async def test_standards_resource_reads_active_gates_from_quality_yaml() -> None:
    """Test that standards resource dynamically reads active_gates from quality.yaml.

    This verifies WP8 requirement: standards.py should read from quality.yaml
    instead of returning hardcoded JSON.
    """
    resource = StandardsResource()
    content = await resource.read("st3://rules/coding_standards")

    data = json.loads(content)

    # Should include active_gates field from quality.yaml
    assert "quality_gates" in data, "Missing quality_gates section"
    assert "active_gates" in data["quality_gates"], "Missing active_gates field"

    # Should have the 6 configured gates from quality.yaml
    # (gate5_tests and gate6_coverage removed in C0 per F1: Remove pytest/coverage)
    active_gates = data["quality_gates"]["active_gates"]
    assert isinstance(active_gates, list), "active_gates should be a list"
    assert len(active_gates) == 6, f"Expected 6 active gates, got {len(active_gates)}"

    # Verify expected gate names from quality.yaml
    expected_gates = [
        "gate0_ruff_format",
        "gate1_formatting",
        "gate2_imports",
        "gate3_line_length",
        "gate4_types",
        "gate4_pyright",
    ]
    assert active_gates == expected_gates, f"Expected {expected_gates}, got {active_gates}"
