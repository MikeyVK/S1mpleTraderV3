# artifact: type=unit_test, version=1.0, created=2026-01-21T22:04:10Z
"""
Unit tests for ValidationError to_resource_dict() enhancement.

Tests ValidationError.to_resource_dict() for structured JSON responses
Following TDD: These tests are written BEFORE implementation (RED phase).
@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.core.exceptions,
                mcp_server.scaffolding.template_introspector]
@responsibilities:
    - Test to_resource_dict() returns proper structure
    - Test schema serialization in resource dict
    - Test validation info (missing/provided) included
    - Test resource dict format matches ToolResult contract
"""
# Standard library
# (no standard library imports needed)

# Third-party
import pytest

# Project modules
from mcp_server.core.exceptions import ValidationError
from mcp_server.scaffolding.template_introspector import TemplateSchema


@pytest.fixture(name="sample_schema")
def fixture_sample_schema() -> TemplateSchema:
    """Provides sample TemplateSchema for testing"""
    return TemplateSchema(
        required=["name", "description"],
        optional=["frozen"]
    )


class TestValidationErrorEnhancement:
    """Tests for ValidationError to_resource_dict() enhancement."""

    def test_to_resource_dict_includes_schema(
        self,
        sample_schema: TemplateSchema
    ) -> None:
        """RED: to_resource_dict() returns dict with artifact_type and schema"""
        # Arrange
        error = ValidationError(
            message="Missing required fields",
            schema=sample_schema
        )

        # Act
        result = error.to_resource_dict("dto")

        # Assert
        assert result["artifact_type"] == "dto"
        assert "schema" in result
        assert result["schema"]["required"] == ["name", "description"]
        assert result["schema"]["optional"] == ["frozen"]

    def test_to_resource_dict_includes_validation(
        self,
        sample_schema: TemplateSchema
    ) -> None:
        """RED: to_resource_dict() includes validation details (missing/provided)"""
        # Arrange - create error with missing/provided tracking
        error = ValidationError(
            message="Missing required fields",
            schema=sample_schema
        )
        # Simulate scaffolder setting these attributes
        error.missing = ["description"]
        error.provided = ["name"]

        # Act
        result = error.to_resource_dict("dto")

        # Assert
        assert "validation" in result
        assert result["validation"]["missing"] == ["description"]
        assert result["validation"]["provided"] == ["name"]

    def test_to_resource_dict_handles_none_schema(
        self
    ) -> None:
        """RED: to_resource_dict() handles None schema gracefully"""
        # Arrange
        error = ValidationError(
            message="Validation failed",
            schema=None
        )

        # Act
        result = error.to_resource_dict("dto")

        # Assert
        assert result["artifact_type"] == "dto"
        assert "schema" not in result  # Schema omitted when None
