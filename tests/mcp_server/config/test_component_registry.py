"""Unit tests for ComponentRegistryConfig.

Tests config loading, validation, and singleton pattern for components.yaml.
"""

import pytest

from mcp_server.config.component_registry import ComponentRegistryConfig
from mcp_server.core.exceptions import ConfigError


class TestComponentRegistryConfig:
    """Test suite for ComponentRegistryConfig."""

    def setup_method(self):
        """Reset singleton before each test."""
        ComponentRegistryConfig.reset_instance()

    def test_load_valid_config(self):
        """Test loading valid components.yaml file.

        Tests that config loads all 9 component types correctly.
        """
        config = ComponentRegistryConfig.from_file(".st3/components.yaml")

        # Should load all 9 component types
        assert len(config.components) == 9

        # Should contain expected types
        assert "dto" in config.components
        assert "worker" in config.components
        assert "adapter" in config.components

        # Should parse component definition correctly
        dto = config.components["dto"]
        assert dto.type_id == "dto"
        assert dto.description is not None
        assert dto.scaffolder_class == "DTOScaffolder"

    def test_singleton_pattern(self):
        """Test singleton returns same instance.

        Tests that from_file() caches and returns the same instance.
        """
        config1 = ComponentRegistryConfig.from_file(".st3/components.yaml")
        config2 = ComponentRegistryConfig.from_file(".st3/components.yaml")

        # Should return exact same object (not just equal)
        assert config1 is config2

    def test_missing_file(self):
        """Test ConfigError when file not found.

        Should raise ConfigError with clear message about missing file.
        """
        with pytest.raises(ConfigError, match="Config file not found"):
            ComponentRegistryConfig.from_file(".st3/nonexistent.yaml")

    def test_get_component_valid(self):
        """Test get_component with valid type.

        Should return ComponentDefinition for known type.
        """
        config = ComponentRegistryConfig.from_file()
        dto = config.get_component("dto")

        assert dto.type_id == "dto"
        assert dto.scaffolder_class == "DTOScaffolder"

    def test_get_component_invalid(self):
        """Test get_component with unknown type.

        Should raise ValueError with list of available types.
        """
        config = ComponentRegistryConfig.from_file()

        with pytest.raises(ValueError, match="Unknown component type"):
            config.get_component("invalid_type")

    def test_has_component_type(self):
        """Test has_component_type checker method."""
        config = ComponentRegistryConfig.from_file()

        assert config.has_component_type("dto") is True
        assert config.has_component_type("worker") is True
        assert config.has_component_type("invalid") is False

    def test_get_available_types(self):
        """Test get_available_types returns sorted list."""
        config = ComponentRegistryConfig.from_file()
        types = config.get_available_types()

        # Should return all 9 types
        assert len(types) == 9

        # Should be sorted
        assert types == sorted(types)

        # Should contain expected types
        assert "dto" in types
        assert "worker" in types

    def test_validate_scaffold_fields_complete(self):
        """Test field validation with all required fields.

        Should not raise when all required fields provided.
        """
        config = ComponentRegistryConfig.from_file()
        dto = config.get_component("dto")

        # Should not raise
        dto.validate_scaffold_fields({"name": "User", "description": "User DTO"})

    def test_validate_scaffold_fields_missing(self):
        """Test field validation with missing required fields.

        Should raise ValueError listing missing fields.
        """
        config = ComponentRegistryConfig.from_file()
        dto = config.get_component("dto")

        with pytest.raises(ValueError, match="Missing required fields"):
            dto.validate_scaffold_fields({"name": "User"})  # Missing description
