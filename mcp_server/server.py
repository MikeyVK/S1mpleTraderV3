"""MCP Server Entrypoint."""
import asyncio
from io import TextIOWrapper
from pathlib import Path
import sys
import time
from typing import Any, cast, Type
import uuid

from pydantic import AnyUrl, BaseModel, ValidationError
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

from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult

from mcp_server.config.settings import settings
from mcp_server.core.logging import get_logger, setup_logging
from mcp_server.resources.github import GitHubIssuesResource

# Config
from mcp_server.config.label_startup import validate_label_config_on_startup

# Resources
from mcp_server.resources.standards import StandardsResource
from mcp_server.resources.status import StatusResource
from mcp_server.tools.code_tools import CreateFileTool
from mcp_server.tools.discovery_tools import GetWorkContextTool, SearchDocumentationTool
from mcp_server.tools.git_fetch_tool import GitFetchTool
from mcp_server.tools.git_pull_tool import GitPullTool
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
    GetParentBranchTool,
)
from mcp_server.tools.git_analysis_tools import GitDiffTool, GitListBranchesTool
from mcp_server.tools.health_tools import HealthCheckTool
from mcp_server.tools.admin_tools import RestartServerTool

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
from mcp_server.tools.phase_tools import TransitionPhaseTool, ForcePhaseTransitionTool
from mcp_server.tools.quality_tools import RunQualityGatesTool
from mcp_server.tools.scaffold_artifact import ScaffoldArtifactTool
from mcp_server.tools.test_tools import RunTestsTool
from mcp_server.tools.validation_tools import ValidateDTOTool, ValidationTool
from mcp_server.tools.safe_edit_tool import SafeEditTool
from mcp_server.tools.template_validation_tool import TemplateValidationTool

# Scaffolding infrastructure (Issue #72)
from mcp_server.scaffolding.template_registry import TemplateRegistry
from mcp_server.managers.artifact_manager import ArtifactManager

# Initialize logging
setup_logging()
logger = get_logger("server")
lifecycle_logger = get_logger("server_lifecycle")


