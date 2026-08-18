# tests/mcp_server/integration/test_context_loaded_enforcement.py
# template=unit_test version=cycle8-green created=2026-01-01T00:00Z updated=
"""Integration tests for context-loaded enforcement gate (issue #268 C8).

Verifies that:
  1. EnforcementRunner blocks branch-mutating tools when context is not loaded.
  2. EnforcementRunner allows tools after get_work_context has been called.
  3. force_phase_transition is exempt from the gate.
  4. force_cycle_transition is exempt from the gate.
  5. Bootstrap predicate: gate is inactive when state.json does not exist.
  6. GitCheckoutTool resets context-loaded flag after successful checkout.
  7. GitPullTool resets context-loaded flag when new commits are pulled.
  8. PhaseStateEngine.transition() resets context-loaded flag after phase transition.

@layer: Tests (Integration)
@dependencies: [pytest, pytest-asyncio, unittest.mock,
    mcp_server.config.loader,
    mcp_server.core.exceptions,
    mcp_server.core.interfaces,
    mcp_server.core.operation_notes,
    mcp_server.managers.enforcement_runner,
    mcp_server.managers.phase_state_engine,
    mcp_server.state.context_loaded_cache,
    mcp_server.tools.git_tools,
    mcp_server.tools.git_pull_tool,
    tests.mcp_server.test_support]
@responsibilities:
    - Verify check_context_loaded gate via live enforcement.yaml
    - Verify exempt_tools bypass for force_phase/cycle_transition
    - Verify bootstrap predicate suppresses gate before state.json exists
    - Verify GitCheckoutTool and GitPullTool reset context-loaded on execution
    - Verify PhaseStateEngine.transition() resets context-loaded via live cache
"""

from __future__ import annotations
from tests.mcp_server.test_support import get_default_server_root


from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.core.exceptions import ValidationError
from mcp_server.core.interfaces import IPRStatusReader, PRStatus
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.enforcement_runner import EnforcementContext, EnforcementRunner
from mcp_server.managers.state_repository import FileStateRepository
from mcp_server.schemas import GitConfig
from mcp_server.state.context_loaded_cache import ContextLoadedCache
from mcp_server.tools.git_pull_tool import GitPullInput, GitPullTool
from mcp_server.tools.git_tools import GitCheckoutInput, GitCheckoutTool
from tests.mcp_server.test_support import make_phase_state_engine, make_project_manager

pytestmark = pytest.mark.asyncio

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_BRANCH = "feature/test-268"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pr_reader() -> IPRStatusReader:
    """Return a PR reader that always reports no open PR."""
    reader: MagicMock = MagicMock(spec=IPRStatusReader)
    reader.get_pr_status.return_value = PRStatus.ABSENT
    return reader


def _make_runner(cache: ContextLoadedCache, server_root: Path) -> EnforcementRunner:
    """Build an EnforcementRunner with the live enforcement.yaml and given cache."""
    loader = ConfigLoader(config_root=_REPO_ROOT / get_default_server_root() / "config")
    config = loader.load_enforcement_config()
    return EnforcementRunner(
        workspace_root=_REPO_ROOT,
        config=config,
        git_config=loader.load_git_config(),
        pr_status_reader=_make_pr_reader(),
        server_root=server_root,
        context_loaded_reader=cache,
        state_reader=FileStateRepository(state_file=server_root / "state.json"),
    )


def _make_ctx(tool_name: str, branch: str = _BRANCH) -> EnforcementContext:
    """Build an EnforcementContext with current_branch set."""
    return EnforcementContext(
        workspace_root=_REPO_ROOT,
        tool_name=tool_name,
        params=SimpleNamespace(current_branch=branch),
    )


# ---------------------------------------------------------------------------
# 1-5: Enforcement gate behaviour
# ---------------------------------------------------------------------------


