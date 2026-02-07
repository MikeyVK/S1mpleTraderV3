# artifact: type=unit_test, version=1.0, created=2026-01-21T21:59:47Z
"""
Unit tests for TemplateScaffolder introspection integration.

Tests template introspection integration in TemplateScaffolder validation
Following TDD: These tests are written BEFORE implementation (RED phase).
@layer: Tests (Unit)
@dependencies: [pytest, jinja2, mcp_server.scaffolders.template_scaffolder,
                mcp_server.scaffolding.template_introspector]
@responsibilities:
    - Test validate() uses introspection instead of artifacts.yaml
    - Test ValidationError includes schema from template
    - Test missing required fields detected via introspection
    - Test optional fields not required
    - Test system fields filtered from validation
"""
# Standard library
# (no standard library imports needed)

# Third-party
import pytest

# Project modules
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.exceptions import ValidationError
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder


@pytest.fixture(name="registry")
def fixture_registry() -> ArtifactRegistryConfig:
    """Provides artifact registry configuration"""
    return ArtifactRegistryConfig.from_file()

@pytest.fixture(name="scaffolder")
def fixture_scaffolder(registry: ArtifactRegistryConfig) -> TemplateScaffolder:
    """Provides TemplateScaffolder instance with introspection"""
    return TemplateScaffolder(registry=registry)


class TestTemplateScaffolderIntrospection:
    """Tests for TemplateScaffolder introspection integration."""

    def test_validate_uses_introspection_not_yaml(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """RED: validate() should use template introspection for schema extraction"""
        # Arrange - DTO template has {{ name }}, {{ description }}, {% if frozen %}
        # System fields should be filtered

        # Act - provide all required fields (from template introspection)
        result = scaffolder.validate(
            "dto",
            name="TestDTO",
            description="Test description",
            frozen=True,
            examples=[{"test": "data"}],
            fields=[{"name": "test", "type": "str", "description": "Test"}],
            dependencies=["pydantic"],
            responsibilities=["Validation"]
        )

        # Assert - validation passes (frozen is optional, system fields not required)
        assert result is True

    def test_validate_error_includes_template_schema(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """RED: validate() raises ValidationError with schema when fields missing"""
        # Arrange - Concrete DTO template requires only 'name' (fields is optional)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            scaffolder.validate("dto")  # Missing name (required)

        # Assert - error should have schema attribute with template-derived fields
        error = exc_info.value
        assert hasattr(error, "schema"), "ValidationError should have schema attribute"
        # Concrete DTO template: name=required, fields/description/validators=optional
        assert "name" in error.schema.required
        assert "fields" in error.schema.optional
        assert "description" in error.schema.optional

    def test_validate_allows_optional_fields_omitted(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """RED: validate() allows optional fields to be omitted"""
        # Arrange - DTO has optional 'frozen' field ({% if frozen %})

        # Act - omit optional field
        result = scaffolder.validate(
            "dto",
            name="TestDTO",
            description="Test",
            frozen=True,
            examples=[{"test": "data"}],
            fields=[{"name": "test", "type": "str", "description": "Test"}],
            dependencies=["pydantic"],
            responsibilities=["Validation"]
            # validators omitted - should be OK (optional)
        )

        # Assert
        assert result is True

    def test_validate_skips_system_fields(
        self,
        scaffolder: TemplateScaffolder
    ) -> None:
        """RED: validate() does NOT require system-injected fields"""
        # Arrange - template uses {{ template_id }}, {{ template_version }}, etc.
        # These are injected by ArtifactManager, NOT provided by agent

        # Act - don't provide system fields
        result = scaffolder.validate(
            "dto",
            name="TestDTO",
            description="Test",
            frozen=True,
            examples=[{"test": "data"}],
            fields=[{"name": "test", "type": "str", "description": "Test"}],
            dependencies=["pydantic"],
            responsibilities=["Validation"]
            # NO template_id, template_version, scaffold_created, output_path
        )

        # Assert - should pass (system fields filtered from validation)
        assert result is True
