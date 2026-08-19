"""RED tests for Cycle 2 of issue #260: state_root injection.

These tests verify that all production code accepts an injected state_root
and does NOT compute workspace_root / get_default_server_root() internally.

TDD: These tests FAIL before the GREEN implementation.
"""

from __future__ import annotations

import inspect
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.config.loader import normalize_config_root
from mcp_server.core.interfaces import IStateReader
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.managers.enforcement_runner import (
    EnforcementConfig,
    EnforcementRunner,
)
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.scaffolding.template_registry import TemplateRegistry
from mcp_server.tools.admin_tools import (
    RestartServerTool,
)
from mcp_server.tools.cycle_tools import TransitionCycleTool
from mcp_server.tools.git_tools import build_phase_guard
from tests.mcp_server.test_support import get_default_server_root

# ---------------------------------------------------------------------------
# F1 / normalize_config_root — dir-name-agnostic
# ---------------------------------------------------------------------------


class TestNormalizeConfigRootPhaseGate:
    """normalize_config_root must accept .pgmcp/ as well as .pgmcp/."""

    def test_accepts_phase_gate_config_dir(self, tmp_path: Path) -> None:
        """normalize_config_root('/ws/.pgmcp/config') → same path."""
        config_dir = tmp_path / get_default_server_root() / "config"
        config_dir.mkdir(parents=True)
        result = normalize_config_root(config_dir)
        assert result == config_dir.resolve()

    def test_accepts_phase_gate_state_root(self, tmp_path: Path) -> None:
        """normalize_config_root is a pure resolver after C3 — returns resolved path as-is."""
        state_root = tmp_path / get_default_server_root()
        config_dir = state_root / "config"
        config_dir.mkdir(parents=True)
        result = normalize_config_root(state_root)
        assert result == state_root.resolve()

    def test_arbitrary_dir_name_still_works(self, tmp_path: Path) -> None:
        """Backward compat: normalize_config_root accepts any hidden dir name."""
        config_dir = tmp_path / ".legacy" / "config"
        config_dir.mkdir(parents=True)
        result = normalize_config_root(config_dir)
        assert result == config_dir.resolve()

    def test_state_root_parent_gives_back_state_root(self, tmp_path: Path) -> None:
        """config_root.parent == state_root for any hidden dir name."""
        for state_dir_name in (".legacy", get_default_server_root(), ".myapp"):
            state_root = tmp_path / state_dir_name
            config_dir = state_root / "config"
            config_dir.mkdir(parents=True)
            result = normalize_config_root(config_dir)
            assert result.parent == state_root.resolve(), (
                f"For {state_dir_name}: expected parent {state_root.resolve()}, got {result.parent}"
            )
            # Cleanup for next iteration
            shutil.rmtree(state_root)


# ---------------------------------------------------------------------------
# F1 / PhaseStateEngine — accepts state_root
# ---------------------------------------------------------------------------


class TestPhaseStateEngineStateRoot:
    """PhaseStateEngine must use injected state_root for state.json path."""

    def _make_engine(self, state_root: Path, workspace_root: Path) -> PhaseStateEngine:
        return PhaseStateEngine(
            workspace_root=workspace_root,
            server_root=state_root,
            project_manager=MagicMock(),
            git_config=MagicMock(),
            contracts_config=MagicMock(),
            state_repository=MagicMock(),
            scope_decoder=MagicMock(),
            workflow_gate_runner=MagicMock(),
            state_reconstructor=MagicMock(),
            workflow_state_mutator=MagicMock(),
        )

    def test_state_file_uses_injected_state_root(self, tmp_path: Path) -> None:
        """When state_root is provided, state_path = state_root / 'state.json'."""
        state_root = tmp_path / get_default_server_root()
        workspace_root = tmp_path / "workspace"

        engine = self._make_engine(state_root, workspace_root)

        assert engine.state_path == state_root / "state.json"

    def test_state_file_is_not_workspace_root_phase_gate(self, tmp_path: Path) -> None:
        """state_path must NOT be derived from workspace_root / get_default_server_root()."""
        state_root = tmp_path / ".custom-state"
        workspace_root = tmp_path / "workspace"

        engine = self._make_engine(state_root, workspace_root)

        assert get_default_server_root() not in str(engine.state_path)

    def test_state_path_uses_injected_state_root(self, tmp_path: Path) -> None:
        """C6 RED: state_path (not state_file) must equal state_root / 'state.json'."""
        state_root = tmp_path / get_default_server_root()
        workspace_root = tmp_path / "workspace"

        engine = self._make_engine(state_root, workspace_root)

        assert engine.state_path == state_root / "state.json"

    def test_state_path_is_not_workspace_root_phase_gate(self, tmp_path: Path) -> None:
        """C6 RED: state_path must NOT be derived from workspace_root /
        get_default_server_root()."""
        state_root = tmp_path / ".custom-state"
        workspace_root = tmp_path / "workspace"

        engine = self._make_engine(state_root, workspace_root)

        assert get_default_server_root() not in str(engine.state_path)


