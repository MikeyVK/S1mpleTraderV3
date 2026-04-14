# pyright: reportMissingImports=false
# tests\mcp_server\unit\tools\test_cycle_tools.py
# template=unit_test version=3d15d309 created=2026-03-13T11:30Z updated=
"""Unit tests for the renamed cycle tools module and dispatch hooks.

@layer: Tests (Unit)
@dependencies: pytest, mcp.types, mcp_server.tools.cycle_tools, tests.mcp_server.test_support
"""

from pathlib import Path
from shutil import copytree
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams

from mcp_server.core.exceptions import ConfigError
from mcp_server.core.operation_notes import NoteContext
from mcp_server.server import MCPServer
from mcp_server.tools.cycle_tools import (
    ForceCycleTransitionInput,
    ForceCycleTransitionTool,
    TransitionCycleTool,
)
from mcp_server.tools.tool_result import ToolResult
from tests.mcp_server.test_support import (
    make_git_manager,
    make_phase_state_engine,
    make_project_manager,
)


class FakeForceCycleStateEngine:
    """Minimal force-cycle state engine fake for wrapper tests."""

    def __init__(self, result: dict[str, object]) -> None:
        self._result = result
        self.last_call: dict[str, object] | None = None

    def force_cycle_transition(
        self,
        *,
        branch: str,
        to_cycle: int,
        skip_reason: str,
        human_approval: str,
        gate_runner: object | None = None,
    ) -> dict[str, object]:
        self.last_call = {
            "branch": branch,
            "to_cycle": to_cycle,
            "skip_reason": skip_reason,
            "human_approval": human_approval,
            "gate_runner": gate_runner,
        }
        return self._result


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
    async def test_call_tool_post_enforcement_runs_after_cycle_transition(
        self,
        tmp_path: Path,
    ) -> None:
        """Dispatch post-hook should still run after a successful cycle transition."""
        config_dir = tmp_path / ".st3" / "config"
        copytree(Path.cwd() / ".st3" / "config", config_dir, dirs_exist_ok=True)

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

            server = MCPServer()
            server.tools = [
                TransitionCycleTool(
                    workspace_root=tmp_path,
                    project_manager=server.project_manager,
                    state_engine=server.phase_state_engine,
                    git_manager=server.git_manager,
                    gate_runner=server.workflow_gate_runner,
                ),
            ]
            handler = server.server.request_handlers[CallToolRequest]

            with patch.object(
                server.enforcement_runner,
                "run",
                return_value=[],
            ) as mock_run:
                req = CallToolRequest(
                    params=CallToolRequestParams(
                        name="transition_cycle",
                        arguments={"to_cycle": 1, "issue_number": 257},
                    )
                )
                response = await handler(req)

        assert "✅" in response.root.content[0].text
        assert any(
            call.kwargs.get("event") == "transition_cycle" and call.kwargs.get("timing") == "post"
            for call in mock_run.call_args_list
        )

    @pytest.mark.asyncio
    async def test_call_tool_force_cycle_post_enforcement_returns_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Force cycle transitions should fail when post-enforcement raises."""
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
                    gate_runner=server.workflow_gate_runner,
                ),
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
        assert "cycle hook failed" in text
        assert "⚠️" not in text
        assert "✅" not in text


class TestForceCycleToolFormatting:
    """Formatting tests for the shared force-cycle gate report path."""

    @pytest.mark.asyncio
    async def test_force_cycle_tool_formats_blocking_gates_before_success(
        self,
        tmp_path: Path,
    ) -> None:
        """Blocking gate warnings must appear before the success line."""
        gate_runner = object()
        git_manager = MagicMock()
        git_manager.get_current_branch.return_value = "feature/257-cycle-orchestration"
        state_engine = FakeForceCycleStateEngine(
            {
                "success": True,
                "from_cycle": 2,
                "to_cycle": 4,
                "total_cycles": 4,
                "cycle_name": "Cycle orchestration",
                "skipped_gates": ["cycle-checklist"],
                "passing_gates": ["cycle-docs"],
            }
        )
        tool = ForceCycleTransitionTool(
            workspace_root=tmp_path,
            project_manager=MagicMock(),
            state_engine=state_engine,
            git_manager=git_manager,
            gate_runner=gate_runner,
        )

        result = await tool.execute(
            ForceCycleTransitionInput(
                to_cycle=4,
                skip_reason="audited skip",
                human_approval="Verifier approved",
                issue_number=257,
            ),
            NoteContext(),
        )

        assert not result.is_error
        assert state_engine.last_call is not None
        assert state_engine.last_call["gate_runner"] is gate_runner
        text = result.content[0]["text"]
        assert "ACTION REQUIRED" in text
        assert "cycle-checklist" in text
        assert text.index("ACTION REQUIRED") < text.index("✅")

    @pytest.mark.asyncio
    async def test_force_cycle_tool_formats_passing_gates_after_success(
        self,
        tmp_path: Path,
    ) -> None:
        """Passing gate information must remain informational after the success line."""
        git_manager = MagicMock()
        git_manager.get_current_branch.return_value = "feature/257-cycle-orchestration"
        state_engine = FakeForceCycleStateEngine(
            {
                "success": True,
                "from_cycle": 2,
                "to_cycle": 3,
                "total_cycles": 4,
                "cycle_name": "State recovery",
                "skipped_gates": [],
                "passing_gates": ["cycle-docs"],
            }
        )
        tool = ForceCycleTransitionTool(
            workspace_root=tmp_path,
            project_manager=MagicMock(),
            state_engine=state_engine,
            git_manager=git_manager,
            gate_runner=object(),
        )

        result = await tool.execute(
            ForceCycleTransitionInput(
                to_cycle=3,
                skip_reason="audited skip",
                human_approval="Verifier approved",
                issue_number=257,
            ),
            NoteContext(),
        )

        assert not result.is_error
        text = result.content[0]["text"]
        assert "✅" in text
        assert "cycle-docs" in text
        assert text.index("✅") < text.index("cycle-docs")