class MCPServer:
    """Main MCP server class that handles resources and tools."""

    def __init__(self) -> None:
        """Initialize the MCP server with resources and tools."""
        server_name = getattr(getattr(settings, "server"), "name")

        # Log server startup
        lifecycle_logger.info("MCP server starting")

        # Validate label configuration at startup
        validate_label_config_on_startup()

        # Initialize template registry (Issue #72 Task 1.6)
        workspace_root = Path(settings.server.workspace_root)
        registry_path = workspace_root / ".st3" / "template_registry.yaml"

        # Bootstrap registry file if missing
        if not registry_path.exists():
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            lifecycle_logger.info("Bootstrapping template registry: %s", registry_path)

        self.template_registry = TemplateRegistry(registry_path=registry_path)
        lifecycle_logger.info("Template registry initialized")

        self.server = Server(server_name)

        # Core resources (always available)
        self.resources = [
            StandardsResource(),
            StatusResource(),
        ]

        # Core tools (always available)
        self.tools = [
            # Git tools
            CreateBranchTool(),
            GitStatusTool(),
            GitCommitTool(),
            GitCheckoutTool(),
            GitFetchTool(),
            GitPullTool(),
            GitPushTool(),
            GitMergeTool(),
            GitDeleteBranchTool(),
            GitStashTool(),
            GitRestoreTool(),
            GitListBranchesTool(),
            GitDiffTool(),
            GetParentBranchTool(),
            # Quality tools
            RunQualityGatesTool(),
            ValidationTool(),
            ValidateDTOTool(),
            SafeEditTool(),
            TemplateValidationTool(),
            # Development tools
            HealthCheckTool(),
            RestartServerTool(),
            RunTestsTool(),
            CreateFileTool(),
            # Project tools (Phase 0.5)
            InitializeProjectTool(workspace_root=Path(settings.server.workspace_root)),
            GetProjectPlanTool(workspace_root=Path(settings.server.workspace_root)),
            # Phase tools (Phase B)
            TransitionPhaseTool(workspace_root=Path(settings.server.workspace_root)),
            ForcePhaseTransitionTool(workspace_root=Path(settings.server.workspace_root)),
            # Scaffold tools (unified artifact scaffolding)
            ScaffoldArtifactTool(
                manager=ArtifactManager(
                    workspace_root=workspace_root,
                    template_registry=self.template_registry
                )
            ),
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

    def _validate_tool_arguments(
        self,
        tool: BaseTool,
        arguments: dict[str, Any] | None,
        call_id: str,
        name: str
    ) -> BaseModel | dict[str, Any] | list[TextContent | ImageContent | EmbeddedResource]:
        """Validate tool arguments against args_model.

        Returns:
            - Validated BaseModel instance if validation succeeds
            - Raw arguments dict if no args_model
            - List of content with error if validation fails
        """
        if not getattr(tool, "args_model", None):
            return arguments or {}

        model_cls = cast(Type[BaseModel], tool.args_model)
        logger.debug(
            "Validating tool arguments",
            extra={"props": {
                "call_id": call_id,
                "tool_name": name,
                "model": model_cls.__name__,
            }}
        )
        try:
            model_validated = model_cls(**(arguments or {}))
            logger.debug(
                "Arguments validated successfully",
                extra={"props": {
                    "call_id": call_id,
                    "tool_name": name,
                }}
            )
            return model_validated
        except ValidationError as validation_error:
            logger.warning(
                "Argument validation failed: %s",
                validation_error,
                extra={"props": {
                    "call_id": call_id,
                    "tool_name": name,
                    "model": model_cls.__name__,
                    "arguments": arguments,
                }}
            )
            error_details = str(validation_error)
            return [TextContent(
                type="text",
                text=f"Invalid input for {name}: {error_details}"
            )]

    @staticmethod
    def _augment_text_with_error_metadata(text: str, result: ToolResult) -> str:
        """Add error_code and hints to text when result is error."""
        if not result.is_error or not hasattr(result, "error_code"):
            return text

        if result.error_code:
            text += f"\n\nError code: {result.error_code}"
        if hasattr(result, "hints") and result.hints:
            text += "\nHints:"
            for hint in result.hints:
                text += f"\n  - {hint}"
        return text

    def _convert_tool_result_to_content(
        self,
        result: ToolResult
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Convert ToolResult to MCP content list."""
        response_content: list[TextContent | ImageContent | EmbeddedResource] = []

        for content in result.content:
            if content.get("type") == "text":
                text = content["text"]
                text = self._augment_text_with_error_metadata(text, result)
                response_content.append(TextContent(type="text", text=text))
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

    def setup_handlers(self) -> None:
        """Set up the MCP protocol handlers."""

        @self.server.list_resources()  # type: ignore[no-untyped-call, untyped-decorator]
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

        @self.server.read_resource()  # type: ignore[no-untyped-call, untyped-decorator]
        async def handle_read_resource(uri: str) -> str:
            for resource in self.resources:
                if resource.matches(uri):
                    return await resource.read(uri)
            raise ValueError(f"Resource not found: {uri}")

        @self.server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
        async def handle_list_tools() -> list[Tool]:
            return [
                Tool(
                    name=t.name,
                    description=t.description,
                    inputSchema=t.input_schema
                )
                for t in self.tools
            ]

        @self.server.call_tool()  # type: ignore[untyped-decorator]
        async def handle_call_tool(
            name: str,
            arguments: dict[str, Any] | None
        ) -> list[TextContent | ImageContent | EmbeddedResource]:
            call_id = uuid.uuid4().hex
            start_time = time.perf_counter()
            argument_keys = sorted((arguments or {}).keys())

            logger.debug(
                "Tool call received",
                extra={"props": {
                    "call_id": call_id,
                    "tool_name": name,
                    "argument_keys": argument_keys,
                }}
            )

            for tool in self.tools:
                if tool.name == name:
                    try:
                        # Validate arguments
                        validated = self._validate_tool_arguments(
                            tool, arguments, call_id, name
                        )
                        # Early return if validation failed
                        if isinstance(validated, list):
                            return validated

                        # Execute tool
                        result = await tool.execute(validated)

                        # Convert result to MCP content
                        response_content = self._convert_tool_result_to_content(result)

                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        logger.debug(
                            "Tool call completed",
                            extra={"props": {
                                "call_id": call_id,
                                "tool_name": name,
                                "duration_ms": duration_ms,
                            }}
                        )
                        return response_content
                    except asyncio.CancelledError:
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        logger.info(
                            "Tool call cancelled",
                            extra={"props": {
                                "call_id": call_id,
                                "tool_name": name,
                                "duration_ms": duration_ms,
                            }}
                        )
                        raise
                    except (KeyError, AttributeError, TypeError) as e:
                        # Response processing error (dict access, attribute access, type issues)
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        logger.error(
                            "Response processing failed: %s",
                            e,
                            exc_info=True,
                            extra={"props": {
                                "call_id": call_id,
                                "tool_name": name,
                                "duration_ms": duration_ms,
                                "error_type": type(e).__name__,
                            }}
                        )
                        return [TextContent(
                            type="text",
                            text=f"Error processing tool response: {e!s}"
                        )]
            raise ValueError(f"Tool not found: {name}")

    async def run(self) -> None:
        """Run the MCP server."""
        server_name = getattr(getattr(settings, "server"), "name")

        # Validate label configuration at startup
        validate_label_config_on_startup()

        logger.info(
            "Starting MCP server: %s",
            server_name
        )
        lifecycle_logger.info("MCP server running")

        # Force LF only on Windows to prevent "invalid trailing data"
        # and other CRLF issues in the JSON-RPC stream
        stdout = anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n"))

        try:
            async with stdio_server(stdout=stdout) as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        except KeyboardInterrupt:
            lifecycle_logger.info("MCP server interrupted by user")
        except Exception as e:
            lifecycle_logger.error(
                "MCP server crashed: %s",
                e,
                exc_info=True,
                extra={"props": {
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }}
            )
            # Re-raise to ensure proper exit code
            raise
        finally:
            lifecycle_logger.info("MCP server shutting down")

    async def shutdown(self) -> None:
        """Shutdown the MCP server gracefully."""
        lifecycle_logger.info("MCP server shutting down")


def main() -> None:
    """Entry point for the MCP server."""
    server = MCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