# ---------------------------------------------------------------------------
# F1 / ProjectManager — accepts state_root
# ---------------------------------------------------------------------------


class TestProjectManagerStateRoot:
    """ProjectManager must use injected state_root for deliverables.json path."""

    def _make_manager(self, state_root: Path, workspace_root: Path) -> ProjectManager:
        return ProjectManager(
            workspace_root=workspace_root,
            server_root=state_root,
            contracts_config=MagicMock(),
            workflow_status_resolver=MagicMock(),
        )

    def test_deliverables_file_uses_injected_state_root(self, tmp_path: Path) -> None:
        state_root = tmp_path / get_default_server_root()
        workspace_root = tmp_path / "workspace"

        manager = self._make_manager(state_root, workspace_root)

        assert manager.deliverables_file == state_root / "deliverables.json"

    def test_deliverables_file_is_not_workspace_root_phase_gate(self, tmp_path: Path) -> None:
        state_root = tmp_path / ".custom-state"
        workspace_root = tmp_path / "workspace"

        manager = self._make_manager(state_root, workspace_root)

        assert get_default_server_root() not in str(manager.deliverables_file)


# ---------------------------------------------------------------------------
# F1 / EnforcementRunner — accepts state_root
# ---------------------------------------------------------------------------


class TestEnforcementRunnerStateRoot:
    """EnforcementRunner must accept server_root injection."""

    def test_enforcement_runner_init_accepts_state_root(self, tmp_path: Path) -> None:
        """EnforcementRunner must accept server_root kwarg (was state_root)."""
        state_root = tmp_path / get_default_server_root()
        runner = EnforcementRunner(
            workspace_root=tmp_path,
            server_root=state_root,
            git_config=MagicMock(),
            config=MagicMock(),
            state_reader=MagicMock(spec=IStateReader),
        )
        assert runner.server_root == state_root


# ---------------------------------------------------------------------------
# F1 / build_phase_guard — accepts state_root
# ---------------------------------------------------------------------------


class TestBuildPhaseGuard:
    """build_phase_guard must use injected state and contracts, not direct file reads."""

    def test_reads_state_via_injected_state_reader(self) -> None:
        state_reader = MagicMock()
        state_reader.load.return_value = MagicMock(
            branch="feature/42-test",
            workflow_name="bug",
            current_phase="implementation",
            current_cycle=2,
        )
        phase_contract_resolver = MagicMock()
        phase_contract_resolver.is_cycle_based_phase.return_value = True

        guard = build_phase_guard(
            state_reader=state_reader,
            phase_contract_resolver=phase_contract_resolver,
        )

        guard("feature/42-test", "implementation", 2)

        state_reader.load.assert_called_once_with("feature/42-test")
        phase_contract_resolver.is_cycle_based_phase.assert_called_once_with(
            "bug", "implementation"
        )

    def test_skips_cycle_mismatch_for_non_cycle_based_phase(self) -> None:
        state_reader = MagicMock()
        state_reader.load.return_value = MagicMock(
            branch="feature/42-test",
            workflow_name="bug",
            current_phase="planning",
            current_cycle=2,
        )
        phase_contract_resolver = MagicMock()
        phase_contract_resolver.is_cycle_based_phase.return_value = False

        guard = build_phase_guard(
            state_reader=state_reader,
            phase_contract_resolver=phase_contract_resolver,
        )

        guard("feature/42-test", "planning", 99)

        state_reader.load.assert_called_once_with("feature/42-test")
        phase_contract_resolver.is_cycle_based_phase.assert_called_once_with("bug", "planning")


