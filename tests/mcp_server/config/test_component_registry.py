"""Unit tests for ComponentRegistryConfig.

Tests config loading, validation, and singleton pattern for components.yaml.
"""

from mcp_server.config.component_registry import ComponentRegistryConfig


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