class TestContextLoadedGate:
    """EnforcementRunner gate blocks/allows tools based on context-loaded state."""

    def test_gate_blocks_tool_when_context_not_loaded(self, tmp_path: Path) -> None:
        (tmp_path / "state.json").write_text('{"schema_version": "1.0.0"}')
        cache = ContextLoadedCache()
        runner = _make_runner(cache, server_root=tmp_path)

        with pytest.raises(ValidationError, match="get_work_context"):
            runner.run(
                "git_commit",
                "pre",
                _make_ctx("git_commit"),
                NoteContext(),
                tool_category="branch_mutating",
            )

    def test_gate_allows_tool_when_context_loaded(self, tmp_path: Path) -> None:
        (tmp_path / "state.json").write_text('{"schema_version": "1.0.0"}')
        cache = ContextLoadedCache()
        cache.set_context_loaded(_BRANCH, value=True)
        runner = _make_runner(cache, server_root=tmp_path)

        # Must not raise
        runner.run(
            "git_commit",
            "pre",
            _make_ctx("git_commit"),
            NoteContext(),
            tool_category="branch_mutating",
        )

    def test_force_phase_transition_exempt(self, tmp_path: Path) -> None:
        (tmp_path / "state.json").write_text('{"schema_version": "1.0.0"}')
        cache = ContextLoadedCache()  # context NOT loaded
        runner = _make_runner(cache, server_root=tmp_path)

        # Must not raise: force_phase_transition is in exempt_tools
        runner.run(
            "force_phase_transition",
            "pre",
            _make_ctx("force_phase_transition"),
            NoteContext(),
            tool_category="branch_mutating",
        )

    def test_force_cycle_transition_exempt(self, tmp_path: Path) -> None:
        (tmp_path / "state.json").write_text('{"schema_version": "1.0.0"}')
        cache = ContextLoadedCache()  # context NOT loaded
        runner = _make_runner(cache, server_root=tmp_path)

        # Must not raise: force_cycle_transition is in exempt_tools
        runner.run(
            "force_cycle_transition",
            "pre",
            _make_ctx("force_cycle_transition"),
            NoteContext(),
            tool_category="branch_mutating",
        )

    def test_gate_inactive_on_bootstrap_no_state_json(self, tmp_path: Path) -> None:
        # No state.json created — bootstrap predicate suppresses gate
        cache = ContextLoadedCache()  # context NOT loaded
        runner = _make_runner(cache, server_root=tmp_path)

        # Must not raise: bootstrap predicate active (no state.json)
        runner.run(
            "git_commit",
            "pre",
            _make_ctx("git_commit"),
            NoteContext(),
            tool_category="branch_mutating",
        )

    def test_gate_inactive_when_issue_number_mismatches_branch(self, tmp_path: Path) -> None:
        """C3.D5: gate inactive when state.json present but issue_number mismatches branch."""
        # state.json exists but belongs to a DIFFERENT issue (999 vs branch issue 357)
        (tmp_path / "state.json").write_text(
            '{"schema_version": "1.0.0", "branch": "feature/999-other", "issue_number": 999,'
            ' "workflow_name": "feature", "current_phase": "implementation"}',
            encoding="utf-8",
        )
        cache = ContextLoadedCache()  # context NOT loaded
        git_config = GitConfig(
            branch_types=["feature", "bug", "refactor", "docs", "hotfix", "epic"],
            protected_branches=["main"],
            branch_name_pattern=r"^[a-z0-9-]+$",
            commit_types=["feat", "fix", "docs", "chore"],
            default_base_branch="main",
            issue_title_max_length=72,
        )
        loader = ConfigLoader(config_root=_REPO_ROOT / get_default_server_root() / "config")
        config = loader.load_enforcement_config()
        runner = EnforcementRunner(
            workspace_root=_REPO_ROOT,
            config=config,
            pr_status_reader=_make_pr_reader(),
            server_root=tmp_path,
            context_loaded_reader=cache,
            git_config=git_config,
            state_reader=FileStateRepository(state_file=tmp_path / "state.json"),
        )

        # Must not raise: mismatch bypass active (state.json issue 999 != branch issue 357)
        runner.run(
            "git_commit",
            "pre",
            _make_ctx("git_commit", branch="bug/357-fix-test"),
            NoteContext(),
            tool_category="branch_mutating",
        )


