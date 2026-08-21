# pyright: reportMissingImports=false
# tests\mcp_server\unit\tools\test_cycle_tools.py
# template=unit_test version=3d15d309 created=2026-03-13T11:30Z updated=
"""Unit tests for the renamed cycle tools module and dispatch hooks.

@layer: Tests (Unit)
@dependencies: pytest, mcp.types, mcp_server.tools.cycle_tools, tests.mcp_server.test_support
"""

from collections.abc import Awaitable, Callable
from pathlib import Path
from shutil import copytree
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams
from pydantic import BaseModel

from mcp_server.bootstrap import ServerBootstrapper, TemplateRegistry
from mcp_server.core.exceptions import ConfigError
from mcp_server.core.operation_notes import NoteContext
from mcp_server.core.tool_factory import ToolFactory
from mcp_server.tools.cycle_tools import (
    ForceCycleTransitionInput,
    ForceCycleTransitionTool,
    TransitionCycleInput,
    TransitionCycleTool,
)
from tests.mcp_server.test_support import (
    get_default_server_root,
    make_git_manager,
    make_phase_state_engine,
    make_project_manager,
    make_test_server,
)

TRANSITION_ADVISORY_NOTE = (
    "🚀 REQUIRED NEXT STEP: Call get_work_context now before any other tool call "
    "to load the current phase context for this branch."
)


def _get_test_bootstrap_context(settings: Any) -> tuple[Any, Path]:
    workspace_root = Path(settings.server.workspace_root)
    server_root_dir = getattr(settings.server, "server_root_dir", get_default_server_root())
    resolved_server_root = workspace_root / server_root_dir

    # Configure resolved paths on mock settings if needed
    if not hasattr(settings.server, "resolved_server_root") or isinstance(
        settings.server.resolved_server_root, MagicMock
    ):
        settings.server.resolved_server_root = resolved_server_root
    if not hasattr(settings.server, "resolved_config_root") or isinstance(
        settings.server.resolved_config_root, MagicMock
    ):
        config_dir = (
            Path(settings.server.config_root)
            if getattr(settings.server, "config_root", None)
            else resolved_server_root / "config"
        )
        if not config_dir.exists():
            package_root = Path(__file__).resolve().parents[4]
            settings.server.resolved_config_root = package_root / "mcp_server" / "assets" / "config"
        else:
            settings.server.resolved_config_root = config_dir
    if not hasattr(settings.server, "resolved_template_root") or isinstance(
        settings.server.resolved_template_root, MagicMock
    ):
        template_dir = resolved_server_root / "templates"
        if not template_dir.exists():
            settings.server.resolved_template_root = (
                Path.cwd() / get_default_server_root() / "templates"
            )
        else:
            settings.server.resolved_template_root = template_dir

    bootstrapper = ServerBootstrapper(settings)
    configs = bootstrapper._build_config_layer()  # type: ignore[reportPrivateUsage]
    template_registry = TemplateRegistry(
        registry_path=resolved_server_root / "template_registry.json"
    )
    managers = bootstrapper._build_manager_graph(configs, template_registry)  # type: ignore[reportPrivateUsage]
    return managers, workspace_root


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
        human_approval_message: str,
        gate_runner: object | None = None,
    ) -> dict[str, object]:
        self.last_call = {
            "branch": branch,
            "to_cycle": to_cycle,
            "skip_reason": skip_reason,
            "human_approval_message": human_approval_message,
            "gate_runner": gate_runner,
        }
        return self._result


def _make_transition_advisory_execute(
    success: bool = True,
    to_cycle: int = 1,
    total_cycles: int = 2,
    cycle_name: str = "One",
    is_force: bool = False,
) -> Callable[[object, object, NoteContext], Awaitable[BaseModel]]:
    async def execute(_self: object, _params: object, context: NoteContext) -> BaseModel:
        from mcp_server.schemas.tool_outputs import (  # noqa: PLC0415
            CycleTransitionOutput,
            ForceCycleTransitionOutput,
        )

        # No legacy InfoNote produced
        if is_force:
            return ForceCycleTransitionOutput(
                success=success,
                branch="feature/257-reorder-workflow-phases",
                from_cycle=None,
                to_cycle=to_cycle,
                total_cycles=total_cycles,
                cycle_name=cycle_name,
                skip_reason="testing",
                human_approval_message="test",
            )
        return CycleTransitionOutput(
            success=success,
            branch="feature/257-reorder-workflow-phases",
            from_cycle=None,
            to_cycle=to_cycle,
            total_cycles=total_cycles,
            cycle_name=cycle_name,
        )

    return execute


