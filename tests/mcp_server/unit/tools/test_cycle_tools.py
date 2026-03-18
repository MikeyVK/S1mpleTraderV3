# pyright: reportMissingImports=false
# tests\mcp_server\unit\tools\test_cycle_tools.py
# template=unit_test version=3d15d309 created=2026-03-13T11:30Z updated=
"""Unit tests for the renamed cycle tools module and dispatch hooks."""

from pathlib import Path
from shutil import copytree
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams

from mcp_server.core.exceptions import ConfigError
from mcp_server.managers.state_repository import InMemoryStateRepository
from mcp_server.server import MCPServer
from mcp_server.tools.cycle_tools import ForceCycleTransitionTool, TransitionCycleTool
from mcp_server.tools.tool_result import ToolResult
from tests.mcp_server.test_support import (
    make_git_manager,
    make_phase_state_engine,
    make_project_manager,
)


class TestCycleTools:
    """Cycle tool rename, injection, and enforcement tests."""

    def test_cycle_tools_require_workspace_root_and_define_enforcement_events(
        self,
        tmp_path: Path,
    ) -> None:
        """Cycle tools should use constructor-injected workspace roots and hook metadata."""
        project_manager = make_project_manager(tmp_path)
        state_engine = make_phase_state_engine(tmp_path, project_manager=project_manager)
        git_manager = make_git_manager(tmp_path)
        transition_tool = TransitionCycleTool(
            workspace_root=tmp_path,
            project_manager=project_manager,
            state_engine=state_engine,
            git_manager=git_manager,
        )
        force_tool = ForceCycleTransitionTool(
            workspace_root=tmp_path,
            project_manager=project_manager,
            state_engine=state_engine,
            git_manager=git_manager,
        )

        assert transition_tool.workspace_root == tmp_path
        assert force_tool.workspace_root == tmp_path
        assert transition_tool.enforcement_event == "transition_cycle"
        assert force_tool.enforcement_event == "transition_cycle"

    @pytest.mark.asyncio
    async def test_call_tool_post_enforcement_commits_state_files_after_cycle_transition(
        self,
        tmp_path: Path,
    ) -> None:
        """Dispatch post-hook should commit state files after a successful cycle transition."""
        config_dir = tmp_path / ".st3" / "config"
        copytree(Path.cwd() / ".st3" / "config", config_dir, dirs_exist_ok=True)
        (config_dir / "enforcement.yaml").write_text(
            """
            enforcement:
              - event_source: tool
                tool: transition_cycle
                timing: post
                actions:
                  - type: commit_state_files
                    paths: [\".st3/state.json\"]
                    message: persist state after cycle transition
            """,
            encoding="utf-8",
        )

        project_manager = make_project_manager(tmp_path)
        project_manager.initialize_project(
            issue_number=257,
            issue_title="Cycle 5.1 enforcement",
            workflow_name="feature",
        )
        project_manager.save_planning_deliverables(
            257,
            {
                "tdd_cycles": {
                    "total": 2,
                    "cycles": [
                        {
                            "cycle_number": 1,
                            "name": "One",
                            "deliverables": ["cycle-1"],
                            "exit_criteria": "pass",
                        },
                        {
                            "cycle_number": 2,
                            "name": "Two",
                            "deliverables": ["cycle-2"],
                            "exit_criteria": "pass",
                        },
                    ],
                }
            },
        )
        state_engine = make_phase_state_engine(
            tmp_path,
            project_manager=project_manager,
            state_repository=InMemoryStateRepository(),
        )
        branch = "feature/257-reorder-workflow-phases"
        state_engine.initialize_branch(
            branch=branch,
            issue_number=257,
            initial_phase="implementation",
        )

        with (
            patch("mcp_server.server.Settings") as mock_settings_cls,
            patch(
                "mcp_server.managers.enforcement_runner.GitManager.commit_with_scope"
            ) as mock_commit,
            patch("mcp_server.tools.cycle_tools.GitManager") as mock_git_class,
            patch(
                "mcp_server.tools.cycle_tools.TransitionCycleTool.execute",
                new=AsyncMock(
                    return_value=ToolResult.text("✅ Transitioned to TDD Cycle 1/2: One")
                ),
            ),
        ):
            mock_settings_cls.from_env.return_value.server.name = "test-server"
            mock_settings_cls.from_env.return_value.server.workspace_root = str(tmp_path)
            mock_settings_cls.from_env.return_value.server.config_root = str(
                tmp_path / ".st3" / "config"
            )
            mock_settings_cls.from_env.return_value.github.token = None
            mock_settings_cls.from_env.return_value.github.owner = "test"
            mock_settings_cls.from_env.return_value.github.repo = "repo"
            mock_settings_cls.from_env.return_value.logging.level = "INFO"
            mock_settings_cls.from_env.return_value.logging.audit_log = ".logs/mcp_audit.log"
            mock_commit.return_value = "abc1234"
            mock_git = MagicMock()
            mock_git.get_current_branch.return_value = branch
            mock_git_class.return_value = mock_git

            server = MCPServer()
            server.tools = [
                TransitionCycleTool(
                    workspace_root=tmp_path,
                    project_manager=server.project_manager,
                    state_engine=server.phase_state_engine,
                    git_manager=server.git_manager,
                )
            ]
            handler = server.server.request_handlers[CallToolRequest]

            req = CallToolRequest(
                params=CallToolRequestParams(
                    name="transition_cycle",
                    arguments={"to_cycle": 1, "issue_number": 257},
                )
            )
            response = await handler(req)

        assert "✅" in response.root.content[0].text
        mock_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_tool_force_cycle_post_enforcement_returns_warning(
        self,
        tmp_path: Path,
    ) -> None:
        """Force cycle transitions should warn on hook failures instead of blocking."""
        config_dir = tmp_path / ".st3" / "config"
        copytree(Path.cwd() / ".st3" / "config", config_dir, dirs_exist_ok=True)

        with patch("mcp_server.server.Settings") as mock_settings_cls:
            mock_settings_cls.from_env.return_value.server.name = "test-server"
            mock_settings_cls.from_env.return_value.server.workspace_root = str(tmp_path)
            mock_settings_cls.from_env.return_value.server.config_root = str(
                tmp_path / ".st3" / "config"
            )
            mock_settings_cls.from_env.return_value.github.token = None
            mock_settings_cls.from_env.return_value.github.owner = "test"
            mock_settings_cls.from_env.return_value.github.repo = "repo"
            mock_settings_cls.from_env.return_value.logging.level = "INFO"
            mock_settings_cls.from_env.return_value.logging.audit_log = ".logs/mcp_audit.log"

            server = MCPServer()
            server.tools = [
                ForceCycleTransitionTool(
                    workspace_root=tmp_path,
                    project_manager=server.project_manager,
                    state_engine=server.phase_state_engine,
                    git_manager=server.git_manager,
                )
            ]
            handler = server.server.request_handlers[CallToolRequest]

            with (
                patch.object(server.enforcement_runner, "run") as mock_run,
                patch.object(
                    ForceCycleTransitionTool,
                    "execute",
                    new=AsyncMock(return_value=ToolResult.text("✅ Forced cycle transition")),
                ),
            ):

                def side_effect(*_args: object, **kwargs: object) -> list[str]:
                    if kwargs.get("event") == "transition_cycle" and kwargs.get("timing") == "post":
                        raise ConfigError("cycle hook failed")
                    return []

                mock_run.side_effect = side_effect
                req = CallToolRequest(
                    params=CallToolRequestParams(
                        name="force_cycle_transition",
                        arguments={
                            "to_cycle": 2,
                            "skip_reason": "Force test",
                            "human_approval": "Approved",
                            "issue_number": 257,
                        },
                    )
                )
                response = await handler(req)

        text = response.root.content[0].text
        assert "⚠️" in text
        assert "cycle hook failed" in text
        assert "✅" in text
