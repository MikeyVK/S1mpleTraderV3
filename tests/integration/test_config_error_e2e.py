"""
@module: tests.integration.test_config_error_e2e
@layer: Test Infrastructure
@dependencies: pytest, mcp_server.core.exceptions, mcp_server.config
@responsibilities:
  - E2E test for ConfigError scenarios
  - Test loading invalid artifacts.yaml
  - Verify error messages include file path
"""

# Standard library
from pathlib import Path

# Third-party
import pytest

# Project
from mcp_server.core.exceptions import ConfigError
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig


def test_config_error_for_invalid_yaml(tmp_path: Path) -> None:
    """ConfigError raised for invalid YAML syntax."""
    # Create invalid YAML
    bad_yaml = tmp_path / "bad_artifacts.yaml"
    bad_yaml.write_text("version: 1.0\nartifacts: {invalid", encoding="utf-8")

    # Reset singleton
    ArtifactRegistryConfig.reset_instance()

    # Attempt to load should raise ConfigError
    with pytest.raises(ConfigError) as exc_info:
        ArtifactRegistryConfig.from_file(bad_yaml)

    error = exc_info.value
    assert error.code == "ERR_CONFIG"
    assert str(bad_yaml) in error.message or "bad_artifacts.yaml" in error.message
    assert "YAML" in error.message


def test_config_error_for_missing_required_field(tmp_path: Path) -> None:
    """ConfigError raised when artifacts.yaml missing required fields."""
    # Create YAML with missing required field (state_machine)
    incomplete_yaml = tmp_path / "incomplete_artifacts.yaml"
    incomplete_yaml.write_text("""version: "1.0"
artifact_types:
  - type: doc
    type_id: test
    name: Test
    description: Test artifact
    template_path: null
    fallback_template: null
    name_suffix: null
    file_extension: ".md"
    generate_test: false
""", encoding="utf-8")

    ArtifactRegistryConfig.reset_instance()

    with pytest.raises(ConfigError) as exc_info:
        ArtifactRegistryConfig.from_file(incomplete_yaml)

    error = exc_info.value
    assert error.code == "ERR_CONFIG"
    # Pydantic validation error mentions missing field
    assert "state_machine" in error.message.lower() or "required" in error.message.lower()


def test_config_error_includes_file_path(tmp_path: Path) -> None:
    """ConfigError message includes file path for debugging."""
    bad_yaml = tmp_path / "debug_test.yaml"
    bad_yaml.write_text("invalid yaml: [", encoding="utf-8")

    ArtifactRegistryConfig.reset_instance()

    with pytest.raises(ConfigError) as exc_info:
        ArtifactRegistryConfig.from_file(bad_yaml)

    error = exc_info.value
    # File path should be in error.file_path attribute OR in message
    assert error.file_path is not None or "debug_test.yaml" in error.message
