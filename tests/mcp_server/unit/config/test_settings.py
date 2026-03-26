# tests/mcp_server/unit/config/test_settings.py
"""
Tests for configuration settings.

@layer: Tests (Unit)
@dependencies: [pathlib, pytest, unittest.mock, mcp_server.config.settings]
"""

# Standard library
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

# Third-party
import pytest

# Project modules
from mcp_server.config.settings import Settings


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
