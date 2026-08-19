"""
Integration test: End-to-end validation failure response via handle_call_tool.
Scope: Cycle 2, Change A — ensures early-return guard works correctly.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from mcp.types import CallToolRequest, CallToolRequestParams, EmbeddedResource
from pydantic import BaseModel, ConfigDict

from mcp_server.bootstrap import ServerBootstrapper, TemplateRegistry
from mcp_server.config.settings import Settings
from mcp_server.core.interfaces.icore_tool import ICoreTool
from mcp_server.core.tool_factory import ToolFactory
from mcp_server.server import MCPServer
from mcp_server.tools.tool_result import ToolResult
from tests.mcp_server.test_support import make_test_server


class IntegrationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str


class MockIntegrationTool(ICoreTool[IntegrationInput, ToolResult]):
    """Mock tool for integration testing."""

    @property
    def name(self) -> str:
        return "MockIntegrationTool"

    @property
    def description(self) -> str:
        return "Mock integration tool"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return IntegrationInput

    async def execute(
        self,
        params: IntegrationInput,
        context: Any,
    ) -> ToolResult:
        return ToolResult(content=[{"type": "text", "text": f"Action: {params.action}"}])

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "The action to perform."},
            },
            "required": ["action"],
        }


class TestStrictInputValidationResponse:
    """Integration test: validation failure flows through MCP response pipeline."""

    @pytest_asyncio.fixture
    async def server(self) -> MCPServer:
        """MCPServer with MockIntegrationTool registered."""
        settings = Settings.from_env()
        bootstrapper = ServerBootstrapper(settings)
        configs = bootstrapper._build_config_layer()  # type: ignore[reportPrivateUsage]
        workspace_root = Path(settings.server.workspace_root)
        server_root = workspace_root / settings.server.server_root_dir
        template_registry = TemplateRegistry(registry_path=server_root / "template_registry.json")
        managers = bootstrapper._build_manager_graph(configs, template_registry)  # type: ignore[reportPrivateUsage]

        s = make_test_server()

        factory = ToolFactory(
            enforcement_runner=managers.enforcement_runner,
            workspace_root=workspace_root,
        )
        s.tools.append(factory.create_tool(MockIntegrationTool()))
        return s

    @pytest.mark.asyncio
    async def test_extra_field_returns_call_tool_result_error(  # noqa: ANN201
        self, server: MCPServer
    ):
        """
        Integration test: end-to-end validation failure path.
        When an extra unknown field is supplied, the call_tool handler returns a
        CallToolResult with isError=True.
        """
        extra_field_args = {"action": "test", "unknown_field": "typo"}

        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="MockIntegrationTool",
                arguments=extra_field_args,
            )
        )
        with patch("jsonschema.validate"):
            response = await handler(req)
        result = response.root

        assert hasattr(result, "isError"), "Result must have isError"
        assert result.isError is True

    @pytest.mark.asyncio
    async def test_schema_resource_in_error_response(  # noqa: ANN201
        self, server: MCPServer
    ):
        """
        Integration test: error response includes schema://validation resource
        so the agent can learn the valid input structure.
        """
        extra_field_args = {"action": "test", "unknown_field": "typo"}

        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="MockIntegrationTool",
                arguments=extra_field_args,
            )
        )
        with patch("jsonschema.validate"):
            response = await handler(req)
        result = response.root
        assert result.isError is True

        # content on CallToolResult contains MCP TextContent / EmbeddedResource objects
        content = result.content
        assert isinstance(content, list), "content must be a list"

        # Look for embedded resource item (schema://validation)
        resource_items = [c for c in content if isinstance(c, EmbeddedResource)]
        assert len(resource_items) > 0, "Expected schema://validation EmbeddedResource"

        resource = resource_items[0].resource
        assert str(resource.uri) == "schema://validation"
        assert resource.mimeType == "application/json"

        schema = json.loads(resource.text)
        assert "properties" in schema
        assert "action" in schema["properties"]
