# pyright: reportMissingImports=false
"""MCP Server Entrypoint."""

import asyncio
import json
import sys
import time
import uuid
from io import TextIOWrapper
from typing import Any

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    EmbeddedResource,
    ImageContent,
    Resource,
    TextContent,
    Tool,
)
from pydantic import AnyUrl

# Config
from mcp_server.config.settings import Settings

# Resources
# Resources
# Scaffolding infrastructure (Issue #72)
from mcp_server.core.interfaces.ipresenter import IPresenter
from mcp_server.core.interfaces.itool import ITool
from mcp_server.core.interfaces.itool_response_cache import IToolResponsePublisher
from mcp_server.core.logging import get_logger
from mcp_server.core.operation_notes import NoteContext
from mcp_server.resources.base import BaseResource
from mcp_server.schemas.presentation_output import PresentedOutput

# Tools
from mcp_server.tools.tool_result import ToolResult
from mcp_server.utils.mcp_converters import (
    convert_tool_result_to_mcp_result,
)

logger = get_logger("server")
lifecycle_logger = get_logger("server_lifecycle")


class MCPServer:
    """Main MCP server class that handles resources and tools."""

    def __init__(
        self,
        settings: Settings,
        tools: list[ITool],
        resources: list[BaseResource],
        presenter: IPresenter | None = None,
        publisher: IToolResponsePublisher | None = None,
    ) -> None:
        """Initialize the MCP server with resources and tools."""
        self._settings = settings
        self.presenter = presenter
        self.response_cache_manager = publisher
        server_name = settings.server.name

        self.server = Server(server_name)
        self.resources = resources
        self.tools = tools

        self.setup_handlers()

    def _convert_tool_result_to_mcp_result(self, result: ToolResult) -> CallToolResult:
        """Convert ToolResult to CallToolResult while preserving error semantics."""
        return convert_tool_result_to_mcp_result(result)

    def setup_handlers(self) -> None:
        """Set up the MCP protocol handlers."""

        @self.server.list_resources()  # type: ignore[no-untyped-call, untyped-decorator]
        async def handle_list_resources() -> list[Resource]:
            return [
                Resource(
                    uri=AnyUrl(r.uri_pattern),
                    name=r.uri_pattern.rsplit("/", maxsplit=1)[-1],
                    description=r.description,
                    mimeType=r.mime_type,
                )
                for r in self.resources
            ]

        @self.server.read_resource()  # type: ignore[no-untyped-call, untyped-decorator]
        async def handle_read_resource(uri: str) -> str:
            uri_str = str(uri)
            for resource in self.resources:
                if resource.matches(uri_str):
                    return await resource.read(uri_str)
            raise ValueError(f"Resource not found: {uri_str}")

        @self.server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
        async def handle_list_tools() -> list[Tool]:
            tools_list = []
            for t in self.tools:
                output_schema = None
                if hasattr(t, "output_model") and getattr(t, "output_model", None) is not None:
                    output_schema = t.output_model.model_json_schema()
                tools_list.append(
                    Tool(
                        name=t.name,
                        description=t.description,
                        inputSchema=t.input_schema,
                        outputSchema=output_schema,
                    )
                )
            return tools_list

        @self.server.call_tool()  # type: ignore[untyped-decorator]
        async def handle_call_tool(
            name: str, arguments: dict[str, Any] | None
        ) -> CallToolResult | list[TextContent | ImageContent | EmbeddedResource]:
            call_id = uuid.uuid4().hex
            start_time = time.perf_counter()
            argument_keys = sorted((arguments or {}).keys())

            logger.debug(
                "Tool call received",
                extra={
                    "props": {
                        "call_id": call_id,
                        "tool_name": name,
                        "argument_keys": argument_keys,
                    }
                },
            )

            for tool in self.tools:
                if tool.name == name:
                    try:
                        note_context = NoteContext()

                        # 1. Execute target tool (guaranteed to return a BaseModel DTO)
                        result_dto = await tool.execute(arguments or {}, note_context)

                        # 2. Publish result to cache (resilient; returns None on failure)
                        cache_pub = None
                        if self.response_cache_manager is not None:
                            cache_pub = self.response_cache_manager.put(tool.name, result_dto)

                        # 3. Generate presentation output (resilient; formats DTO, notes, and resources)
                        if self.presenter is not None:
                            presented = self.presenter.present(
                                tool_name=tool.name,
                                data=result_dto,
                                notes=note_context.entries,
                                cache_pub=cache_pub,
                            )
                        else:
                            presented = PresentedOutput(text=str(result_dto), resources=[])

                        # 4. Construct and return normalized ToolResult
                        content: list[dict[str, Any]] = [{"type": "text", "text": presented.text}]
                        for res in presented.resources:
                            content.append(
                                {
                                    "type": "resource",
                                    "resource": {
                                        "uri": res.uri,
                                        "mimeType": res.mime_type,
                                        "text": res.content,
                                    },
                                }
                            )

                        success = getattr(result_dto, "success", True)
                        raw_result = ToolResult(content=content, is_error=not success)
                        response_content = self._convert_tool_result_to_mcp_result(raw_result)

                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        logger.debug(
                            "Tool call completed",
                            extra={
                                "props": {
                                    "call_id": call_id,
                                    "tool_name": name,
                                    "duration_ms": duration_ms,
                                }
                            },
                        )
                        return response_content
                    except asyncio.CancelledError:
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        logger.info(
                            "Tool call cancelled",
                            extra={
                                "props": {
                                    "call_id": call_id,
                                    "tool_name": name,
                                    "duration_ms": duration_ms,
                                }
                            },
                        )
                        raise
                    except Exception as e:
                        duration_ms = (time.perf_counter() - start_time) * 1000.0
                        logger.error(
                            "Response processing failed: %s",
                            e,
                            exc_info=True,
                            extra={
                                "props": {
                                    "call_id": call_id,
                                    "tool_name": name,
                                    "duration_ms": duration_ms,
                                    "error_type": type(e).__name__,
                                }
                            },
                        )
                        return [
                            TextContent(type="text", text=f"Error processing tool response: {e!s}")
                        ]
            raise ValueError(f"Tool not found: {name}")

    async def run(self) -> None:
        """Run the MCP server."""
        server_name = self._settings.server.name

        logger.info("Starting MCP server: %s", server_name)
        lifecycle_logger.info("MCP server running")

        # Force LF only on Windows to prevent "invalid trailing data"
        # and other CRLF issues in the JSON-RPC stream
        stdout = anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n"))

        try:
            async with stdio_server(stdout=stdout) as (read_stream, write_stream):
                await self.server.run(
                    read_stream, write_stream, self.server.create_initialization_options()
                )
        except KeyboardInterrupt:
            lifecycle_logger.info("MCP server interrupted by user")
        finally:
            lifecycle_logger.info("MCP server shutting down")

    async def shutdown(self) -> None:
        """Shutdown the MCP server gracefully."""
        lifecycle_logger.info("MCP server shutting down")


class DegradedMCPServer(MCPServer):
    """Degraded MCP server initialized when a config error occurs."""

    def __init__(self, settings: Settings, reason: str) -> None:
        """Initialize the degraded server with only the health check tool."""
        from mcp_server.schemas.tool_outputs import HealthStatus  # noqa: PLC0415
        from mcp_server.tools.health_tools import HealthCheckTool  # noqa: PLC0415

        health_tool = HealthCheckTool(
            override_status=HealthStatus.UNHEALTHY,
            override_reason=reason,
        )

        super().__init__(
            settings=settings,
            tools=[health_tool],
            resources=[],
            presenter=None,
            publisher=None,
        )