# ---------------------------------------------------------------------------
# F1 / cycle_tools — uses state_root in _get_current_branch
# ---------------------------------------------------------------------------


class TestCycleToolsStateRoot:
    """Cycle tools must read state.json from state_root, not workspace_root/.pgmcp."""

    def test_transition_cycle_tool_reads_state_from_state_root(self, tmp_path: Path) -> None:
        """TransitionCycleTool._get_current_branch falls back to state_root/state.json."""
        state_root = tmp_path / get_default_server_root()
        state_root.mkdir()
        state_file = state_root / "state.json"
        state_file.write_text(json.dumps({"branch": "feature/99-test"}), encoding="utf-8")

        tool = TransitionCycleTool(
            workspace_root=tmp_path,
            server_root=state_root,
        )
        # Simulate git unavailable — should fall back to state.json
        with patch.object(tool, "_get_git_manager") as mock_git:
            mock_git.return_value.get_current_branch.side_effect = RuntimeError("no git")
            branch = tool._get_current_branch()  # pyright: ignore[reportPrivateUsage]
        assert branch == "feature/99-test"

    def test_transition_cycle_tool_does_not_read_from_workspace_phase_gate(
        self, tmp_path: Path
    ) -> None:
        state_root = tmp_path / ".custom-state"
        state_root.mkdir()
        # No state.json in state_root

        # Put misleading state.json in workspace/.pgmcp
        phase_gate_dir = tmp_path / get_default_server_root()
        phase_gate_dir.mkdir()
        (phase_gate_dir / "state.json").write_text(
            json.dumps({"branch": "feature/wrong-branch"}), encoding="utf-8"
        )

        tool = TransitionCycleTool(
            workspace_root=tmp_path,
            server_root=state_root,
        )
        with patch.object(tool, "_get_git_manager") as mock_git:
            mock_git.return_value.get_current_branch.return_value = "feature/correct-branch"
            branch = tool._get_current_branch()  # pyright: ignore[reportPrivateUsage]
        assert branch == "feature/correct-branch"


# ---------------------------------------------------------------------------
# F5 / admin_tools — workspace-aware restart marker
# ---------------------------------------------------------------------------


