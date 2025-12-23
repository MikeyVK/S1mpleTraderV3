"""MCP Server Entrypoint."""
import asyncio
from io import TextIOWrapper
import sys
from typing import Any, cast, Type

from pydantic import AnyUrl, BaseModel
import anyio

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
    GitRestoreTool,
    GitStashTool,
    GitStatusTool,
)
from mcp_server.tools.git_analysis_tools import GitDiffTool, GitListBranchesTool
from mcp_server.tools.health_tools import HealthCheckTool

# Tools
from mcp_server.tools.issue_tools import (
    CloseIssueTool,
    CreateIssueTool,
    GetIssueTool,
    ListIssuesTool,
    UpdateIssueTool,
)
from mcp_server.tools.label_tools import (
    AddLabelsTool,
    CreateLabelTool,
    DeleteLabelTool,
    ListLabelsTool,
    RemoveLabelsTool,
)
from mcp_server.tools.milestone_tools import (
    CloseMilestoneTool,
    CreateMilestoneTool,
    ListMilestonesTool,
)
from mcp_server.tools.pr_tools import CreatePRTool, ListPRsTool, MergePRTool
from mcp_server.tools.project_tools import InitializeProjectTool, GetProjectPlanTool
from mcp_server.tools.quality_tools import RunQualityGatesTool
from mcp_server.tools.scaffold_tools import ScaffoldComponentTool, ScaffoldDesignDocTool
from mcp_server.tools.test_tools import RunTestsTool
from mcp_server.tools.validation_tools import ValidateDTOTool, ValidationTool
from mcp_server.tools.safe_edit_tool import SafeEditTool
from mcp_server.tools.template_validation_tool import TemplateValidationTool

# Initialize logging
setup_logging()
logger = get_logger("server")


class MCPServer:
    """Main MCP server class that handles resources and tools."""

    def __init__(self) -> None:
        """Initialize the MCP server with resources and tools."""
        server_name = getattr(getattr(settings, "server"), "name")
        self.server = Server(server_name)

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
            GitRestoreTool(),
            GitListBranchesTool(),
            GitDiffTool(),
            # Quality tools
            RunQualityGatesTool(),
            ValidateDocTool(),
            ValidationTool(),
            ValidateDTOTool(),
            SafeEditTool(),
            TemplateValidationTool(),
            # Development tools
            HealthCheckTool(),
            RunTestsTool(),
            CreateFileTool(),
            # Project tools (Phase 0.5)
            InitializeProjectTool(workspace_root=settings.workspace_root),
            GetProjectPlanTool(workspace_root=settings.workspace_root),
            # Scaffold tools
            ScaffoldComponentTool(),
            ScaffoldDesignDocTool(),
            # Discovery tools
            SearchDocumentationTool(),
            GetWorkContextTool(),
        ]

        # GitHub-dependent resources and additional tools (only if token is configured)
        github_token = getattr(getattr(settings, "github"), "token")
        if github_token:
            self.resources.append(GitHubIssuesResource())
            self.tools.extend([
                # GitHub Issue tools
                CreateIssueTool(),
                ListIssuesTool(),
                GetIssueTool(),
                CloseIssueTool(),
                UpdateIssueTool(),
                # PR and Label tools (require token at init time)
                CreatePRTool(),
                ListPRsTool(),
                MergePRTool(),
                AddLabelsTool(),
                ListLabelsTool(),
                CreateLabelTool(),
                DeleteLabelTool(),
                RemoveLabelsTool(),
                ListMilestonesTool(),
                CreateMilestoneTool(),
                CloseMilestoneTool(),
            ])
            logger.info("GitHub integration enabled")
        else:
            # Register issue tools without token so schemas are available; execution will error.
            self.tools.extend([
                CreateIssueTool(),
                ListIssuesTool(),
                GetIssueTool(),
                CloseIssueTool(),
                UpdateIssueTool(),
            ])
            logger.info(
                "GitHub token not configured - GitHub issue tools available but will "
                "return error on use. Set GITHUB_TOKEN to enable full functionality."
            )

        self.setup_handlers()

    def setup_handlers(self) -> None:
        """Set up the MCP protocol handlers."""

        @self.server.list_resources()  # type: ignore[no-untyped-call, misc]
        async def handle_list_resources() -> list[Resource]:
            return [
                Resource(
                    uri=AnyUrl(r.uri_pattern),
                    name=r.uri_pattern.rsplit("/", maxsplit=1)[-1],
                    description=r.description,
                    mimeType=r.mime_type
                )
                for r in self.resources
            ]

        @self.server.read_resource()  # type: ignore[no-untyped-call, misc]
        async def handle_read_resource(uri: str) -> str:
            for resource in self.resources:
                if resource.matches(uri):
                    return await resource.read(uri)
            raise ValueError(f"Resource not found: {uri}")

        @self.server.list_tools()  # type: ignore[no-untyped-call, misc]
        async def handle_list_tools() -> list[Tool]:
            return [
                Tool(
                    name=t.name,
                    description=t.description,
                    inputSchema=t.input_schema
                )
                for t in self.tools
            ]

        @self.server.call_tool()  # type: ignore[misc]
        async def handle_call_tool(
            name: str,
            arguments: dict[str, Any] | None
        ) -> list[TextContent | ImageContent | EmbeddedResource]:
            for tool in self.tools:
                if tool.name == name:
                    try:
                        # ALL tools now enforce args_model via BaseTool inheritance
                        if getattr(tool, "args_model", None):
                            # Validate args against model
                            model_cls = cast(Type[BaseModel], tool.args_model)
                            model_validated = model_cls(**(arguments or {}))
                            result = await tool.execute(model_validated)
                        else:
                            # Fallback if somehow a tool is missed (should not happen)
                            # Passing kwargs as a single dict if BaseTool expects Any
                            # But legacy typically wanted spread kwargs.
                            # We assume full migration.
                            # Raising error here would be strict.
                            # But for safety, we try passing as kwargs, which will fail types
                            # if tool expects params.
                            # Actually, BaseTool.execute(params) means we must pass an object.
                            # If no model, we pass the dict?
                            result = await tool.execute(arguments or {})

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
        server_name = getattr(getattr(settings, "server"), "name")
        logger.info(
            "Starting MCP server: %s",
            server_name
        )
        # Force LF only on Windows to prevent "invalid trailing data"
        # and other CRLF issues in the JSON-RPC stream
        stdout = anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n"))

        async with stdio_server(stdout=stdout) as (read_stream, write_stream):
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
