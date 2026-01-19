"""Unit tests for ArtifactRegistryConfig.

Tests config loading, validation, and singleton pattern for artifacts.yaml.
"""

from pathlib import Path

import pytest

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.exceptions import ConfigError


class TestArtifactRegistryConfig:
    """Test suite for ArtifactRegistryConfig."""

    def setup_method(self):
        """Reset singleton before each test."""
        ArtifactRegistryConfig.reset_instance()

    def test_load_valid_config(self):
        """Test loading valid artifacts.yaml file.

        Tests that config loads all artifact types correctly.
        """
        config = ArtifactRegistryConfig.from_file(Path(".st3/artifacts.yaml"))

        # Should load artifact types (code + doc)
        type_ids = config.list_type_ids()
        assert len(type_ids) > 0

        # Should contain expected core types
        assert "dto" in type_ids
        assert "worker" in type_ids
        assert "tool" in type_ids
        assert "design" in type_ids

        # Should parse artifact definition correctly
        dto = config.get_artifact("dto")
        assert dto.type_id == "dto"
        assert dto.description is not None
        assert dto.type.value == "code"

    def test_singleton_pattern(self):
        """Test singleton returns same instance.

        Tests that from_file() caches and returns the same instance.
        """
        config1 = ArtifactRegistryConfig.from_file(Path(".st3/artifacts.yaml"))
        config2 = ArtifactRegistryConfig.from_file(Path(".st3/artifacts.yaml"))

        # Should return exact same object (not just equal)
        assert config1 is config2

    def test_missing_file(self):
        """Test ConfigError when file not found.

        Should raise ConfigError with clear message about missing file.
        """
        with pytest.raises(ConfigError, match="Artifact registry not found"):
            ArtifactRegistryConfig.from_file(Path(".st3/nonexistent.yaml"))

    def test_get_artifact_valid(self):
        """Test get_artifact with valid type.

        Should return ArtifactDefinition for known type.
        """
        config = ArtifactRegistryConfig.from_file()
        dto = config.get_artifact("dto")

        assert dto.type_id == "dto"
        assert dto.type.value == "code"

    def test_get_artifact_invalid(self):
        """Test get_artifact with unknown type.

        Should raise ConfigError with list of available types.
        """
        config = ArtifactRegistryConfig.from_file()

        with pytest.raises(ConfigError, match="Artifact type 'invalid_type' not found"):
            config.get_artifact("invalid_type")

    def test_has_artifact_type(self):
        """Test has_artifact_type checker method."""
        config = ArtifactRegistryConfig.from_file()

        assert config.has_artifact_type("dto") is True
        assert config.has_artifact_type("worker") is True
        assert config.has_artifact_type("design") is True
        assert config.has_artifact_type("invalid") is False

    def test_list_type_ids(self):
        """Test list_type_ids returns sorted list."""
        config = ArtifactRegistryConfig.from_file()
        type_ids = config.list_type_ids()

        # Should have multiple types
        assert len(type_ids) > 0

        # Should be sorted
        assert type_ids == sorted(type_ids)

        # Should contain core types
        assert "dto" in type_ids
        assert "worker" in type_ids
        assert "design" in type_ids

    def test_validate_artifact_fields_complete(self):
        """Test field validation with all required fields.

        Should not raise when all required fields provided.
        """
        config = ArtifactRegistryConfig.from_file()
        dto = config.get_artifact("dto")

        # Should not raise
        dto.validate_artifact_fields({"name": "User", "description": "User DTO"})

    def test_validate_artifact_fields_missing(self):
        """Test field validation with missing required fields.

        Should raise ValueError listing missing fields.
        """
        config = ArtifactRegistryConfig.from_file()
        dto = config.get_artifact("dto")

        with pytest.raises(ValueError, match="Missing required fields"):
            dto.validate_artifact_fields({"name": "User"})  # Missing description
