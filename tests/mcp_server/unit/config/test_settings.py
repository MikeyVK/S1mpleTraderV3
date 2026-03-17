"""Tests for configuration settings."""

# pylint: disable=no-member  # Pydantic v2 FieldInfo false positives
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.config.settings import Settings


def test_default_settings() -> None:
    """Test that default settings are loaded correctly."""
    settings = Settings()
    assert settings.server.name == "st3-workflow"
    assert settings.logging.level == "INFO"


def test_load_from_env(mock_env_vars: MagicMock) -> None:  # noqa: ARG001
    """Test loading settings from environment variables."""
    settings = Settings.from_env()
    assert settings.logging.level == "DEBUG"
    assert settings.github.token == "test-token"


def test_load_from_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading settings from a YAML file via MCP_CONFIG_PATH env var."""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("""
server:
  name: "yaml-server"
logging:
  level: "WARNING"
""")
    monkeypatch.setenv("MCP_CONFIG_PATH", str(config_file))
    monkeypatch.delenv("MCP_SERVER_NAME", raising=False)
    monkeypatch.delenv("MCP_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("MCP_CONFIG_ROOT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    settings = Settings.from_env()
    assert settings.server.name == "yaml-server"
    assert settings.logging.level == "WARNING"
