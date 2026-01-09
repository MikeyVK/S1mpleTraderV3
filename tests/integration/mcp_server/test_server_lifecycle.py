"""Test server lifecycle audit logging."""
import json
from unittest.mock import patch, MagicMock

import pytest


@pytest.mark.asyncio
async def test_server_startup_logged_to_audit(tmp_path):
    """Test that server startup is logged to audit log."""
    # Set up temporary audit log
    audit_log = tmp_path / "test_audit.log"

    with patch("mcp_server.config.settings.settings.logging.audit_log", str(audit_log)):
        with patch("mcp_server.managers.github_manager.GitHubAdapter") as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.list_issues.return_value = []
            mock_adapter_class.return_value = mock_adapter

            # Import after patching
            # pylint: disable=import-outside-toplevel
            from mcp_server.server import MCPServer
            from mcp_server.core.logging import setup_logging

            # Setup logging with our temp path
            setup_logging()

            # Create server (triggers __init__)
            _server = MCPServer()

            # Check that audit log was created and contains startup entry
            assert audit_log.exists(), "Audit log should be created"

            # Read and parse audit log
            log_lines = audit_log.read_text().strip().split("\n")
            log_entries = [json.loads(line) for line in log_lines if line]

            # Should have at least one startup message
            startup_entries = [
                entry for entry in log_entries
                if "server_lifecycle" in entry.get("logger", "")
                and entry.get("message") == "MCP server starting"
            ]

            assert len(startup_entries) >= 1, "Should log server startup"
            assert startup_entries[0]["level"] == "INFO"


@pytest.mark.asyncio
async def test_server_shutdown_logged_to_audit(tmp_path):
    """Test that server shutdown is logged to audit log."""
    # Set up temporary audit log
    audit_log = tmp_path / "test_audit.log"

    with patch("mcp_server.config.settings.settings.logging.audit_log", str(audit_log)):
        with patch("mcp_server.managers.github_manager.GitHubAdapter") as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.list_issues.return_value = []
            mock_adapter_class.return_value = mock_adapter

            # pylint: disable=import-outside-toplevel
            from mcp_server.server import MCPServer
            from mcp_server.core.logging import setup_logging

            setup_logging()
            server = MCPServer()

            # Simulate shutdown by explicitly calling a cleanup method
            # (we'll implement this in the GREEN phase)
            if hasattr(server, "shutdown"):
                await server.shutdown()

            # Read audit log
            log_lines = audit_log.read_text().strip().split("\n")
            log_entries = [json.loads(line) for line in log_lines if line]

            # Should have shutdown message
            shutdown_entries = [
                entry for entry in log_entries
                if "server_lifecycle" in entry.get("logger", "")
                and entry.get("message") == "MCP server shutting down"
            ]

            assert len(shutdown_entries) >= 1, "Should log server shutdown"
