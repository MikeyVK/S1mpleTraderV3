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
from pydantic import ValidationError

# Project modules
from mcp_server.config.settings import (
    ServerSettings,
    Settings,
    _default_server_version,  # pyright: ignore[reportPrivateUsage]
)
from tests.mcp_server.test_support import get_default_server_root


@pytest.fixture(autouse=True)
def mock_server_version() -> Iterator[None]:
    """Make server version resolution deterministic in tests."""
    with patch("mcp_server.config.settings.metadata.version", return_value="3.0.0"):
        yield


def test_default_settings() -> None:
    """Test that default settings are loaded correctly."""
    settings = Settings()
    assert settings.server.name == "phase-gate-mcp"
    assert settings.server.version == "3.0.0"
    assert settings.logging.level == "INFO"


def test_load_from_env(mock_env_vars: MagicMock) -> None:  # noqa: ARG001
    """Test loading settings from environment variables."""
    settings = Settings.from_env()
    assert settings.logging.level == "DEBUG"
    assert settings.github.token == "test-token"
    assert settings.server.version == "3.0.0"


def test_load_from_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading settings from a YAML file via PGMCP_CONFIG_PATH env var."""
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
    monkeypatch.setenv("PGMCP_CONFIG_PATH", str(config_file))
    monkeypatch.delenv("PGMCP_SERVER_NAME", raising=False)
    monkeypatch.delenv("PGMCP_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("PGMCP_CONFIG_ROOT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings.from_env()

    assert settings.server.name == "yaml-server"
    assert settings.server.version == "3.0.0"
    assert settings.logging.level == "WARNING"


def test_default_server_version_resolves_via_distribution_map() -> None:
    """Version lookup uses packages_distributions() to find the owning distribution."""
    with (
        patch(
            "mcp_server.config.settings.metadata.packages_distributions",
            return_value={"mcp_server": ["some-dist"]},
        ),
        patch(
            "mcp_server.config.settings.metadata.version",
            return_value="3.1.0",
        ),
    ):
        assert _default_server_version() == "3.1.0"


def test_default_server_version_raises_when_no_package_metadata_exists() -> None:
    """Missing package metadata should fall back to release manifest or default version."""
    with patch(
        "mcp_server.config.settings.metadata.version",
        side_effect=metadata.PackageNotFoundError,
    ):
        assert _default_server_version() == "2.0.0"


# ---------------------------------------------------------------------------
# C3 — server_root_dir field in ServerSettings (renamed from state_dir in C6)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# C1 #359 — version must be read-only (computed_field + extra='forbid')
# ---------------------------------------------------------------------------


def test_server_settings_rejects_version_kwarg() -> None:
    """#359 RED: ServerSettings must reject version= as a constructor kwarg."""
    with pytest.raises(ValidationError):
        ServerSettings(version="injected")


def test_state_dir_default_is_pgmcp() -> None:
    """C5 RED: ServerSettings server_root_dir default must be '.pgmcp'."""
    s = ServerSettings()
    assert s.server_root_dir == ".pgmcp"