class TestAdminToolsRestartMarker:
    """RestartServerTool must resolve restart marker relative to injected server_root."""

    def test_uses_injected_server_root(self, tmp_path: Path) -> None:
        """Marker path must come from constructor-injected server_root, not env vars."""
        server_root = tmp_path / get_default_server_root()
        tool = RestartServerTool(server_root=server_root)
        result = tool._get_restart_marker_path()  # pyright: ignore[reportPrivateUsage]
        assert str(server_root) in str(result)
        assert ".restart_marker" in result.name

    def test_does_not_use_cwd_dot_phase_gate(self, tmp_path: Path) -> None:
        """Marker path must not contain CWD-relative get_default_server_root()."""
        server_root = tmp_path / ".custom-state"
        tool = RestartServerTool(server_root=server_root)
        result = tool._get_restart_marker_path()  # pyright: ignore[reportPrivateUsage]
        assert get_default_server_root() not in str(result)

    def test_env_var_does_not_override_injected_server_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Even with MCP_WORKSPACE_ROOT set, injected server_root wins."""
        server_root = tmp_path / get_default_server_root()
        tool = RestartServerTool(server_root=server_root)
        monkeypatch.setenv("PGMCP_WORKSPACE_ROOT", str(tmp_path / "other"))
        monkeypatch.delenv("PGMCP_CONFIG_ROOT", raising=False)
        result = tool._get_restart_marker_path()  # pyright: ignore[reportPrivateUsage]
        assert result == server_root / ".restart_marker"


# ---------------------------------------------------------------------------
# F6 / artifact_manager — ephemeral temp uses workspace_root
# ---------------------------------------------------------------------------


class TestArtifactManagerEphemeralTemp:
    """ArtifactManager ephemeral temp dir must be workspace_root-relative."""

    def test_ephemeral_temp_uses_workspace_root(self, tmp_path: Path) -> None:
        """Path(f"{get_default_server_root()}/temp") must be replaced
        with self.server_root / 'temp'."""
        state_root = tmp_path / get_default_server_root()
        state_root.mkdir()
        (state_root / "template_registry.json").touch()

        manager = ArtifactManager(
            workspace_root=tmp_path,
            server_root=state_root,
            registry=MagicMock(),
        )

        # The internal server_root should be the injected one
        assert manager.server_root == state_root

    def test_template_registry_path_not_cwd_relative(self, tmp_path: Path) -> None:
        """template_registry path must be based on server_root, not CWD."""
        state_root = tmp_path / get_default_server_root()
        state_root.mkdir()
        registry_path = state_root / "template_registry.json"

        manager = ArtifactManager(
            workspace_root=tmp_path,
            server_root=state_root,
            registry=MagicMock(),
            template_registry=TemplateRegistry(registry_path=registry_path),
        )
        assert str(tmp_path) in str(manager.template_registry.registry_path)


# ---------------------------------------------------------------------------
# template_registry — default arg not .pgmcp-based
# ---------------------------------------------------------------------------


class TestTemplateRegistryDefaultArg:
    """TemplateRegistry default registry_path must not hardcode .pgmcp."""

    def test_default_registry_path_is_not_cwd_dot_phase_gate(self) -> None:
        """TemplateRegistry() without args: no hardcoded default path."""
        sig = inspect.signature(TemplateRegistry.__init__)
        default = sig.parameters["registry_path"].default

        # Default should be None (not a .pgmcp Path)
        expected_path = f"{get_default_server_root()}/template_registry.json"
        assert default is None or str(default) != expected_path, (
            f"Registry path should not be {expected_path}, got: {default}"
        )


# ===========================================================================
# C2 RED — TDD Cycle 2: no-fallback enforcement

# ---------------------------------------------------------------------------
# PhaseStateEngine — must raise when server_root absent
# ---------------------------------------------------------------------------


class TestPhaseStateEngineNoFallback:
    """PhaseStateEngine must raise when server_root is not provided."""

    def test_raises_when_server_root_is_none(self) -> None:
        """Constructing without server_root must raise — no silent .pgmcp fallback.

        RED: constructor currently has state_root: Path|None=None with
        effective_state_root = state_root or workspace_path / get_default_server_root().
        It succeeds silently instead of raising.
        """
        with pytest.raises((ValueError, TypeError)):
            PhaseStateEngine(
                workspace_root=Path("/some/workspace"),
                project_manager=MagicMock(),
                git_config=MagicMock(),
                contracts_config=MagicMock(),
                state_repository=MagicMock(),
                scope_decoder=MagicMock(),
                workflow_gate_runner=MagicMock(),
                state_reconstructor=MagicMock(),
                workflow_state_mutator=MagicMock(),
                # server_root omitted — must raise, not default to workspace/.pgmcp
            )


# ---------------------------------------------------------------------------
# ProjectManager — must raise when server_root absent
# ---------------------------------------------------------------------------


class TestProjectManagerNoFallback:
    """ProjectManager must raise when server_root is not provided."""

    def test_raises_when_server_root_is_none(self) -> None:
        """Constructing without server_root must raise — no silent .pgmcp fallback.

        RED: constructor currently has state_root: Path|None=None with
        effective_state_root = state_root or workspace_root / get_default_server_root().
        It succeeds silently instead of raising.
        """
        with pytest.raises((ValueError, TypeError)):
            ProjectManager(
                workspace_root=Path("/some/workspace"),
                contracts_config=MagicMock(),
                workflow_status_resolver=MagicMock(),
                # server_root omitted — must raise, not default to workspace/.pgmcp
            )


# ---------------------------------------------------------------------------
# EnforcementRunner — must raise when server_root absent
# ---------------------------------------------------------------------------


class TestEnforcementRunnerNoFallback:
    """EnforcementRunner must raise when server_root is not provided."""

    def test_raises_when_server_root_is_none(self) -> None:
        """Constructing without server_root must raise — no silent .pgmcp fallback.

        RED: constructor currently has state_root: Path|None=None with
        self.state_root = state_root or workspace_root / get_default_server_root().
        It succeeds silently instead of raising.
        """
        with pytest.raises((ValueError, TypeError)):
            EnforcementRunner(
                workspace_root=Path("/some/workspace"),
                config=EnforcementConfig(enforcement=[]),
                git_config=MagicMock(),
                # server_root omitted — must raise, not default to workspace/.pgmcp
            )


# ---------------------------------------------------------------------------
# _BaseTransitionTool / cycle tools — must raise when server_root absent
# ---------------------------------------------------------------------------


class TestBaseTransitionToolNoFallback:
    """_BaseTransitionTool subclasses must raise when server_root is not provided."""

    def test_transition_cycle_tool_raises_when_server_root_is_none(self) -> None:
        """TransitionCycleTool without server_root must raise.

        RED: _BaseTransitionTool has state_root: Path|None=None with
        self.state_root = state_root or workspace_root / get_default_server_root().
        Constructor succeeds silently.
        """
        with pytest.raises((ValueError, TypeError)):
            TransitionCycleTool(
                workspace_root=Path("/some/workspace"),
                # server_root omitted — must raise, not default to workspace/.pgmcp
            )


# ---------------------------------------------------------------------------
# RestartServerTool — must accept server_root injection
# ---------------------------------------------------------------------------


class TestAdminToolsServerRootInjection:
    """RestartServerTool must accept server_root and use it for the marker path."""

    def test_restart_tool_uses_injected_server_root(self, tmp_path: Path) -> None:
        """RestartServerTool(server_root=...) sets marker path from server_root.

        RED: RestartServerTool has no __init__ accepting server_root.
        Constructing with server_root= raises TypeError (unexpected kwarg).
        """
        server_root = tmp_path / get_default_server_root()
        tool = RestartServerTool(server_root=server_root)

        expected = server_root / ".restart_marker"
        result = tool._get_restart_marker_path()  # pyright: ignore[reportPrivateUsage]
        assert result == expected

    def test_marker_path_ignores_env_vars_when_server_root_injected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Injected server_root must win over any MCP_WORKSPACE_ROOT env var.

        RED: marker path currently comes from env-var lookup, not constructor injection.
        """
        server_root = tmp_path / get_default_server_root()
        tool = RestartServerTool(server_root=server_root)

        monkeypatch.setenv("PGMCP_WORKSPACE_ROOT", "/some/other/workspace")
        monkeypatch.delenv("PGMCP_CONFIG_ROOT", raising=False)

        result = tool._get_restart_marker_path()  # pyright: ignore[reportPrivateUsage]
        assert result == server_root / ".restart_marker"
        assert "/some/other/workspace" not in str(result)


