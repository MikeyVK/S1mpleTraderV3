# tests\mcp_server\unit\config\test_modular_loader.py
# template=unit_test version=3d15d309 created=2026-07-15T21:32Z updated=
"""
Unit tests for mcp_server.config.loader.

Verify loading and merging of modular artifact config files from the artifacts/ subdirectory.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.config.loader]
@responsibilities:
    - Test TestModularLoader functionality
    - Verify None
    - None
"""

# Third-party
from pathlib import Path

import pytest

# Project modules
from mcp_server.config.loader import ArtifactRegistryConfig, ConfigLoader
from mcp_server.core.exceptions import ConfigError


class TestModularLoader:
    """Test suite for loader."""

    def test_loader_scans_artifacts_dir_and_merges(self, tmp_path: Path) -> None:
        """Test that loader scans template_root/config/ dir and merges definitions."""
        # Arrange
        config_root = tmp_path / "config"
        template_root = tmp_path / "templates"
        index_file = config_root / "artifacts.yaml"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text("version: '1.0.0'\nartifact_types: []\n", encoding="utf-8")
        (template_root / "config").mkdir(parents=True, exist_ok=True)
        # Create modular YAML files
        dto_yaml = (
            "type: code\n"
            "type_id: dto\n"
            "template_version: '1.0.0'\n"
            "name: DTO\n"
            "description: DTO desc\n"
            "file_extension: .py\n"
            "state_machine:\n"
            "  states: [CREATED]\n"
            "  initial_state: CREATED\n"
            "  valid_transitions: []\n"
        )
        worker_yaml = (
            "type: code\n"
            "type_id: worker\n"
            "template_version: '1.0.0'\n"
            "name: Worker\n"
            "description: Worker desc\n"
            "file_extension: .py\n"
            "state_machine:\n"
            "  states: [CREATED]\n"
            "  initial_state: CREATED\n"
            "  valid_transitions: []\n"
        )
        (template_root / "config" / "dto.yaml").write_text(dto_yaml, encoding="utf-8")
        (template_root / "config" / "worker.yaml").write_text(worker_yaml, encoding="utf-8")

        loader = ConfigLoader(config_root=config_root, template_root=template_root)

        # Act
        config = loader.load_artifact_registry_config()

        # Assert
        assert isinstance(config, ArtifactRegistryConfig)
        assert config.version == "1.0.0"
        assert len(config.artifact_types) == 2
        type_ids = [a.type_id for a in config.artifact_types]
        assert "dto" in type_ids
        assert "worker" in type_ids

    def test_loader_fails_fast_on_invalid_yaml_in_modular_file(self, tmp_path: Path) -> None:
        """Test that loader fails fast when a modular file has invalid YAML syntax."""
        # Arrange
        config_root = tmp_path / "config"
        template_root = tmp_path / "templates"
        index_file = config_root / "artifacts.yaml"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text("version: '1.0.0'\nartifact_types: []\n", encoding="utf-8")
        (template_root / "config").mkdir(parents=True, exist_ok=True)

        # Create templates/config/ directory with bad YAML
        (template_root / "config" / "bad.yaml").write_text(
            "invalid: yaml: syntax: [}", encoding="utf-8"
        )

        loader = ConfigLoader(config_root=config_root, template_root=template_root)

        # Act & Assert
        with pytest.raises(ConfigError) as exc_info:
            loader.load_artifact_registry_config()
        assert "Invalid YAML syntax" in str(exc_info.value)

    def test_loader_clean_break_fails_without_modular_artifacts(self, tmp_path: Path) -> None:
        """Test that under Clean Break, loading fails if registry is empty."""
        # Arrange
        config_root = tmp_path / "config"
        template_root = tmp_path / "templates"
        index_file = config_root / "artifacts.yaml"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text("version: '1.0.0'\nartifact_types: []\n", encoding="utf-8")
        (template_root / "config").mkdir(parents=True, exist_ok=True)

        loader = ConfigLoader(config_root=config_root, template_root=template_root)

        # Act & Assert
        with pytest.raises(ConfigError) as exc_info:
            loader.load_artifact_registry_config()
        assert "Empty" in str(exc_info.value) or "no artifact types defined" in str(exc_info.value)

    def test_loader_fails_if_legacy_artifacts_directory_exists(self, tmp_path: Path) -> None:
        """Test that under Clean Break, loading fails if legacy config/artifacts exists."""
        # Arrange
        config_root = tmp_path / "config"
        template_root = tmp_path / "templates"
        index_file = config_root / "artifacts.yaml"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text("version: '1.0.0'\nartifact_types: []\n", encoding="utf-8")
        (template_root / "config").mkdir(parents=True, exist_ok=True)

        # Create legacy artifacts dir
        legacy_dir = config_root / "artifacts"
        legacy_dir.mkdir(parents=True)

        loader = ConfigLoader(config_root=config_root, template_root=template_root)

        # Act & Assert
        with pytest.raises(ConfigError) as exc_info:
            loader.load_artifact_registry_config()
        assert (
            "legacy" in str(exc_info.value).lower()
            or "no longer supported" in str(exc_info.value).lower()
        )