def test_state_dir_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """C3 RED: PGMCP_SERVER_PROJECT_DIR env var must override server_root_dir."""
    monkeypatch.setenv("PGMCP_SERVER_PROJECT_DIR", ".custom-gate")
    monkeypatch.delenv("PGMCP_SERVER_NAME", raising=False)
    monkeypatch.delenv("PGMCP_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("PGMCP_CONFIG_ROOT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    s = Settings.from_env()
    assert s.server.server_root_dir == ".custom-gate"


# ---------------------------------------------------------------------------
# C6 — server_root_dir field rename (F13)
# ---------------------------------------------------------------------------


def test_server_root_dir_default_is_pgmcp() -> None:
    """C6 RED: ServerSettings must expose server_root_dir (not state_dir)."""
    s = ServerSettings()
    assert s.server_root_dir == ".pgmcp"


def test_server_root_dir_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """C6 RED: PGMCP_SERVER_PROJECT_DIR env var must populate server_root_dir field."""
    monkeypatch.setenv("PGMCP_SERVER_PROJECT_DIR", ".custom-root")
    monkeypatch.delenv("PGMCP_SERVER_NAME", raising=False)
    monkeypatch.delenv("PGMCP_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("PGMCP_CONFIG_ROOT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    s = Settings.from_env()
    assert s.server.server_root_dir == ".custom-root"


# ---------------------------------------------------------------------------
# logs_dir field in ServerSettings
# ---------------------------------------------------------------------------


def test_logs_dir_default_is_logs() -> None:
    """ServerSettings logs_dir default must be 'logs'."""
    s = ServerSettings()
    assert s.logs_dir == "logs"


def test_logs_dir_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """PGMCP_LOGS_DIR env var must override logs_dir field."""
    monkeypatch.setenv("PGMCP_LOGS_DIR", "custom-logs")
    monkeypatch.delenv("PGMCP_SERVER_NAME", raising=False)
    monkeypatch.delenv("PGMCP_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("PGMCP_CONFIG_ROOT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    s = Settings.from_env()
    assert s.server.logs_dir == "custom-logs"


def test_load_from_env_applies_all_supported_env_overrides_when_yaml_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment variables should still populate settings without a YAML file."""
    missing_config = tmp_path / "missing.yaml"
    monkeypatch.setenv("PGMCP_CONFIG_PATH", str(missing_config))
    monkeypatch.setenv("PGMCP_SERVER_NAME", "env-server")
    monkeypatch.setenv("PGMCP_WORKSPACE_ROOT", str(tmp_path / "workspace"))
    monkeypatch.setenv("PGMCP_CONFIG_ROOT", str(tmp_path / ".phase-gate" / "config"))
    monkeypatch.setenv("GITHUB_OWNER", "example-owner")
    monkeypatch.setenv("GITHUB_REPO", "example-repo")
    monkeypatch.setenv("GITHUB_PROJECT_NUMBER", "42")
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")

    settings = Settings.from_env()

    assert settings.server.name == "env-server"
    assert settings.server.workspace_root == str(tmp_path / "workspace")
    assert settings.server.config_root == str(tmp_path / ".phase-gate" / "config")
    assert settings.github.owner == "example-owner"
    assert settings.github.repo == "example-repo"
    assert settings.github.project_number == 42
    assert settings.logging.level == "ERROR"


def test_get_default_server_root_resolves_dynamically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that get_default_server_root resolves dynamically."""
    monkeypatch.delenv("PGMCP_SERVER_PROJECT_DIR", raising=False)

    real_exists = Path.exists

    def mock_exists(self: Path) -> bool:
        if self.name == ".phase-gate":
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", mock_exists)

    # By default, it should be ".pgmcp"
    assert get_default_server_root() == ".pgmcp"

    # If overridden in the environment, it should dynamically change
    monkeypatch.setenv("PGMCP_SERVER_PROJECT_DIR", ".custom-test-root")


def test_resolved_paths_properties(tmp_path: Path) -> None:
    # 1. When folders DO exist under workspace_root
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    server_root = workspace / ".pgmcp"
    config_dir = server_root / "config"
    templates_dir = server_root / "templates"

    config_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    s = ServerSettings(workspace_root=str(workspace), server_root_dir=".pgmcp", config_root="")
    assert s.resolved_server_root == server_root.resolve()
    assert s.resolved_config_root == config_dir.resolve()
    assert s.resolved_template_root == templates_dir.resolve()

    # 2. When folders DO NOT exist under workspace_root (should resolve strictly without fallback)
    non_existent_workspace = tmp_path / "non_existent"
    s_fallback = ServerSettings(
        workspace_root=str(non_existent_workspace), server_root_dir=".pgmcp", config_root=""
    )

    assert s_fallback.resolved_server_root == (non_existent_workspace / ".pgmcp").resolve()
    assert (
        s_fallback.resolved_config_root == (non_existent_workspace / ".pgmcp" / "config").resolve()
    )
    assert (
        s_fallback.resolved_template_root
        == (non_existent_workspace / ".pgmcp" / "templates").resolve()
    )
    # 3. With explicit config_root
    s_explicit = ServerSettings(
        workspace_root=str(workspace),
        server_root_dir=".pgmcp",
        config_root=str(tmp_path / "custom"),
    )
    assert s_explicit.resolved_config_root == (tmp_path / "custom").resolve()


def test_bypass_version_check_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # Under pytest, it should default to True
    assert Settings().server.bypass_version_check is True

    # If we clear PYTEST_CURRENT_TEST, it should default to False
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert Settings().server.bypass_version_check is False


def test_bypass_version_check_from_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    # Explicit PGMCP_BYPASS_VERSION_CHECK="false" overrides pytest Default
    monkeypatch.setenv("PGMCP_BYPASS_VERSION_CHECK", "false")
    assert Settings.from_env().server.bypass_version_check is False

    # Explicit PGMCP_BYPASS_VERSION_CHECK="true" overrides default False
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("PGMCP_BYPASS_VERSION_CHECK", "true")
    assert Settings.from_env().server.bypass_version_check is True
