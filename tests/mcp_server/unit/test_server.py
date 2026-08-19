# pyright: reportMissingImports=false
"""Tests for MCP Server tool registration and dispatch hooks.

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.server, mcp.types
"""

import json
import logging
import os
import shutil
import subprocess
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams
from pydantic import BaseModel

from mcp_server.bootstrap import ServerBootstrapper, TemplateRegistry
from mcp_server.core.exceptions import ConfigError
from mcp_server.core.interfaces import ICoreTool
from mcp_server.core.operation_notes import NoteContext
from mcp_server.core.tool_factory import ToolFactory
from mcp_server.managers.state_repository import InMemoryStateRepository
from mcp_server.schemas.cache_publication import CachePublication
from mcp_server.schemas.tool_outputs import PhaseTransitionOutput
from mcp_server.server import MCPServer
from mcp_server.tools.git_tools import CreateBranchTool
from mcp_server.tools.phase_tools import (
    ForcePhaseTransitionTool,
    TransitionPhaseTool,
)
from mcp_server.tools.tool_result import ToolResult
from tests.mcp_server.test_support import (
    get_default_server_root,
    make_phase_state_engine,
    make_project_manager,
    make_test_server,
)

TRANSITION_ADVISORY_NOTE = (
    "🚀 REQUIRED NEXT STEP: Call get_work_context now before any other tool call "
    "to load the current phase context for this branch."
)


def _bootstrap_workspace_configs(workspace_root: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    shutil.copytree(
        repo_root / get_default_server_root(),
        workspace_root / get_default_server_root(),
        dirs_exist_ok=True,
    )
    deliverables_file = workspace_root / get_default_server_root() / "deliverables.json"
    if deliverables_file.exists():
        try:
            data = json.loads(deliverables_file.read_text(encoding="utf-8"))
            if "schema_version" not in data:
                payload = {"schema_version": "1.0.0", "projects": data.get("projects", data)}
                deliverables_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    state_file = workspace_root / get_default_server_root() / "state.json"
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            if "schema_version" not in data:
                data["schema_version"] = "1.0.0"
                state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass


def _patch_server_settings(
    mock: MagicMock,
    workspace_root: str | None = None,
    token: str | None = None,
) -> None:
    """Configure a Settings class mock for server tests."""
    from tests.mcp_server.test_support import RealSettings  # noqa: PLC0415

    resolved_workspace_root = workspace_root or str(Path(__file__).resolve().parents[3])
    server_root_dir = get_default_server_root()

    settings = RealSettings.from_env()
    settings.server.name = "test-server"
    settings.server.workspace_root = resolved_workspace_root
    settings.server.config_root = None
    settings.server.server_root_dir = server_root_dir
    settings.github.token = token
    settings.github.owner = "test"
    settings.github.repo = "repo"
    settings.logging.level = "INFO"
    settings.logging.audit_log = ".logs/mcp_audit.log"

    mock.return_value = settings
    mock.from_env.return_value = settings


def _get_test_bootstrap_context(settings: Any) -> tuple[Any, Path]:
    bootstrapper = ServerBootstrapper(settings)
    configs = bootstrapper._build_config_layer()  # type: ignore[reportPrivateUsage]
    workspace_root = Path(settings.server.workspace_root)
    server_root = workspace_root / settings.server.server_root_dir
    template_registry = TemplateRegistry(registry_path=server_root / "template_registry.json")
    managers = bootstrapper._build_manager_graph(configs, template_registry)  # type: ignore[reportPrivateUsage]
    return managers, workspace_root


def _write_phase_state(workspace_root: Path, current_phase: str) -> None:
    state_file = workspace_root / get_default_server_root() / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "branch": "refactor/283-ready-phase-enforcement",
                "workflow_name": "refactor",
                "current_phase": current_phase,
                "issue_number": 283,
            }
        ),
        encoding="utf-8",
    )


def _git_test_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GIT_PAGER", "cat")
    env.setdefault("PAGER", "cat")
    return env


def _run_git(workspace_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=workspace_root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
        env=_git_test_env(),
    )


def _track_branch_local_artifacts(workspace_root: Path) -> None:
    deliverables_file = workspace_root / get_default_server_root() / "deliverables.json"
    if not deliverables_file.exists():
        deliverables_file.write_text("{}\n", encoding="utf-8")

    _run_git(workspace_root, "init")
    _run_git(
        workspace_root,
        "add",
        f"{get_default_server_root()}/state.json",
        f"{get_default_server_root()}/deliverables.json",
    )


