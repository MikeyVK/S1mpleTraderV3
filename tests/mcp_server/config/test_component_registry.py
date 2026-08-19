"""Unit tests for ArtifactRegistryConfig.

Tests config loading and validation for artifacts.yaml.

@layer: Tests (Unit)
@dependencies: pytest, pathlib, mcp_server.config.loader, mcp_server.config.schemas
"""

from pathlib import Path

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import ArtifactRegistryConfig
from mcp_server.core.exceptions import ConfigError
from tests.mcp_server.test_support import get_default_server_root


def _load_artifact_registry(config_path: Path | None = None) -> ArtifactRegistryConfig:
    loader = ConfigLoader(
        Path(f"{get_default_server_root()}/config") if config_path is None else config_path.parent
    )
    return loader.load_artifact_registry_config(config_path=config_path)


class TestArtifactRegistryConfig:
    """Test suite for ArtifactRegistryConfig."""

    def test_load_valid_config(self) -> None:
        """Test loading valid artifacts.yaml file."""
        config = _load_artifact_registry()

        type_ids = config.list_type_ids()
        assert len(type_ids) > 0
        assert "dto" in type_ids
        assert "worker" in type_ids
        assert "tool" in type_ids
        assert "design" in type_ids

        dto = config.get_artifact("dto")
        assert dto.type_id == "dto"
        assert dto.description is not None
        assert dto.type == "code"

    def test_repeated_loads_are_equivalent(self) -> None:
        """Repeated loads of the same file should be value-equivalent."""
        config1 = _load_artifact_registry()
        config2 = _load_artifact_registry()
        assert config1 == config2

    def test_missing_file(self) -> None:
        """Test ConfigError when file not found."""
        with pytest.raises(ConfigError, match="Artifact registry not found"):
            _load_artifact_registry(Path(f"{get_default_server_root()}/config/nonexistent.yaml"))

    def test_get_artifact_valid(self) -> None:
        """Test get_artifact with valid type."""
        config = _load_artifact_registry()
        dto = config.get_artifact("dto")

        assert dto.type_id == "dto"
        assert dto.type == "code"

    def test_get_artifact_invalid(self) -> None:
        """Test get_artifact with unknown type."""
        config = _load_artifact_registry()

        with pytest.raises(ConfigError, match="Artifact type 'invalid_type' not found"):
            config.get_artifact("invalid_type")

    def test_has_artifact_type(self) -> None:
        """Test has_artifact_type checker method."""
        config = _load_artifact_registry()

        assert config.has_artifact_type("dto") is True
        assert config.has_artifact_type("worker") is True
        assert config.has_artifact_type("design") is True
        assert config.has_artifact_type("invalid") is False

    def test_list_type_ids(self) -> None:
        """Test list_type_ids returns sorted list."""
        config = _load_artifact_registry()
        type_ids = config.list_type_ids()

        assert len(type_ids) > 0
        assert type_ids == sorted(type_ids)
        assert "dto" in type_ids
        assert "worker" in type_ids
        assert "design" in type_ids

    def test_validate_artifact_fields_complete(self) -> None:
        """Test field validation with all required fields."""
        config = _load_artifact_registry()
        dto = config.get_artifact("dto")

        dto.validate_artifact_fields({"name": "User", "description": "User DTO"})

    def test_context_schema_loading(self, tmp_path: Path) -> None:
        """Test that SchemaFieldDef and context_schema are loaded correctly."""
        import yaml  # noqa: PLC0415

        data = {
            "version": "1.0.0",
            "artifact_types": [
                {
                    "type": "code",
                    "type_id": "test_artifact",
                    "name": "Test",
                    "description": "Test description",
                    "file_extension": ".py",
                    "state_machine": {
                        "states": ["CREATED"],
                        "initial_state": "CREATED",
                    },
                    "context_schema": {
                        "field_a": {
                            "type": "string",
                            "title": "Field A",
                            "description": "Description A",
                            "required": True,
                            "min_length": 5,
                        }
                    },
                }
            ],
        }
        yaml_file = tmp_path / "artifacts.yaml"
        yaml_file.write_text(yaml.safe_dump(data), encoding="utf-8")

        config = _load_artifact_registry(config_path=yaml_file)
        artifact = config.get_artifact("test_artifact")

        assert artifact.context_schema is not None
        assert "field_a" in artifact.context_schema
        field = artifact.context_schema["field_a"]
        assert field.type == "string"
        assert field.title == "Field A"
        assert field.min_length == 5
