"""Tests for MCP Server tool registration."""

import logging
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams

from mcp_server.server import MCPServer
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class TestServerToolRegistration:
    """Tests for server tool registration."""

    def test_github_tools_always_registered(self) -> None:
        """GitHub tools should always be registered, even without token."""
        with patch("mcp_server.server.settings") as mock_settings:
            mock_settings.server.name = "test-server"
            mock_settings.github.token = None
            mock_settings.github.owner = "test"
            mock_settings.github.repo = "repo"

            server = MCPServer()
            tool_names = [t.name for t in server.tools]

            assert "create_issue" in tool_names
            assert "list_issues" in tool_names
            assert "get_issue" in tool_names
            assert "close_issue" in tool_names

    def test_github_tools_registered_with_token(self) -> None:
        """GitHub tools should be registered when token is configured."""
        with (
            patch("mcp_server.server.settings") as mock_settings,
            patch("mcp_server.resources.github.GitHubManager") as mock_res_manager,
            patch("mcp_server.tools.pr_tools.GitHubManager") as mock_pr_manager,
            patch("mcp_server.tools.label_tools.GitHubManager") as mock_label_manager,
        ):
            mock_settings.server.name = "test-server"
            mock_settings.github.token = "test-token"
            mock_settings.github.owner = "test"
            mock_settings.github.repo = "repo"

            mock_res_manager.return_value = MagicMock()
            mock_pr_manager.return_value = MagicMock()
            mock_label_manager.return_value = MagicMock()

            server = MCPServer()
            tool_names = [t.name for t in server.tools]

            assert "create_issue" in tool_names
            assert "list_issues" in tool_names
            assert "get_issue" in tool_names
            assert "close_issue" in tool_names
            assert "create_pr" in tool_names
            assert "add_labels" in tool_names

    @pytest.mark.asyncio
    async def test_call_tool_logging_has_call_id_and_duration(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """call_tool handler should log correlation id and duration."""

        class DummyTool(BaseTool):
            """Dummy tool for testing server call_tool logging."""

            name = "dummy_tool"
            description = "Dummy tool"
            args_model = None

            async def execute(self, params: Any) -> ToolResult:  # noqa: ANN401
                """Return a simple success result."""
                del params
                return ToolResult.text("ok")

        with patch("mcp_server.server.settings") as mock_settings:
            mock_settings.server.name = "test-server"
            mock_settings.github.token = None
            mock_settings.github.owner = "test"
            mock_settings.github.repo = "repo"

            server = MCPServer()
            server.tools = [DummyTool()]

            handler = server.server.request_handlers[CallToolRequest]

            caplog.set_level(logging.DEBUG, logger="mcp_server.server")

            req = CallToolRequest(
                params=CallToolRequestParams(
                    name="dummy_tool",
                    arguments={"a": 1},
                )
            )
            await handler(req)

        start_logs = [
            r
            for r in caplog.records
            if r.name == "mcp_server.server" and r.getMessage() == "Tool call received"
        ]
        assert start_logs
        start_props = cast(dict[str, Any], getattr(start_logs[0], "props", {}))
        assert start_props["tool_name"] == "dummy_tool"
        assert "call_id" in start_props

        done_logs = [
            r
            for r in caplog.records
            if r.name == "mcp_server.server" and r.getMessage() == "Tool call completed"
        ]
        assert done_logs
        done_props = cast(dict[str, Any], getattr(done_logs[0], "props", {}))
        assert done_props["tool_name"] == "dummy_tool"
        assert done_props["call_id"] == start_props["call_id"]
        assert "duration_ms" in done_props
