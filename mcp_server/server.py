"""MCP Server Entrypoint."""
import asyncio
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent,
    EmbeddedResource,
    GetPromptRequest, ListPromptsRequest,
    ReadResourceRequest, ListResourcesRequest,
    CallToolRequest, ListToolsRequest
)
from mcp_server.config.settings import settings
from mcp_server.core.logging import setup_logging, get_logger
from mcp_server.resources.standards import StandardsResource

# Initialize logging
setup_logging()
logger = get_logger("server")

class MCPServer:
    def __init__(self):
        self.server = Server(settings.server.name)
        self.resources = [
            StandardsResource(),
        ]
        self.tools = []

        self.setup_handlers()

    def setup_handlers(self):
        @self.server.list_resources()
        async def handle_list_resources() -> list[Resource]:
            return [
                Resource(
                    uri=r.uri_pattern,
                    name=r.uri_pattern.split("/")[-1],
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
        async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent | ImageContent | EmbeddedResource]:
            for tool in self.tools:
                if tool.name == name:
                    try:
                        result = await tool.execute(**(arguments or {}))
                        response_content = []
                        for content in result.content:
                            if content.get("type") == "text":
                                response_content.append(TextContent(type="text", text=content["text"]))
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

                        # If the tool result indicates an error, we should probably communicate that.
                        # However, call_tool return signature expects a list of content.
                        # The MCP protocol handles errors via JSON-RPC error responses if an exception is raised,
                        # or we can return content that describes the error.
                        # For now, we return the content as is.
                        # If we want to signal tool failure at the protocol level, we could raise an exception.

                        return response_content
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}", exc_info=True)
                        # Return exception message as text content so the model sees it
                        return [TextContent(type="text", text=f"Error executing tool {name}: {str(e)}")]

            raise ValueError(f"Tool not found: {name}")

    async def run(self):
        logger.info(f"Starting MCP server: {settings.server.name}")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

def main():
    server = MCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
