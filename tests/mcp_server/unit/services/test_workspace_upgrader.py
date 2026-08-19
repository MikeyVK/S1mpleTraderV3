# tests/mcp_server/unit/services/test_workspace_upgrader.py
"""Unit tests for WorkspaceUpgrader service."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.config.settings import Settings
from mcp_server.services.workspace_upgrader import WorkspaceUpgrader


@pytest.fixture
def mock_settings(tmp_path: Path) -> MagicMock:
    """Fixture providing Settings with tmp_path server_root."""
    server_root = tmp_path / ".pgmcp"
    server_root.mkdir(parents=True, exist_ok=True)
    (server_root / ".version").write_text("1.0.0\n", encoding="utf-8")

    mock_server = MagicMock()
    mock_server.workspace_root = tmp_path.as_posix()
    mock_server.resolved_server_root = server_root
    mock_server.version = "2.0.0"
    mock_server.logs_dir = "logs"

    settings = MagicMock(spec=Settings)
    settings.server = mock_server
    return settings


def test_get_current_workspace_version_reads_version(
    mock_settings: Settings,
    tmp_path: Path,
) -> None:
    """Verify get_current_workspace_version queries .version string or returns 0.0.0 fallback."""
    upgrader = WorkspaceUpgrader(settings=mock_settings)
    assert upgrader.get_current_workspace_version() == "1.0.0"

    # Missing file returns 0.0.0 fallback
    (tmp_path / ".pgmcp" / ".version").unlink()
    assert upgrader.get_current_workspace_version() == "0.0.0"


def test_execute_upgrade_creates_timestamped_backup(
    mock_settings: Settings,
    tmp_path: Path,
) -> None:
    """Verify execute_upgrade creates timestamped backup directory before mutation."""
    server_root = tmp_path / ".pgmcp"
    dummy_file = server_root / "dummy.txt"
    dummy_file.write_text("pre-upgrade data", encoding="utf-8")

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "new_asset.txt").write_text("new asset content", encoding="utf-8")

    upgrader = WorkspaceUpgrader(settings=mock_settings, assets_dir=assets_dir)
    result = upgrader.execute_upgrade()

    backup_path = Path(result.backup_path)
    assert backup_path.exists()
    assert (backup_path / "dummy.txt").read_text(encoding="utf-8") == "pre-upgrade data"


def test_execute_upgrade_preserves_dynamic_state(
    mock_settings: Settings,
    tmp_path: Path,
) -> None:
    """Verify execute_upgrade preserves state.json, deliverables.json, registry & logs."""
    server_root = tmp_path / ".pgmcp"
    (server_root / "state.json").write_text('{"phase": "design"}', encoding="utf-8")
    (server_root / "deliverables.json").write_text('{"cycles": []}', encoding="utf-8")
    (server_root / "template_registry.json").write_text(
        '{"templates": {}}',
        encoding="utf-8",
    )
    logs_dir = server_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    (logs_dir / "old.log").write_text("existing log content", encoding="utf-8")

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    upgrader = WorkspaceUpgrader(settings=mock_settings, assets_dir=assets_dir)
    upgrader.execute_upgrade()

    assert (server_root / "state.json").read_text(encoding="utf-8") == '{"phase": "design"}'
    assert (server_root / "deliverables.json").read_text(encoding="utf-8") == '{"cycles": []}'
    assert (server_root / "template_registry.json").read_text(
        encoding="utf-8",
    ) == '{"templates": {}}'
    assert (logs_dir / "old.log").read_text(encoding="utf-8") == "existing log content"


def test_execute_upgrade_preserves_valid_custom_configs(
    mock_settings: Settings,
    tmp_path: Path,
) -> None:
    """Verify valid user custom YAML configs in .pgmcp/config/ are preserved."""
    server_root = tmp_path / ".pgmcp"
    config_dir = server_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    custom_git_yaml = config_dir / "git.yaml"
    custom_git_yaml.write_text("custom: true\n", encoding="utf-8")

    assets_dir = tmp_path / "assets"
    asset_config_dir = assets_dir / "config"
    asset_config_dir.mkdir(parents=True, exist_ok=True)
    (asset_config_dir / "git.yaml").write_text("default: true\n", encoding="utf-8")

    upgrader = WorkspaceUpgrader(settings=mock_settings, assets_dir=assets_dir)
    result = upgrader.execute_upgrade()

    assert "config/git.yaml" in result.preserved_files or "git.yaml" in result.preserved_files


def test_execute_upgrade_writes_upgrade_log(
    mock_settings: Settings,
    tmp_path: Path,
) -> None:
    """Verify execute_upgrade writes structured JSON upgrade log to .pgmcp/logs/."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    upgrader = WorkspaceUpgrader(settings=mock_settings, assets_dir=assets_dir)
    result = upgrader.execute_upgrade()

    assert result.status == "success"
    assert result.from_version == "1.0.0"
    assert result.to_version == "2.0.0"

    server_root = tmp_path / ".pgmcp"
    logs_dir = server_root / "logs"
    log_files = list(logs_dir.glob("upgrade_*.json"))
    assert len(log_files) == 1

    log_data = json.loads(log_files[0].read_text(encoding="utf-8"))
    assert log_data["status"] == "success"
    assert log_data["to_version"] == "2.0.0"