def _make_submit_pr_request() -> CallToolRequest:
    return CallToolRequest(
        params=CallToolRequestParams(
            name="submit_pr",
            arguments={
                "title": "Test PR",
                "body": "Test body",
                "head": "refactor/283-ready-phase-enforcement",
                "base": "main",
            },
        )
    )


def _make_transition_advisory_execute(
    _text: str,
) -> Callable[[object, object, NoteContext], Awaitable[PhaseTransitionOutput]]:
    async def execute(
        _self: object, _params: object, context: NoteContext
    ) -> PhaseTransitionOutput:
        # No legacy InfoNote produced
        return PhaseTransitionOutput(
            success=True,
            branch=getattr(_params, "branch", "feature/257-reorder-workflow-phases"),
            from_phase="research",
            to_phase=getattr(_params, "to_phase", "planning"),
            passing_gates=[],
            skipped_gates=[],
            passing_gates_count=0,
            skipped_gates_count=0,
        )

    return execute


class TestServerToolRegistration:
    """Tests for server tool registration."""

    def test_github_tools_always_registered(self) -> None:
        """GitHub tools should always be registered, even without token."""
        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls)

            server = make_test_server()
            tool_names = [t.name for t in server.tools]

            assert "create_issue" in tool_names
            assert "list_issues" in tool_names
            assert "get_issue" in tool_names
            assert "close_issue" in tool_names
            assert "get_pr" not in tool_names

    def test_github_tools_registered_with_token(self) -> None:
        """GitHub tools should be registered when token is configured."""
        with (
            patch("mcp_server.config.settings.Settings") as mock_settings_cls,
            patch("mcp_server.resources.github.GitHubManager") as mock_res_manager,
            patch("mcp_server.tools.pr_tools.GitHubManager") as mock_pr_manager,
            patch("mcp_server.tools.label_tools.GitHubManager") as mock_label_manager,
        ):
            _patch_server_settings(mock_settings_cls, token="test-token")

            mock_res_manager.return_value = MagicMock()
            mock_pr_manager.return_value = MagicMock()
            mock_label_manager.return_value = MagicMock()

            server = make_test_server()
            tool_names = [t.name for t in server.tools]

            assert "create_issue" in tool_names
            assert "list_issues" in tool_names
            assert "get_issue" in tool_names
            assert "close_issue" in tool_names
            assert "add_labels" in tool_names
            assert "get_pr" in tool_names

    @pytest.mark.asyncio
    async def test_call_tool_logging_has_call_id_and_duration(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """call_tool handler should log correlation id and duration."""

        class DummyTool(ICoreTool[BaseModel, ToolResult]):
            """Dummy tool for testing server call_tool logging."""

            @property
            def name(self) -> str:
                return "dummy_tool"

            @property
            def description(self) -> str:
                return "Dummy tool"

            @property
            def args_model(self) -> type[BaseModel] | None:
                return None

            async def execute(self, params: BaseModel | None, context: NoteContext) -> ToolResult:
                del params, context
                return ToolResult.text("ok")

        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls)
            managers, workspace_root = _get_test_bootstrap_context(
                mock_settings_cls.from_env.return_value
            )

            server = make_test_server()
            factory = ToolFactory(managers.enforcement_runner, workspace_root)
            server.tools = [factory.create_tool(DummyTool())]

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
        config_dir = tmp_path / get_default_server_root() / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "enforcement.yaml").write_text(
            """
            version: "1.0.0"
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

        _bootstrap_workspace_configs(tmp_path)

        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls, workspace_root=str(tmp_path))
            managers, workspace_root = _get_test_bootstrap_context(
                mock_settings_cls.from_env.return_value
            )

            server = make_test_server()
            manager = MagicMock()
            manager.git_config = managers.git_manager.git_config
            factory = ToolFactory(managers.enforcement_runner, workspace_root)
            server.tools = [factory.create_tool(CreateBranchTool(manager=manager))]
            handler = server.server.request_handlers[CallToolRequest]

            req = CallToolRequest(
                params=CallToolRequestParams(
                    name="create_branch",
                    arguments={
                        "issue_number": 123,
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
    async def test_call_tool_pre_enforcement_blocks_submit_pr_outside_ready_phase(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Dispatch pre-hook should return a phase error and never reach GitHub PR creation."""
        monkeypatch.delenv("PGMCP_SERVER_PROJECT_DIR", raising=False)
        _bootstrap_workspace_configs(tmp_path)
        _write_phase_state(tmp_path, "documentation")

        with (
            patch("mcp_server.config.settings.Settings") as mock_settings_cls,
            patch(
                "mcp_server.managers.enforcement_runner._get_current_git_branch",
                return_value="refactor/283-ready-phase-enforcement",
            ),
        ):
            _patch_server_settings(
                mock_settings_cls,
                workspace_root=str(tmp_path),
                token="test-token",
            )

            server = make_test_server()
            handler = server.server.request_handlers[CallToolRequest]

            with patch(
                "mcp_server.managers.github_manager.GitHubManager.create_pr",
                side_effect=AssertionError("create_pr should not be called"),
            ) as mock_create_pr:
                response = await handler(_make_submit_pr_request())

        text = "\n".join(c.text for c in response.root.content if hasattr(c, "text"))
        assert response.root.isError is True
        assert "requires phase 'ready'" in text
        assert "Current phase: 'documentation'" in text
        assert 'transition_phase(to_phase="ready")' in text
        mock_create_pr.assert_not_called()

    @pytest.mark.asyncio
    async def test_call_tool_post_enforcement_runs_after_transition(
        self,
        tmp_path: Path,
    ) -> None:
        """Dispatch post-hook should still run after a successful phase transition."""
        _bootstrap_workspace_configs(tmp_path)

        project_manager = make_project_manager(tmp_path)
        project_manager.initialize_project(
            issue_number=257,
            issue_title="Cycle 5 enforcement",
            workflow_name="feature",
        )
        state_engine = make_phase_state_engine(
            tmp_path,
            project_manager=project_manager,
            state_repository=InMemoryStateRepository(),
        )
        state_engine.initialize_branch(
            branch="feature/257-reorder-workflow-phases",
            issue_number=257,
            initial_phase="research",
        )

        research_doc = tmp_path / "docs" / "development" / "issue257" / "cycle5-research.md"
        research_doc.parent.mkdir(parents=True, exist_ok=True)
        research_doc.write_text("# Research\n", encoding="utf-8")

        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls, workspace_root=str(tmp_path))
            managers, workspace_root = _get_test_bootstrap_context(
                mock_settings_cls.from_env.return_value
            )

            server = make_test_server()
            factory = ToolFactory(managers.enforcement_runner, workspace_root)
            server.tools = [
                factory.create_tool(
                    TransitionPhaseTool(
                        workspace_root=tmp_path,
                        project_manager=project_manager,
                        state_engine=state_engine,
                        server_root=tmp_path / get_default_server_root(),
                        workphases_config=None,
                    )
                )
            ]
            handler = server.server.request_handlers[CallToolRequest]

            with (
                patch.object(managers.enforcement_runner, "run", return_value=[]) as mock_run,
                patch.object(
                    TransitionPhaseTool,
                    "execute",
                    new=_make_transition_advisory_execute("Successfully transitioned"),
                ),
            ):
                req = CallToolRequest(
                    params=CallToolRequestParams(
                        name="transition_phase",
                        arguments={
                            "branch": "feature/257-reorder-workflow-phases",
                            "to_phase": "planning",
                            "human_approval_message": "Move into planning",
                        },
                    )
                )
                response = await handler(req)

        assert "Transitioned phase to" in response.root.content[0].text
        assert len(response.root.content) == 1
        assert TRANSITION_ADVISORY_NOTE in response.root.content[0].text
        assert any(
            call.kwargs.get("event") == "transition_phase" and call.kwargs.get("timing") == "post"
            for call in mock_run.call_args_list
        )

    @pytest.mark.asyncio
    async def test_call_tool_post_enforcement_runs_after_force_phase_transition(
        self,
        tmp_path: Path,
    ) -> None:
        """Successful forced phase transitions append the advisory note after post-hook success."""
        _bootstrap_workspace_configs(tmp_path)

        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls, workspace_root=str(tmp_path))
            managers, workspace_root = _get_test_bootstrap_context(
                mock_settings_cls.from_env.return_value
            )

            server = make_test_server()
            factory = ToolFactory(managers.enforcement_runner, workspace_root)
            server.tools = [
                factory.create_tool(
                    ForcePhaseTransitionTool(
                        workspace_root=tmp_path,
                        project_manager=managers.project_manager,
                        state_engine=managers.phase_state_engine,
                        server_root=tmp_path / get_default_server_root(),
                        workphases_config=None,
                    )
                )
            ]
            handler = server.server.request_handlers[CallToolRequest]

            with (
                patch.object(managers.enforcement_runner, "run", return_value=[]) as mock_run,
                patch.object(
                    ForcePhaseTransitionTool,
                    "execute",
                    new=_make_transition_advisory_execute("✅ Forced phase transition"),
                ),
            ):
                req = CallToolRequest(
                    params=CallToolRequestParams(
                        name="force_phase_transition",
                        arguments={
                            "branch": "feature/257-reorder-workflow-phases",
                            "to_phase": "planning",
                            "skip_reason": "Force test",
                            "human_approval_message": "Approved",
                        },
                    )
                )
                response = await handler(req)

        assert "Transitioned phase to" in response.root.content[0].text
        assert len(response.root.content) == 1
        assert TRANSITION_ADVISORY_NOTE in response.root.content[0].text
        assert any(
            call.kwargs.get("event") == "transition_phase" and call.kwargs.get("timing") == "post"
            for call in mock_run.call_args_list
        )

    @pytest.mark.asyncio
    async def test_call_tool_transition_post_enforcement_error_omits_advisory_note(
        self,
        tmp_path: Path,
    ) -> None:
        """Post-hook errors must not leak the success-path advisory note."""
        _bootstrap_workspace_configs(tmp_path)

        project_manager = make_project_manager(tmp_path)
        project_manager.initialize_project(
            issue_number=257,
            issue_title="Cycle 5 enforcement",
            workflow_name="feature",
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
            initial_phase="research",
        )

        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls, workspace_root=str(tmp_path))
            managers, workspace_root = _get_test_bootstrap_context(
                mock_settings_cls.from_env.return_value
            )

            server = make_test_server()
            factory = ToolFactory(managers.enforcement_runner, workspace_root)
            server.tools = [
                factory.create_tool(
                    TransitionPhaseTool(
                        workspace_root=tmp_path,
                        project_manager=project_manager,
                        state_engine=state_engine,
                        server_root=tmp_path / get_default_server_root(),
                        workphases_config=None,
                    )
                )
            ]
            handler = server.server.request_handlers[CallToolRequest]

            with patch.object(managers.enforcement_runner, "run") as mock_run:

                def side_effect(*_args: object, **kwargs: object) -> list[str]:
                    if kwargs.get("event") == "transition_phase" and kwargs.get("timing") == "post":
                        raise ConfigError("post hook failed")
                    return []

                mock_run.side_effect = side_effect
                req = CallToolRequest(
                    params=CallToolRequestParams(
                        name="transition_phase",
                        arguments={
                            "branch": branch,
                            "to_phase": "design",
                            "human_approval_message": "Move into design",
                        },
                    )
                )
                response = await handler(req)

        texts = [item.text for item in response.root.content]
        assert len(response.root.content) == 1
        assert "post hook failed" in texts[0]
        assert all(TRANSITION_ADVISORY_NOTE not in text for text in texts)

    @pytest.mark.asyncio
    async def test_call_tool_force_phase_post_enforcement_returns_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Force phase transitions should fail when post-enforcement raises."""
        _bootstrap_workspace_configs(tmp_path)

        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls, workspace_root=str(tmp_path))
            managers, workspace_root = _get_test_bootstrap_context(
                mock_settings_cls.from_env.return_value
            )

            server = make_test_server()
            factory = ToolFactory(managers.enforcement_runner, workspace_root)
            server.tools = [
                factory.create_tool(
                    ForcePhaseTransitionTool(
                        workspace_root=tmp_path,
                        project_manager=managers.project_manager,
                        state_engine=managers.phase_state_engine,
                        server_root=tmp_path / get_default_server_root(),
                        workphases_config=None,
                    )
                )
            ]
            handler = server.server.request_handlers[CallToolRequest]

            with (
                patch.object(managers.enforcement_runner, "run") as mock_run,
                patch.object(
                    ForcePhaseTransitionTool,
                    "execute",
                    new=_make_transition_advisory_execute("✅ Forced phase transition"),
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
                            "human_approval_message": "Approved",
                        },
                    )
                )
                response = await handler(req)

        text = response.root.content[0].text
        assert len(response.root.content) == 1
        assert "post hook failed" in text
        assert "⚠️" not in text
        assert "✅" not in text
        assert TRANSITION_ADVISORY_NOTE not in text

    @pytest.mark.asyncio
    async def test_run_uses_injected_settings_without_extra_from_env(self) -> None:
        """run() should reuse the injected settings object from the composition root."""

        @asynccontextmanager
        async def fake_stdio_server(
            *_args: object, **_kwargs: object
        ) -> AsyncGenerator[tuple[MagicMock, MagicMock]]:
            yield MagicMock(), MagicMock()

        with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
            _patch_server_settings(mock_settings_cls)
            injected_settings = mock_settings_cls.from_env.return_value
            server = make_test_server(settings=injected_settings)
            mock_settings_cls.from_env.reset_mock()

            with (
                patch("mcp_server.server.TextIOWrapper", return_value=MagicMock()),
                patch("mcp_server.server.stdio_server", side_effect=fake_stdio_server),
                patch("mcp_server.server.anyio.wrap_file", return_value=MagicMock()),
                patch.object(server.server, "run", new=AsyncMock()) as mock_run,
            ):
                await server.run()

        mock_settings_cls.from_env.assert_not_called()
        mock_run.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_call_tool_cache_error_intercept() -> None:
    """If cache write fails (returns None), the presenter should be called with run_id=None
    and format the fallback message correctly without crashing.
    """
    from pydantic import BaseModel  # noqa: PLC0415

    from mcp_server.presenters.text_presenter import TextPresenter  # noqa: PLC0415
    from mcp_server.state.response_cache import ResponseCacheManager  # noqa: PLC0415

    class DummyTool(ICoreTool[BaseModel, ToolResult]):
        @property
        def name(self) -> str:
            return "dummy_tool"

        @property
        def description(self) -> str:
            return "Dummy Tool"

        @property
        def args_model(self) -> type[BaseModel] | None:
            return None

        async def execute(self, params: BaseModel, context: NoteContext) -> ToolResult:
            return ToolResult.text("success")

    with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
        _patch_server_settings(mock_settings_cls)

        config_data = {
            "global": {
                "default_failure_template": "Failure: {error_message}",
                "emojis": {"failure": "❌"},
            },
            "tools": {},
        }
        presenter = TextPresenter(config_data=config_data)

        managers, workspace_root = _get_test_bootstrap_context(
            mock_settings_cls.from_env.return_value
        )
        server = make_test_server()
        server.presenter = presenter
        tool = DummyTool()
        cache_manager = ResponseCacheManager()
        server.response_cache = cache_manager
        server.response_cache_manager = cache_manager
        factory = ToolFactory(managers.enforcement_runner, workspace_root)
        server.tools = [factory.create_tool(tool)]

        with patch.object(
            cache_manager,
            "put",
            return_value=CachePublication(success=False, error_code="write_failed"),
        ) as mock_put:
            handler = server.server.request_handlers[CallToolRequest]

            req = CallToolRequest(
                params=CallToolRequestParams(
                    name="dummy_tool",
                    arguments={},
                )
            )

            with patch.object(presenter, "present", wraps=presenter.present) as mock_present:
                response = await handler(req)

        content = response.root.content
        assert len(content) == 1
        text = getattr(content[0], "text", "")
        # Should return direct text block formatted by presenter
        assert "success" in text
        # Since cache_pub.run_id is None, there should be NO cache URI in output
        assert "pgmcp://cache/runs/" not in text

        # Verify presenter was called with cache_pub
        mock_present.assert_called_once()
        _, kwargs = mock_present.call_args
        assert kwargs.get("cache_pub") is not None
        assert kwargs.get("cache_pub").success is False
        mock_put.assert_called_once()


def test_server_constructor_clean() -> None:
    """Verify that MCPServer can be constructed without configs or managers."""

    with patch("mcp_server.config.settings.Settings") as mock_settings_cls:
        _patch_server_settings(mock_settings_cls)
        settings = mock_settings_cls.from_env.return_value
        server = MCPServer(
            settings=settings,
            tools=[],
            resources=[],
            presenter=None,
            publisher=None,
        )
        assert server is not None
