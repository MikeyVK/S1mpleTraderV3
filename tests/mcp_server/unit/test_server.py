# pyright: reportMissingImports=false
"""Tests for MCP Server tool registration and dispatch hooks."""

import logging
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams

from mcp_server.core.exceptions import ConfigError
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.state_repository import InMemoryStateRepository
from mcp_server.server import MCPServer
from mcp_server.tools.base import BaseTool
from mcp_server.tools.git_tools import CreateBranchTool
from mcp_server.tools.phase_tools import ForcePhaseTransitionTool, TransitionPhaseTool
from mcp_server.tools.tool_result import ToolResult


def _patch_server_settings(
    mock: MagicMock,
    workspace_root: str = ".",
    token: str | None = None,
) -> None:
    """Configure a Settings class mock for server tests."""
    mock.from_env.return_value.server.name = "test-server"
    mock.from_env.return_value.server.workspace_root = workspace_root
    mock.from_env.return_value.github.token = token
    mock.from_env.return_value.github.owner = "test"
    mock.from_env.return_value.github.repo = "repo"
    mock.from_env.return_value.logging.level = "INFO"
    mock.from_env.return_value.logging.audit_log = ".logs/mcp_audit.log"


class TestServerToolRegistration:
    """Tests for server tool registration."""

    def test_github_tools_always_registered(self) -> None:
        """GitHub tools should always be registered, even without token."""
        with patch("mcp_server.server.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls)

            server = MCPServer()
            tool_names = [t.name for t in server.tools]

            assert "create_issue" in tool_names
            assert "list_issues" in tool_names
            assert "get_issue" in tool_names
            assert "close_issue" in tool_names

    def test_github_tools_registered_with_token(self) -> None:
        """GitHub tools should be registered when token is configured."""
        with (
            patch("mcp_server.server.Settings") as mock_settings_cls,
            patch("mcp_server.resources.github.GitHubManager") as mock_res_manager,
            patch("mcp_server.tools.pr_tools.GitHubManager") as mock_pr_manager,
            patch("mcp_server.tools.label_tools.GitHubManager") as mock_label_manager,
        ):
            _patch_server_settings(mock_settings_cls, token="test-token")

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

            async def execute(self, params: object) -> ToolResult:
                del params
                return ToolResult.text("ok")

        with patch("mcp_server.server.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls)

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

    @pytest.mark.asyncio
    async def test_call_tool_pre_enforcement_blocks_invalid_create_branch_base(
        self,
        tmp_path: Path,
    ) -> None:
        """Dispatch pre-hook should block invalid branch creation before tool execution."""
        config_dir = tmp_path / ".st3" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "enforcement.yaml").write_text(
            """
            enforcement:
              - event_source: tool
                tool: create_branch
                timing: pre
                actions:
                  - type: check_branch_policy
                    rules:
                      feature: [main, \"epic/*\"]
            """,
            encoding="utf-8",
        )

        with patch("mcp_server.server.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls, workspace_root=str(tmp_path))

            manager = MagicMock()
            server = MCPServer()
            server.tools = [CreateBranchTool(manager=manager)]
            handler = server.server.request_handlers[CallToolRequest]

            req = CallToolRequest(
                params=CallToolRequestParams(
                    name="create_branch",
                    arguments={
                        "name": "new-thing",
                        "branch_type": "feature",
                        "base_branch": "release/1.0",
                    },
                )
            )
            response = await handler(req)

        assert "cannot be created from base" in response.root.content[0].text
        manager.create_branch.assert_not_called()

    @pytest.mark.asyncio
    async def test_call_tool_post_enforcement_commits_state_files_after_transition(
        self,
        tmp_path: Path,
    ) -> None:
        """Dispatch post-hook should commit state files after a successful transition."""
        config_dir = tmp_path / ".st3" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "enforcement.yaml").write_text(
            """
            enforcement:
              - event_source: tool
                tool: transition_phase
                timing: post
                actions:
                  - type: commit_state_files
                    paths: [\".st3/state.json\"]
                    message: persist state after phase transition
            """,
            encoding="utf-8",
        )

        project_manager = ProjectManager(workspace_root=tmp_path)
        project_manager.initialize_project(
            issue_number=257,
            issue_title="Cycle 5 enforcement",
            workflow_name="feature",
        )
        state_engine = PhaseStateEngine(
            workspace_root=tmp_path,
            project_manager=project_manager,
            state_repository=InMemoryStateRepository(),
        )
        state_engine.initialize_branch(
            branch="feature/257-reorder-workflow-phases",
            issue_number=257,
            initial_phase="research",
        )

        with (
            patch("mcp_server.server.Settings") as mock_settings_cls,
            patch(
                "mcp_server.managers.enforcement_runner.GitManager.commit_with_scope"
            ) as mock_commit,
        ):
            _patch_server_settings(mock_settings_cls, workspace_root=str(tmp_path))
            mock_commit.return_value = "abc1234"

            server = MCPServer()
            server.tools = [TransitionPhaseTool(workspace_root=tmp_path)]
            handler = server.server.request_handlers[CallToolRequest]

            req = CallToolRequest(
                params=CallToolRequestParams(
                    name="transition_phase",
                    arguments={
                        "branch": "feature/257-reorder-workflow-phases",
                        "to_phase": "planning",
                        "human_approval": "Move into planning",
                    },
                )
            )
            response = await handler(req)

        assert "Successfully transitioned" in response.root.content[0].text
        mock_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_tool_force_phase_post_enforcement_returns_warning(
        self,
        tmp_path: Path,
    ) -> None:
        """Force phase transitions should warn on hook failures instead of blocking."""
        with patch("mcp_server.server.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls, workspace_root=str(tmp_path))

            server = MCPServer()
            server.tools = [ForcePhaseTransitionTool(workspace_root=tmp_path)]
            handler = server.server.request_handlers[CallToolRequest]

            with (
                patch.object(server.enforcement_runner, "run") as mock_run,
                patch.object(
                    ForcePhaseTransitionTool,
                    "execute",
                    new=AsyncMock(return_value=ToolResult.text("✅ Forced phase transition")),
                ),
            ):

                def side_effect(*_args: object, **kwargs: object) -> list[str]:
                    if kwargs.get("event") == "transition_phase" and kwargs.get("timing") == "post":
                        raise ConfigError("post hook failed")
                    return []

                mock_run.side_effect = side_effect
                req = CallToolRequest(
                    params=CallToolRequestParams(
                        name="force_phase_transition",
                        arguments={
                            "branch": "feature/257-reorder-workflow-phases",
                            "to_phase": "planning",
                            "skip_reason": "Force test",
                            "human_approval": "Approved",
                        },
                    )
                )
                response = await handler(req)

        text = response.root.content[0].text
        assert "⚠️" in text
        assert "post hook failed" in text
        assert "✅" in text
