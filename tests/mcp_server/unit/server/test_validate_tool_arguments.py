"""
Unit tests for _validate_tool_arguments failure path and schema://validation resource.
Scope: Cycle 2, Change A — argument validation returns ToolResult on failure.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams, EmbeddedResource
from pydantic import BaseModel, Field

from mcp_server.core.interfaces.icore_tool import ICoreTool
from mcp_server.core.operation_notes import NoteContext
from mcp_server.core.tool_factory import ToolFactory
from mcp_server.server import MCPServer
from mcp_server.tools.tool_result import ToolResult
from tests.mcp_server.test_support import get_default_server_root, make_test_server

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_server_settings(mock: MagicMock, workspace_root: str | None = None) -> None:
    from tests.mcp_server.test_support import RealSettings  # noqa: PLC0415

    resolved_workspace_root = workspace_root or str(Path(__file__).resolve().parents[4])
    server_root_dir = get_default_server_root()

    settings = RealSettings.from_env()
    settings.server.name = "test-server"
    settings.server.workspace_root = resolved_workspace_root
    settings.server.config_root = None
    settings.server.server_root_dir = server_root_dir
    settings.github.token = None
    settings.github.owner = "test"
    settings.github.repo = "test-repo"
    settings.logging.level = "WARNING"
    settings.server.logs_dir = "logs"
    settings.logging.audit_log = None

    mock.return_value = settings
    mock.from_env.return_value = settings


# ---------------------------------------------------------------------------
# Mock tool
# ---------------------------------------------------------------------------


class SimpleInput(BaseModel):
    required_field: str = Field(description="A required string field.")
    optional_field: int = Field(default=42, description="An optional integer.")


class MockSimpleTool(ICoreTool[SimpleInput, ToolResult]):
    """Minimal mock tool for argument validation tests."""

    @property
    def name(self) -> str:
        return "mock_simple"

    @property
    def description(self) -> str:
        return "Mock simple tool"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return SimpleInput

    async def execute(self, params: SimpleInput, context: NoteContext) -> ToolResult:  # noqa: ARG002
        return ToolResult(content=[{"type": "text", "text": "OK"}])

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return normalized schema (from Cycle 1, no $defs/$ref)."""
        return {
            "type": "object",
            "properties": {
                "required_field": {"type": "string", "description": "A required string field."},
                "optional_field": {"type": "integer", "description": "An optional integer."},
            },
            "required": ["required_field"],
        }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValidateToolArgumentsFailurePath:
    """Test suite for _validate_tool_arguments return type and schema resource."""

    @pytest.fixture
    def server(self) -> MCPServer:
        """Minimal MCPServer instance for testing _validate_tool_arguments."""
        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls)
            s = make_test_server()

            factory = ToolFactory(
                enforcement_runner=MagicMock(),
                workspace_root=Path(s._workspace_root)  # type: ignore[reportPrivateUsage]
                if hasattr(s, "_workspace_root")
                else Path("."),
            )
            s.tools.append(factory.create_tool(MockSimpleTool()))
            return s

    @pytest.mark.asyncio
    async def test_returns_tool_result_on_validation_error(self, server: MCPServer) -> None:
        """
        RED condition: When Pydantic validation fails (missing required field),
        the call_tool handler returns a result with isError=True.
        """
        invalid_args = {"optional_field": 99}

        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="mock_simple",
                arguments=invalid_args,
            )
        )
        with patch("jsonschema.validate"):
            response = await handler(req)
        result = response.root

        assert hasattr(result, "isError"), "Result must have isError"
        assert result.isError is True, "isError must be True for validation failure"

    @pytest.mark.asyncio
    async def test_failure_includes_schema_resource(self, server: MCPServer) -> None:
        """
        RED condition: The failure response must include a schema://validation
        EmbeddedResource with the valid input schema in JSON.
        """
        invalid_args = {"unknown_field": "typo"}

        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="mock_simple",
                arguments=invalid_args,
            )
        )
        with patch("jsonschema.validate"):
            response = await handler(req)
        result = response.root
        assert result.isError is True

        resource_items = [c for c in result.content if isinstance(c, EmbeddedResource)]
        assert len(resource_items) > 0, "Expected schema://validation resource in failure response"
        resource = resource_items[0].resource
        assert str(resource.uri) == "schema://validation", (
            f"Expected uri=schema://validation, got {resource.uri}"
        )
        assert resource.mimeType == "application/json", (
            f"Expected application/json, got {resource.mimeType}"
        )

        schema = json.loads(resource.text)
        assert isinstance(schema, dict), "schema must be a dict"
        assert "properties" in schema, "schema must have properties"
        assert "required_field" in schema["properties"], "required_field must be in properties"
        assert "description" in schema["properties"]["required_field"], (
            "Field description must be preserved in schema"
        )

    @pytest.mark.asyncio
    async def test_failure_includes_diagnostic_text(self, server: MCPServer) -> None:
        """
        RED condition: The response includes human-readable diagnostic text
        explaining what validation failed.
        """
        invalid_args = {"optional_field": "not-an-integer"}

        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="mock_simple",
                arguments=invalid_args,
            )
        )
        with patch("jsonschema.validate"):
            response = await handler(req)
        result = response.root
        assert result.isError is True

        text_items = [c for c in result.content if getattr(c, "type", None) == "text"]
        assert len(text_items) > 0, "Expected diagnostic text in failure response"

        text_content = text_items[0].text
        assert "Invalid input" in text_content, (
            f"Diagnostic text must mention 'Invalid input', got: {text_content}"
        )
        assert "mock_simple" in text_content, (
            f"Diagnostic text must mention tool name, got: {text_content}"
        )

    @pytest.mark.asyncio
    async def test_success_returns_model_instance(self, server: MCPServer) -> None:
        """
        Happy path: When validation succeeds, the call_tool handler executes
        the tool and returns the expected result content.
        """
        valid_args = {"required_field": "hello"}

        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="mock_simple",
                arguments=valid_args,
            )
        )
        with patch("jsonschema.validate"):
            response = await handler(req)
        result = response.root

        assert getattr(result, "isError", False) is False
        assert len(result.content) == 1
        assert "OK" in result.content[0].text

    @pytest.mark.asyncio
    async def test_schema_is_normalized_no_defs_no_ref(self, server: MCPServer) -> None:
        """
        RED condition: The schema://validation resource must not contain
        $defs or $ref (Cycle 1 guarantee: all schemas are normalized).
        """
        invalid_args = {}

        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="mock_simple",
                arguments=invalid_args,
            )
        )
        with patch("jsonschema.validate"):
            response = await handler(req)
        result = response.root
        assert result.isError is True

        resource_items = [c for c in result.content if isinstance(c, EmbeddedResource)]
        schema = json.loads(resource_items[0].resource.text)

        assert "$defs" not in schema, "Schema must not contain $defs (Cycle 1 guarantee)"
        assert "$ref" not in json.dumps(schema), "Schema must not contain $ref anywhere"