# ---------------------------------------------------------------------------
# normalize_config_root — final fallback must not produce .pgmcp path
# ---------------------------------------------------------------------------


class TestNormalizeConfigRootNoPhaseGateFallback:
    """normalize_config_root must not hardcode .pgmcp in the final fallback branch."""

    def test_workspace_root_fallback_does_not_produce_phase_gate_path(self, tmp_path: Path) -> None:
        """When given a plain directory (not hidden, no config/ child), must not return .pgmcp.

        GREEN: raises FileNotFoundError (no silent .pgmcp fallback).
        Either raising or returning a non-.pgmcp path satisfies the contract.
        """
        # tmp_path is a plain directory (no leading '.', no config/ subdirectory)
        # This hits the final fallback branch of normalize_config_root
        try:
            result = normalize_config_root(tmp_path)
            # If no exception: result must not contain .pgmcp
            assert get_default_server_root() not in str(result), (
                f"normalize_config_root final fallback still hardcodes "
                f"get_default_server_root(): {result}"
            )
        except (FileNotFoundError, ValueError):
            # Raising is preferred — no .pgmcp path was produced
            pass


# ---------------------------------------------------------------------------
# TemplateRegistry — constructing with None must not silently use .pgmcp
# ---------------------------------------------------------------------------


class TestTemplateRegistryNoPhaseGateFallback:
    """TemplateRegistry with registry_path=None must raise, not silently use .pgmcp."""

    def test_none_registry_path_raises_or_no_phase_gate(self) -> None:
        """TemplateRegistry() without args: registry_path must not resolve to .pgmcp.

        RED: current __init__ body sets
            self.registry_path = Path(f"{get_default_server_root()}/template_registry.json")
        when registry_path is None. The instance attribute silently contains
        get_default_server_root().
        """
        with pytest.raises((ValueError, TypeError)):
            # Must raise when no explicit registry_path is provided
            TemplateRegistry()
