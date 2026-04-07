# tests/mcp_server/unit/config/test_settings.py
"""
Tests for configuration settings.

@layer: Tests (Unit)
@dependencies: [pathlib, pytest, unittest.mock, mcp_server.config.settings]
"""

# Standard library
from collections.abc import Iterator
from importlib import metadata
from pathlib import Path
from unittest.mock import MagicMock, patch

# Third-party
import pytest

# Project modules
from mcp_server.config.settings import Settings, _default_server_version


@pytest.fixture(autouse=True)
def mock_server_version() -> Iterator[None]:
    """Make server version resolution deterministic in tests."""
    with patch("mcp_server.config.settings.metadata.version", return_value="3.0.0"):
        yield


def test_default_settings() -> None:
    """Test that default settings are loaded correctly."""
    settings = Settings()
    assert settings.server.name == "st3-workflow"
    assert settings.server.version == "3.0.0"
    assert settings.logging.level == "INFO"


def test_load_from_env(mock_env_vars: MagicMock) -> None:  # noqa: ARG001
    """Test loading settings from environment variables."""
    settings = Settings.from_env()
    assert settings.logging.level == "DEBUG"
    assert settings.github.token == "test-token"
    assert settings.server.version == "3.0.0"


def test_load_from_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading settings from a YAML file via MCP_CONFIG_PATH env var."""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(
        """
server:
  name: "yaml-server"
logging:
  level: "WARNING"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("MCP_CONFIG_PATH", str(config_file))
    monkeypatch.delenv("MCP_SERVER_NAME", raising=False)
    monkeypatch.delenv("MCP_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("MCP_CONFIG_ROOT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings.from_env()

    assert settings.server.name == "yaml-server"
    assert settings.server.version == "3.0.0"
    assert settings.logging.level == "WARNING"


def test_default_server_version_falls_back_to_secondary_package() -> None:
    """Version lookup should fall back from mcp_server to simpletraderv3."""
    with patch(
        "mcp_server.config.settings.metadata.version",
        side_effect=[metadata.PackageNotFoundError, "3.1.0"],
    ):
        assert _default_server_version() == "3.1.0"


def test_default_server_version_raises_when_no_package_metadata_exists() -> None:
    """Missing package metadata should surface a descriptive error."""
    with (
        patch(
            "mcp_server.config.settings.metadata.version",
            side_effect=metadata.PackageNotFoundError,
        ),
        pytest.raises(metadata.PackageNotFoundError, match="Unable to resolve"),
    ):
        _default_server_version()


def test_load_from_env_applies_all_supported_env_overrides_when_yaml_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment variables should still populate settings without a YAML file."""
    missing_config = tmp_path / "missing.yaml"
    monkeypatch.setenv("MCP_CONFIG_PATH", str(missing_config))
    monkeypatch.setenv("MCP_SERVER_NAME", "env-server")
    monkeypatch.setenv("MCP_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    monkeypatch.setenv("MCP_CONFIG_ROOT", str(tmp_path / ".st3" / "config"))
    monkeypatch.setenv("GITHUB_OWNER", "example-owner")
    monkeypatch.setenv("GITHUB_REPO", "example-repo")
    monkeypatch.setenv("GITHUB_PROJECT_NUMBER", "42")
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")

    settings = Settings.from_env()

    assert settings.server.name == "env-server"
    assert settings.server.workspace_root == str(tmp_path / "workspace")
    assert settings.server.config_root == str(tmp_path / ".st3" / "config")
    assert settings.github.owner == "example-owner"
    assert settings.github.repo == "example-repo"
    assert settings.github.project_number == 42
    assert settings.github.token == "secret-token"
    assert settings.logging.level == "ERROR"
