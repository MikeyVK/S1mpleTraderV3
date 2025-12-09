"""MCP Server Entrypoint."""
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    Resource,
    TextContent,
    Tool,
)

from mcp_server.config.settings import settings
from mcp_server.core.logging import get_logger, setup_logging
from mcp_server.resources.github import GitHubIssuesResource

# Resources
from mcp_server.resources.standards import StandardsResource
from mcp_server.resources.status import StatusResource
from mcp_server.resources.templates import TemplatesResource
from mcp_server.tools.code_tools import CreateFileTool
from mcp_server.tools.discovery_tools import GetWorkContextTool, SearchDocumentationTool
from mcp_server.tools.docs_tools import ValidateDocTool
from mcp_server.tools.git_tools import (
    CreateBranchTool,
    GitCheckoutTool,
    GitCommitTool,
    GitDeleteBranchTool,
    GitMergeTool,
    GitPushTool,
    GitStashTool,
    GitStatusTool,
)
from mcp_server.tools.health_tools import HealthCheckTool

# Tools
from mcp_server.tools.issue_tools import (
    CloseIssueTool,
    CreateIssueTool,
    GetIssueTool,
    ListIssuesTool,
)
from mcp_server.tools.label_tools import AddLabelsTool
from mcp_server.tools.pr_tools import CreatePRTool
from mcp_server.tools.quality_tools import RunQualityGatesTool
from mcp_server.tools.scaffold_tools import ScaffoldComponentTool, ScaffoldDesignDocTool
from mcp_server.tools.test_tools import RunTestsTool
from mcp_server.tools.validation_tools import ValidateDTOTool, ValidationTool

# Initialize logging
setup_logging()
logger = get_logger("server")


class MCPServer:
    """Main MCP server class that handles resources and tools."""

    def __init__(self) -> None:
        """Initialize the MCP server with resources and tools."""
        self.server = Server(settings.server.name)  # pylint: disable=no-member

        # Core resources (always available)
        self.resources = [
            StandardsResource(),
            TemplatesResource(),
            StatusResource(),
        ]

        # Core tools (always available)
        self.tools = [
            # Git tools
            CreateBranchTool(),
            GitStatusTool(),
            GitCommitTool(),
            GitCheckoutTool(),
            GitPushTool(),
            GitMergeTool(),
            GitDeleteBranchTool(),
            GitStashTool(),
            # Quality tools
            RunQualityGatesTool(),
            ValidateDocTool(),
            ValidationTool(),
            ValidateDTOTool(),
            # Development tools
            HealthCheckTool(),
            RunTestsTool(),
            CreateFileTool(),
            # Scaffold tools
            ScaffoldComponentTool(),
            ScaffoldDesignDocTool(),
            # Discovery tools
            SearchDocumentationTool(),
            GetWorkContextTool(),
            # GitHub Issue tools (always registered, lazy-init checks token)
            CreateIssueTool(),
            ListIssuesTool(),
            GetIssueTool(),
            CloseIssueTool(),
        ]

        # GitHub-dependent resources and additional tools (only if token is configured)
        if settings.github.token:  # pylint: disable=no-member
            self.resources.append(GitHubIssuesResource())
            self.tools.extend([
                # PR and Label tools (require token at init time)
                CreatePRTool(),
                AddLabelsTool(),
            ])
            logger.info("GitHub integration enabled")
        else:
            logger.info(
                "GitHub token not configured - GitHub issue tools available but will "
                "return error on use. Set GITHUB_TOKEN to enable full functionality."
            )

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