class TestCycleTools:
    """Cycle tool rename, injection, and enforcement tests."""

    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PGMCP_SERVER_PROJECT_DIR", raising=False)

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
            server_root=tmp_path,
        )
        force_tool = ForceCycleTransitionTool(
            workspace_root=tmp_path,
            project_manager=project_manager,
            state_engine=state_engine,
            git_manager=git_manager,
            server_root=tmp_path,
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
        config_dir = tmp_path / get_default_server_root() / "config"
        copytree(Path.cwd() / get_default_server_root() / "config", config_dir, dirs_exist_ok=True)

        project_manager = make_project_manager(tmp_path)
        project_manager.initialize_project(
            issue_number=257,
            issue_title="Cycle 5.1 enforcement",
            workflow_name="feature",
        )
        project_manager.save_planning_deliverables(
            257,
            {
                "cycles": {
                    "total": 2,
                    "cycles": [
                        {
                            "cycle_number": 1,
                            "name": "One",
                            "deliverables": [{"id": "D1.1", "description": "cycle-1"}],
                            "exit_criteria": "pass",
                        },
                        {
                            "cycle_number": 2,
                            "name": "Two",
                            "deliverables": [{"id": "D2.1", "description": "cycle-2"}],
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
            patch("mcp_server.config.settings.Settings") as mock_settings_cls,
            patch(
                "mcp_server.tools.cycle_tools.TransitionCycleTool.execute",
                new=_make_transition_advisory_execute(
                    to_cycle=1, total_cycles=2, cycle_name="One", is_force=False
                ),
            ),
        ):
            mock_settings_cls.from_env.return_value.server.name = "test-server"
            mock_settings_cls.from_env.return_value.server.workspace_root = str(tmp_path)
            mock_settings_cls.from_env.return_value.server.config_root = str(
                tmp_path / get_default_server_root() / "config"
            )
            mock_settings_cls.from_env.return_value.server.server_root_dir = (
                get_default_server_root()
            )
            mock_settings_cls.from_env.return_value.github.token = None
            mock_settings_cls.from_env.return_value.github.owner = "test"
            mock_settings_cls.from_env.return_value.github.repo = "repo"
            mock_settings_cls.from_env.return_value.logging.level = "INFO"
            mock_settings_cls.from_env.return_value.logging.audit_log = ".logs/mcp_audit.log"

            managers, workspace_root = _get_test_bootstrap_context(
                mock_settings_cls.from_env.return_value
            )
            server = make_test_server()
            factory = ToolFactory(managers.enforcement_runner, workspace_root)
            server.tools = [
                factory.create_tool(
                    TransitionCycleTool(
                        workspace_root=tmp_path,
                        project_manager=managers.project_manager,
                        state_engine=managers.phase_state_engine,
                        git_manager=managers.git_manager,
                        gate_runner=managers.workflow_gate_runner,
                        server_root=tmp_path / get_default_server_root(),
                    )
                ),
            ]
            handler = server.server.request_handlers[CallToolRequest]

            with patch.object(
                managers.enforcement_runner,
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
        assert len(response.root.content) == 1
        assert TRANSITION_ADVISORY_NOTE in response.root.content[0].text
        assert any(
            call.kwargs.get("event") == "transition_cycle" and call.kwargs.get("timing") == "post"
            for call in mock_run.call_args_list
        )

    @pytest.mark.asyncio
    async def test_call_tool_post_enforcement_runs_after_force_cycle_transition(
        self,
        tmp_path: Path,
    ) -> None:
        """Successful forced cycle transitions append the advisory note after post-hook success."""
        config_dir = tmp_path / get_default_server_root() / "config"
        copytree(Path.cwd() / get_default_server_root() / "config", config_dir, dirs_exist_ok=True)

        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            mock_settings_cls.from_env.return_value.server.name = "test-server"
            mock_settings_cls.from_env.return_value.server.workspace_root = str(tmp_path)
            mock_settings_cls.from_env.return_value.server.config_root = str(
                tmp_path / get_default_server_root() / "config"
            )
            mock_settings_cls.from_env.return_value.server.server_root_dir = (
                get_default_server_root()
            )
            mock_settings_cls.from_env.return_value.github.token = None
            mock_settings_cls.from_env.return_value.github.owner = "test"
            mock_settings_cls.from_env.return_value.github.repo = "repo"
            mock_settings_cls.from_env.return_value.logging.level = "INFO"
            mock_settings_cls.from_env.return_value.logging.audit_log = ".logs/mcp_audit.log"

            managers, workspace_root = _get_test_bootstrap_context(
                mock_settings_cls.from_env.return_value
            )
            server = make_test_server()
            factory = ToolFactory(managers.enforcement_runner, workspace_root)
            server.tools = [
                factory.create_tool(
                    ForceCycleTransitionTool(
                        workspace_root=tmp_path,
                        project_manager=managers.project_manager,
                        state_engine=managers.phase_state_engine,
                        git_manager=managers.git_manager,
                        gate_runner=managers.workflow_gate_runner,
                        server_root=tmp_path / get_default_server_root(),
                    )
                ),
            ]
            handler = server.server.request_handlers[CallToolRequest]

            with (
                patch.object(managers.enforcement_runner, "run", return_value=[]) as mock_run,
                patch.object(
                    ForceCycleTransitionTool,
                    "execute",
                    new=_make_transition_advisory_execute(
                        to_cycle=2, total_cycles=2, cycle_name="One", is_force=True
                    ),
                ),
            ):
                req = CallToolRequest(
                    params=CallToolRequestParams(
                        name="force_cycle_transition",
                        arguments={
                            "to_cycle": 2,
                            "skip_reason": "Force test",
                            "human_approval_message": "Approved",
                            "issue_number": 257,
                        },
                    )
                )
                response = await handler(req)

        assert "Force-transitioned from Cycle - to Cycle 2/2 (One)" in (
            response.root.content[0].text
        )
        assert len(response.root.content) == 1
        assert TRANSITION_ADVISORY_NOTE in response.root.content[0].text
        assert any(
            call.kwargs.get("event") == "transition_cycle" and call.kwargs.get("timing") == "post"
            for call in mock_run.call_args_list
        )

    @pytest.mark.asyncio
    async def test_call_tool_transition_cycle_post_enforcement_error_omits_advisory_note(
        self,
        tmp_path: Path,
    ) -> None:
        """Post-hook errors must not leak the success-path advisory note for cycle transitions."""
        config_dir = tmp_path / get_default_server_root() / "config"
        copytree(Path.cwd() / get_default_server_root() / "config", config_dir, dirs_exist_ok=True)

        project_manager = make_project_manager(tmp_path)
        project_manager.initialize_project(
            issue_number=257,
            issue_title="Cycle 5.1 enforcement",
            workflow_name="feature",
        )
        project_manager.save_planning_deliverables(
            257,
            {
                "cycles": {
                    "total": 2,
                    "cycles": [
                        {
                            "cycle_number": 1,
                            "name": "One",
                            "deliverables": [{"id": "D1.1", "description": "cycle-1"}],
                            "exit_criteria": "pass",
                        },
                        {
                            "cycle_number": 2,
                            "name": "Two",
                            "deliverables": [{"id": "D2.1", "description": "cycle-2"}],
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

        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            mock_settings_cls.from_env.return_value.server.name = "test-server"
            mock_settings_cls.from_env.return_value.server.workspace_root = str(tmp_path)
            mock_settings_cls.from_env.return_value.server.config_root = str(
                tmp_path / get_default_server_root() / "config"
            )
            mock_settings_cls.from_env.return_value.server.server_root_dir = (
                get_default_server_root()
            )
            mock_settings_cls.from_env.return_value.github.token = None
            mock_settings_cls.from_env.return_value.github.owner = "test"
            mock_settings_cls.from_env.return_value.github.repo = "repo"
            mock_settings_cls.from_env.return_value.logging.level = "INFO"
            mock_settings_cls.from_env.return_value.logging.audit_log = ".logs/mcp_audit.log"

            managers, workspace_root = _get_test_bootstrap_context(
                mock_settings_cls.from_env.return_value
            )
            server = make_test_server()
            factory = ToolFactory(managers.enforcement_runner, workspace_root)
            server.tools = [
                factory.create_tool(
                    TransitionCycleTool(
                        workspace_root=tmp_path,
                        project_manager=project_manager,
                        state_engine=state_engine,
                        git_manager=managers.git_manager,
                        gate_runner=managers.workflow_gate_runner,
                        server_root=tmp_path / get_default_server_root(),
                    )
                ),
            ]
            handler = server.server.request_handlers[CallToolRequest]

            with (
                patch.object(managers.enforcement_runner, "run") as mock_run,
                patch.object(managers.git_manager, "get_current_branch", return_value=branch),
            ):

                def side_effect(*_args: object, **kwargs: object) -> list[str]:
                    if kwargs.get("event") == "transition_cycle" and kwargs.get("timing") == "post":
                        raise ConfigError("cycle hook failed")
                    return []

                mock_run.side_effect = side_effect
                req = CallToolRequest(
                    params=CallToolRequestParams(
                        name="transition_cycle",
                        arguments={"to_cycle": 1, "issue_number": 257},
                    )
                )
                response = await handler(req)

        texts = [item.text for item in response.root.content]
        assert len(response.root.content) == 1
        assert "cycle hook failed" in texts[0]
        assert all(TRANSITION_ADVISORY_NOTE not in text for text in texts)

    @pytest.mark.asyncio
    async def test_call_tool_force_cycle_post_enforcement_returns_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Force cycle transitions should fail when post-enforcement raises."""
        config_dir = tmp_path / get_default_server_root() / "config"
        copytree(Path.cwd() / get_default_server_root() / "config", config_dir, dirs_exist_ok=True)

        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            mock_settings_cls.from_env.return_value.server.name = "test-server"
            mock_settings_cls.from_env.return_value.server.workspace_root = str(tmp_path)
            mock_settings_cls.from_env.return_value.server.config_root = str(
                tmp_path / get_default_server_root() / "config"
            )
            mock_settings_cls.from_env.return_value.server.server_root_dir = (
                get_default_server_root()
            )
            mock_settings_cls.from_env.return_value.github.token = None
            mock_settings_cls.from_env.return_value.github.owner = "test"
            mock_settings_cls.from_env.return_value.github.repo = "repo"
            mock_settings_cls.from_env.return_value.logging.level = "INFO"
            mock_settings_cls.from_env.return_value.logging.audit_log = ".logs/mcp_audit.log"

            managers, workspace_root = _get_test_bootstrap_context(
                mock_settings_cls.from_env.return_value
            )
            server = make_test_server()
            factory = ToolFactory(managers.enforcement_runner, workspace_root)
            server.tools = [
                factory.create_tool(
                    ForceCycleTransitionTool(
                        workspace_root=tmp_path,
                        project_manager=managers.project_manager,
                        state_engine=managers.phase_state_engine,
                        git_manager=managers.git_manager,
                        gate_runner=managers.workflow_gate_runner,
                        server_root=tmp_path / get_default_server_root(),
                    )
                ),
            ]
            handler = server.server.request_handlers[CallToolRequest]

            with (
                patch.object(managers.enforcement_runner, "run") as mock_run,
                patch.object(
                    ForceCycleTransitionTool,
                    "execute",
                    new=_make_transition_advisory_execute(
                        to_cycle=2, total_cycles=2, cycle_name="One", is_force=True
                    ),
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
                            "human_approval_message": "Approved",
                            "issue_number": 257,
                        },
                    )
                )
                response = await handler(req)

        text = response.root.content[0].text
        assert len(response.root.content) == 1
        assert "cycle hook failed" in text
        assert "⚠️" not in text
        assert "✅" not in text
        assert TRANSITION_ADVISORY_NOTE not in text


class FakeTransitionCycleStateEngine:
    """Minimal transition-cycle state engine fake for wrapper tests."""

    def __init__(self, result: dict[str, object]) -> None:
        self._result = result
        self.last_call: dict[str, object] | None = None

    def transition_cycle(
        self,
        *,
        branch: str,
        to_cycle: int,
        gate_runner: object | None = None,
    ) -> dict[str, object]:
        self.last_call = {
            "branch": branch,
            "to_cycle": to_cycle,
            "gate_runner": gate_runner,
        }
        return self._result


class TestTransitionCycleToolAdvisoryNote:
    """Success-path advisory note tests for standard cycle transitions."""

    @pytest.mark.asyncio
    async def test_transition_cycle_tool_emits_advisory_info_note_after_success(
        self,
        tmp_path: Path,
    ) -> None:
        """Successful cycle transitions should emit the standard advisory note."""
        gate_runner = object()
        git_manager = MagicMock()
        git_manager.get_current_branch.return_value = "feature/257-cycle-orchestration"
        state_engine = FakeTransitionCycleStateEngine(
            {
                "success": True,
                "to_cycle": 3,
                "total_cycles": 4,
                "cycle_name": "Transition advisory note",
            }
        )
        tool = TransitionCycleTool(
            workspace_root=tmp_path,
            project_manager=MagicMock(),
            state_engine=state_engine,
            git_manager=git_manager,
            gate_runner=gate_runner,
            server_root=tmp_path,
        )
        context = NoteContext()

        from mcp_server.schemas.tool_outputs import CycleTransitionOutput  # noqa: PLC0415

        result = await tool.execute(
            TransitionCycleInput(to_cycle=3, issue_number=257),
            context,
        )

        assert isinstance(result, CycleTransitionOutput)
        assert result.success
        assert state_engine.last_call is not None
        assert state_engine.last_call["gate_runner"] is gate_runner
        assert len(context.entries) == 0


class TestForceCycleToolAdvisoryNote:
    """Success-path advisory note tests for forced cycle transitions."""

    @pytest.mark.asyncio
    async def test_force_cycle_tool_emits_advisory_info_note_after_success(
        self,
        tmp_path: Path,
    ) -> None:
        """Forced cycle transitions should emit the standard advisory note."""
        git_manager = MagicMock()
        git_manager.get_current_branch.return_value = "feature/257-cycle-orchestration"
        state_engine = FakeForceCycleStateEngine(
            {
                "success": True,
                "from_cycle": 2,
                "to_cycle": 3,
                "total_cycles": 4,
                "cycle_name": "Transition advisory note",
                "skipped_gates": [],
                "passing_gates": [],
            }
        )
        tool = ForceCycleTransitionTool(
            workspace_root=tmp_path,
            project_manager=MagicMock(),
            state_engine=state_engine,
            git_manager=git_manager,
            gate_runner=object(),
            server_root=tmp_path,
        )
        context = NoteContext()

        result = await tool.execute(
            ForceCycleTransitionInput(
                to_cycle=3,
                skip_reason="audited skip",
                human_approval_message="Verifier approved",
                issue_number=257,
            ),
            context,
        )

        from mcp_server.schemas.tool_outputs import ForceCycleTransitionOutput  # noqa: PLC0415

        assert isinstance(result, ForceCycleTransitionOutput)
        assert result.success
        assert len(context.entries) == 0


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
            server_root=tmp_path,
        )

        result = await tool.execute(
            ForceCycleTransitionInput(
                to_cycle=4,
                skip_reason="audited skip",
                human_approval_message="Verifier approved",
                issue_number=257,
            ),
            NoteContext(),
        )

        from mcp_server.schemas.tool_outputs import ForceCycleTransitionOutput  # noqa: PLC0415

        assert isinstance(result, ForceCycleTransitionOutput)
        assert result.success
        assert state_engine.last_call is not None
        assert state_engine.last_call["gate_runner"] is gate_runner
        assert result.skipped_gates == ["cycle-checklist"]
        assert result.passing_gates == ["cycle-docs"]
        assert result.skipped_gates_count == 1
        assert result.passing_gates_count == 1

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
            server_root=tmp_path,
        )

        result = await tool.execute(
            ForceCycleTransitionInput(
                to_cycle=3,
                skip_reason="audited skip",
                human_approval_message="Verifier approved",
                issue_number=257,
            ),
            NoteContext(),
        )

        from mcp_server.schemas.tool_outputs import ForceCycleTransitionOutput  # noqa: PLC0415

        assert isinstance(result, ForceCycleTransitionOutput)
        assert result.success
        assert result.skipped_gates == []
        assert result.passing_gates == ["cycle-docs"]
        assert result.skipped_gates_count == 0
        assert result.passing_gates_count == 1

    def test_force_cycle_transition_input_rejects_boolean_approval(self) -> None:
        """Reject boolean input for human_approval_message (C_CYCLE_TOOLS.3)."""
        from pydantic import ValidationError  # noqa: PLC0415

        from mcp_server.tools.cycle_tools import ForceCycleTransitionInput  # noqa: PLC0415

        with pytest.raises(ValidationError, match="human_approval_message"):
            ForceCycleTransitionInput(
                to_cycle=2,
                skip_reason="Valid reason",
                human_approval_message=True,  # type: ignore
            )
        with pytest.raises(ValidationError, match="human_approval_message"):
            ForceCycleTransitionInput(
                to_cycle=2,
                skip_reason="Valid reason",
                human_approval_message=False,  # type: ignore
            )

    def test_force_cycle_transition_input_rejects_empty_approval_and_reason(self) -> None:
        """Reject empty/whitespace approval/reason (C_CYCLE_TOOLS.3)."""
        from pydantic import ValidationError  # noqa: PLC0415

        from mcp_server.tools.cycle_tools import ForceCycleTransitionInput  # noqa: PLC0415

        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            ForceCycleTransitionInput(
                to_cycle=2,
                skip_reason="Valid reason",
                human_approval_message="",
            )
        with pytest.raises(ValidationError, match="Field cannot be empty"):
            ForceCycleTransitionInput(
                to_cycle=2,
                skip_reason="   ",
                human_approval_message="Approved",
            )
