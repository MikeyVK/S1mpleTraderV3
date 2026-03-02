"""Tests for CLI."""

import contextlib
from unittest.mock import patch

import pytest

from mcp_server.cli import main


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that --version flag prints version and exits without running server."""
    with (
        patch("sys.exit") as mock_exit,
        patch("mcp_server.cli.server_main") as mock_server,
        patch("sys.argv", ["mcp-server", "--version"]),
    ):
        mock_exit.side_effect = SystemExit(0)
        with contextlib.suppress(SystemExit):
            main()

        mock_exit.assert_called_with(0)
        mock_server.assert_not_called()

    captured = capsys.readouterr()
    assert "ST3 Workflow MCP Server v1.0.0" in captured.out


def test_cli_run() -> None:
    """Test that main() calls server_main when no arguments provided."""
    with patch("mcp_server.cli.server_main") as mock_server, patch("sys.argv", ["mcp-server"]):
        main()
        mock_server.assert_called_once()
