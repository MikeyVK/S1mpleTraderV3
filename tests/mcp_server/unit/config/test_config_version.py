# c:\temp\pgmcp\tests\mcp_server\unit\config\test_config_version.py
# template=unit_test version=3d15d309 created=2026-07-07T20:15s updated=
"""
Unit tests for config version validation.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.config.loader]
"""

from pathlib import Path

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.core.exceptions import ConfigError
from tests.mcp_server.test_support import get_default_server_root


def _write_yaml(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class TestConfigVersionValidation:
    """Test suite for config version validation."""

    def test_load_workflow_config_success(self, tmp_path: Path) -> None:
        """Valid version '1.0.0' loads successfully."""
        config_dir = tmp_path / get_default_server_root() / "config"
        _write_yaml(config_dir / "workflows.yaml", "version: '1.0.0'\nworkflows: {}\n")
        loader = ConfigLoader(config_dir)
        result = loader.load_workflow_config()
        assert result.version == "1.0.0"

    def test_load_workflow_config_missing_version_raises_config_error(self, tmp_path: Path) -> None:
        """Missing version field raises ConfigError."""
        config_dir = tmp_path / get_default_server_root() / "config"
        _write_yaml(config_dir / "workflows.yaml", "workflows: {}\n")
        loader = ConfigLoader(config_dir)
        with pytest.raises(ConfigError, match="version"):
            loader.load_workflow_config()

    def test_load_workflow_config_invalid_version_raises_config_error(self, tmp_path: Path) -> None:
        """Version other than '1.0.0' raises ConfigError."""
        config_dir = tmp_path / get_default_server_root() / "config"
        _write_yaml(config_dir / "workflows.yaml", "version: '2.0.0'\nworkflows: {}\n")
        loader = ConfigLoader(config_dir)
        with pytest.raises(ConfigError, match="version"):
            loader.load_workflow_config()

    def test_load_git_config_missing_version_raises_config_error(self, tmp_path: Path) -> None:
        """GitConfig lacking version raises ConfigError."""
        config_dir = tmp_path / get_default_server_root() / "config"
        _write_yaml(config_dir / "git.yaml", "branch_types: []\n")
        loader = ConfigLoader(config_dir)
        with pytest.raises(ConfigError, match="version"):
            loader.load_git_config()

    def test_load_git_config_invalid_version_raises_config_error(self, tmp_path: Path) -> None:
        """GitConfig with invalid version raises ConfigError."""
        config_dir = tmp_path / get_default_server_root() / "config"
        _write_yaml(config_dir / "git.yaml", "version: '1.1.0'\nbranch_types: []\n")
        loader = ConfigLoader(config_dir)
        with pytest.raises(ConfigError, match="version"):
            loader.load_git_config()
