"""Command line interface for the MCP server."""
import argparse
import sys
from mcp_server.server import main as server_main
from mcp_server.config.settings import settings

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="ST3 Workflow MCP Server")
    parser.add_argument("--version", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        print(f"ST3 Workflow MCP Server v{settings.server.version}")
        sys.exit(0)

    server_main()

if __name__ == "__main__":
    main()
