"""Tests for configuration settings."""
# pylint: disable=no-member  # Pydantic v2 FieldInfo false positives
from mcp_server.config.settings import Settings


def test_default_settings() -> None:
    """Test that default settings are loaded correctly."""
    settings = Settings()
    assert settings.server.name == "st3-workflow"
    assert settings.logging.level == "INFO"

def test_load_from_env(mock_env_vars) -> None:
    """Test loading settings from environment variables."""
    settings = Settings.load()
    assert settings.logging.level == "DEBUG"
    assert settings.github.token == "test-token"

def test_load_from_yaml(tmp_path) -> None:
    """Test loading settings from a YAML file."""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("""
server:
  name: "yaml-server"
logging:
  level: "WARNING"
""")

    settings = Settings.load(str(config_file))
    assert settings.server.name == "yaml-server"
    assert settings.logging.level == "WARNING"
