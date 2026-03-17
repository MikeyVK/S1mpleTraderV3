"""Test server lifecycle audit logging."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.config.settings import GitHubSettings, LogSettings, ServerSettings, Settings
from mcp_server.server import MCPServer


def _make_test_settings(audit_log: Path) -> Settings:
    """Build real settings with repo config and test-local audit log."""
    workspace_root = Path(__file__).resolve().parents[4]
    return Settings(
        server=ServerSettings(
            name="test-server",
            workspace_root=str(workspace_root),
            config_root=str(workspace_root / ".st3" / "config"),
        ),
        logging=LogSettings(level="INFO", audit_log=str(audit_log)),
        github=GitHubSettings(owner="test", repo="repo", token=None),
    )


@pytest.mark.asyncio
async def test_server_startup_logged_to_audit(tmp_path: Path) -> None:
    """Test that server startup is logged to audit log."""
    audit_log = tmp_path / "test_audit.log"

    with patch("mcp_server.managers.github_manager.GitHubAdapter") as mock_adapter_class:
        mock_adapter = MagicMock()
        mock_adapter.list_issues.return_value = []
        mock_adapter_class.return_value = mock_adapter

        _server = MCPServer(settings=_make_test_settings(audit_log))

    assert audit_log.exists(), "Audit log should be created"

    log_lines = audit_log.read_text().strip().split("\n")
    log_entries = [json.loads(line) for line in log_lines if line]

    startup_entries = [
        entry
        for entry in log_entries
        if "server_lifecycle" in entry.get("logger", "")
        and entry.get("message") == "MCP server starting"
    ]

    assert len(startup_entries) >= 1, "Should log server startup"
    assert startup_entries[0]["level"] == "INFO"


@pytest.mark.asyncio
async def test_server_shutdown_logged_to_audit(tmp_path: Path) -> None:
    """Test that server shutdown is logged to audit log."""
    audit_log = tmp_path / "test_audit.log"

    with patch("mcp_server.managers.github_manager.GitHubAdapter") as mock_adapter_class:
        mock_adapter = MagicMock()
        mock_adapter.list_issues.return_value = []
        mock_adapter_class.return_value = mock_adapter

        server = MCPServer(settings=_make_test_settings(audit_log))
        await server.shutdown()

    log_lines = audit_log.read_text().strip().split("\n")
    log_entries = [json.loads(line) for line in log_lines if line]

    shutdown_entries = [
        entry
        for entry in log_entries
        if "server_lifecycle" in entry.get("logger", "")
        and entry.get("message") == "MCP server shutting down"
    ]

    assert len(shutdown_entries) >= 1, "Should log server shutdown"
