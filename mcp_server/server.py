"""MCP Server Entrypoint."""
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

from mcp_server.config.settings import settings
from mcp_server.core.logging import setup_logging, get_logger

# Resources
from mcp_server.resources.standards import StandardsResource
from mcp_server.resources.github import GitHubIssuesResource
from mcp_server.resources.templates import TemplatesResource

# Tools
from mcp_server.tools.issue_tools import CreateIssueTool
from mcp_server.tools.git_tools import CreateBranchTool, GitStatusTool
from mcp_server.tools.quality_tools import RunQualityGatesTool
from mcp_server.tools.docs_tools import ValidateDocTool
from mcp_server.tools.health_tools import HealthCheckTool

# Initialize logging
setup_logging()
logger = get_logger("server")


class MCPServer:
    """Main MCP server class that handles resources and tools."""

    def __init__(self) -> None:
        """Initialize the MCP server with resources and tools."""
        self.server = Server(settings.server.name)  # pylint: disable=no-member

        self.resources = [
            StandardsResource(),
            GitHubIssuesResource(),
            TemplatesResource(),
        ]

        self.tools = [
            CreateIssueTool(),
            CreateBranchTool(),
            GitStatusTool(),
            RunQualityGatesTool(),
            ValidateDocTool(),
            HealthCheckTool(),
        ]

        self.setup_handlers()

    def setup_handlers(self) -> None:
        """Set up the MCP protocol handlers."""

        @self.server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            return [
                Resource(
                    uri=r.uri_pattern,
                    name=r.uri_pattern.rsplit("/", maxsplit=1)[-1],
                    description=r.description,
                    mimeType=r.mime_type
                )
                for r in self.resources
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            for resource in self.resources:
                if resource.matches(uri):
                    return await resource.read(uri)
            raise ValueError(f"Resource not found: {uri}")

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            return [
                Tool(
                    name=t.name,
                    description=t.description,
                    inputSchema=t.input_schema
                )
                for t in self.tools
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str,
            arguments: dict | None
        ) -> list[TextContent | ImageContent | EmbeddedResource]:
            for tool in self.tools:
                if tool.name == name:
                    try:
                        result = await tool.execute(**(arguments or {}))
                        response_content: list[
                            TextContent | ImageContent | EmbeddedResource
                        ] = []
                        for content in result.content:
                            if content.get("type") == "text":
                                response_content.append(
                                    TextContent(type="text", text=content["text"])
                                )
                            elif content.get("type") == "image":
                                response_content.append(ImageContent(
                                    type="image",
                                    data=content["data"],
                                    mimeType=content["mimeType"]
                                ))
                            elif content.get("type") == "resource":
                                response_content.append(EmbeddedResource(
                                    type="resource",
                                    resource=content["resource"]
                                ))
                        return response_content
                    except (ValueError, TypeError, KeyError) as e:
                        logger.error(
                            "Tool execution failed: %s", e, exc_info=True
                        )
                        return [TextContent(
                            type="text",
                            text=f"Error executing tool {name}: {e!s}"
                        )]

            raise ValueError(f"Tool not found: {name}")

    async def run(self) -> None:
        """Run the MCP server."""
        logger.info(
            "Starting MCP server: %s",
            settings.server.name  # pylint: disable=no-member
        )
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main() -> None:
    """Entry point for the MCP server."""
    server = MCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
