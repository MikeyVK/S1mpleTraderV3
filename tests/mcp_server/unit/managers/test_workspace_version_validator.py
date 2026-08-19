# tests/mcp_server/unit/managers/test_workspace_version_validator.py
"""Unit tests for WorkspaceVersionValidator."""

from pathlib import Path

import pytest

from mcp_server.core.exceptions import ConfigError
from mcp_server.managers.workspace_version_validator import WorkspaceVersionValidator


def test_validate_missing_version_file_raises_config_error(tmp_path: Path) -> None:
    """Verify missing .version file raises ConfigError with --init advice."""
    validator = WorkspaceVersionValidator()
    with pytest.raises(ConfigError) as exc_info:
        validator.validate(server_root=tmp_path, expected_version="1.0.0")
    assert "--init" in str(exc_info.value)
    assert exc_info.value.file_path == (tmp_path / ".version").as_posix()


def test_validate_version_mismatch_raises_config_error(tmp_path: Path) -> None:
    """Verify version mismatch raises ConfigError with --upgrade advice."""
    version_file = tmp_path / ".version"
    version_file.write_text("0.9.0\n", encoding="utf-8")

    validator = WorkspaceVersionValidator()
    with pytest.raises(ConfigError) as exc_info:
        validator.validate(server_root=tmp_path, expected_version="1.0.0")
    assert "--upgrade" in str(exc_info.value)
    assert "Workspace version mismatch" in str(exc_info.value)


def test_validate_matching_version_succeeds(tmp_path: Path) -> None:
    """Verify matching version string passes without exception."""
    version_file = tmp_path / ".version"
    version_file.write_text("1.0.0\n", encoding="utf-8")

    validator = WorkspaceVersionValidator()
    validator.validate(server_root=tmp_path, expected_version="1.0.0")


def test_validate_bypass_version_check_skips_validation(tmp_path: Path) -> None:
    """Verify bypass_version_check flag skips version validation."""
    validator = WorkspaceVersionValidator()
    validator.validate(server_root=tmp_path, expected_version="1.0.0", bypass_version_check=True)


def test_read_version_returns_string_or_none(tmp_path: Path) -> None:
    """Verify read_version queries .version string or returns None."""
    validator = WorkspaceVersionValidator()
    assert validator.read_version(tmp_path) is None

    (tmp_path / ".version").write_text("2.0.0", encoding="utf-8")
    assert validator.read_version(tmp_path) == "2.0.0"