# ---------------------------------------------------------------------------
# 6-7: State reset after checkout / pull
# ---------------------------------------------------------------------------


class TestContextLoadedResets:
    """GitCheckoutTool and GitPullTool clear context-loaded after execution."""

    async def test_checkout_resets_context_loaded(self) -> None:
        cache = ContextLoadedCache()
        cache.set_context_loaded("feature/checkout-test", value=True)
        assert cache.is_context_loaded("feature/checkout-test")

        mock_manager = MagicMock()
        mock_manager.checkout.return_value = None
        mock_manager.get_current_branch.return_value = "main"
        mock_state_engine = MagicMock()
        mock_state_engine.get_state.return_value = SimpleNamespace(
            current_phase="implementation", parent_branch=None
        )

        tool = GitCheckoutTool(
            manager=mock_manager,
            state_engine=mock_state_engine,
            context_loaded_writer=cache,
        )
        await tool.execute(
            GitCheckoutInput(branch="feature/checkout-test"),
            NoteContext(),
        )

        assert not cache.is_context_loaded("feature/checkout-test")

    async def test_pull_resets_context_loaded(self) -> None:
        cache = ContextLoadedCache()
        cache.set_context_loaded("feature/pull-test", value=True)
        assert cache.is_context_loaded("feature/pull-test")

        mock_manager = MagicMock()
        mock_manager.pull.return_value = "Updating abc..def\nFast-forward"
        mock_manager.get_current_branch.return_value = "feature/pull-test"

        tool = GitPullTool(
            manager=mock_manager,
            context_loaded_writer=cache,
        )
        await tool.execute(GitPullInput(), NoteContext())

        assert not cache.is_context_loaded("feature/pull-test")

    def test_phase_transition_resets_context_loaded(self, tmp_path: Path) -> None:
        """PhaseStateEngine.transition() clears the live ContextLoadedCache flag.

        Composition root proof: verifies that the real ContextLoadedCache injected
        as context_loaded_writer into PhaseStateEngine is cleared on transition().
        """
        contracts_yaml = (
            'version: "1.0.0"\n'
            "merge_policy:\n"
            "  pr_allowed_phase: ready\n"
            "  branch_local_artifacts: []\n"
            "workflows:\n"
            "  feature:\n"
            "    phases:\n"
            "      - name: research\n"
            "        instructions:\n"
            "          sub_role: researcher\n"
            "          phase_instructions: Research phase.\n"
            "          handover_template: Co to Imp.\n"
            "      - name: design\n"
            "        instructions:\n"
            "          sub_role: designer\n"
            "          phase_instructions: Design phase.\n"
            "          handover_template: Co to Imp.\n"
            "      - name: ready\n"
            "        instructions:\n"
            "          sub_role: implementer\n"
            "          phase_instructions: Ready phase.\n"
            "          handover_template: Imp to QA.\n"
        )
        config_dir = tmp_path / get_default_server_root() / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "contracts.yaml").write_text(contracts_yaml, encoding="utf-8")

        issue_number = 268
        branch = "feature/268-phase-reset-test"

        pm = make_project_manager(tmp_path)
        pm.initialize_project(
            issue_number=issue_number,
            issue_title="Phase reset integration test",
            workflow_name="feature",
        )

        cache = ContextLoadedCache()
        engine = make_phase_state_engine(tmp_path, project_manager=pm, context_loaded_writer=cache)
        engine.initialize_branch(branch=branch, issue_number=issue_number, initial_phase="research")

        cache.set_context_loaded(branch, value=True)
        assert cache.is_context_loaded(branch)  # precondition

        engine.transition(branch=branch, to_phase="design")

        assert not cache.is_context_loaded(branch)
