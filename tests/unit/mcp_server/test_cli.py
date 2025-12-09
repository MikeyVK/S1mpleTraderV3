"""Tests for CLI."""
from unittest.mock import patch

from mcp_server.cli import main


def test_cli_version(capsys) -> None:
    """Test that --version flag prints version and exits without running server."""
    with patch("sys.exit") as mock_exit:
        # We also need to patch server_main to prevent it from running if args parsing fails
        # or if we want to ensure it's NOT called when version is requested
        with patch("mcp_server.cli.server_main") as mock_server:
            # sys.exit raises SystemExit, so mock_exit will just record the call
            # but execution will continue unless we raise it ourselves in the mock or catch it
            mock_exit.side_effect = SystemExit(0)

            with patch("sys.argv", ["mcp-server", "--version"]):
                try:
                    main()
                except SystemExit:
                    pass

                mock_exit.assert_called_with(0)
                mock_server.assert_not_called()

    captured = capsys.readouterr()
    assert "ST3 Workflow MCP Server v1.0.0" in captured.out

def test_cli_run() -> None:
    """Test that main() calls server_main when no arguments provided."""
    with patch("mcp_server.cli.server_main") as mock_server, patch("sys.argv", ["mcp-server"]):
        main()
        mock_server.assert_called_once()
