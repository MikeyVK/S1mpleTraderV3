"""Command line interface for the MCP server."""

import argparse
import sys

from mcp_server.config.settings import Settings
from mcp_server.server import main as server_main


def main(settings: Settings | None = None) -> None:
    """CLI entry point."""
    _settings = settings or Settings.from_env()

    parser = argparse.ArgumentParser(description="ST3 Workflow MCP Server")
    parser.add_argument("--version", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        # pylint: disable=no-member
        print(f"ST3 Workflow MCP Server v{_settings.server.version}")
        sys.exit(0)

    server_main(_settings)


if __name__ == "__main__":
    main()
