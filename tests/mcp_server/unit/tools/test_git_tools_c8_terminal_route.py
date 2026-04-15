# tests/mcp_server/unit/tools/test_git_tools_c8_terminal_route.py
"""Unit tests for C8: GitCommitTool terminal-phase route (neutralize_to_base).

Tests the route-selection logic in GitCommitTool.execute() when ExclusionNote
entries are present in the NoteContext — the "terminal-phase route".

Contracts tested:
  - When ExclusionNote entries are present:
    - adapter.neutralize_to_base() is called with the resolved paths + base
    - commit_with_scope() is called with files=None and skip_paths=frozenset()
    - params.message is NOT used — fixed message with resolved_base is used
    - 3-tier base resolution: params.base > state parent_branch > git_config.default_base_branch
  - When no ExclusionNote entries are present:
    - adapter.neutralize_to_base() is NOT called
    - Normal route: params.message used, skip_paths=frozenset()

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.tools.git_tools, mcp_server.core.operation_notes]
"""

from unittest.mock import ANY, MagicMock

import pytest

from mcp_server.core.operation_notes import ExclusionNote, NoteContext
from mcp_server.managers.state_repository import BranchState
from mcp_server.tools.git_tools import GitCommitInput, GitCommitTool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_manager(
    branch: str = "refactor/283-feature",
    default_base_branch: str = "main",
    parent_branch: str | None = None,
) -> MagicMock:
    """Return a fully configured mock GitManager + state engine."""
    manager = MagicMock()
    git_config = MagicMock()
    git_config.commit_types = ["feat", "fix", "docs", "chore", "test", "refactor"]
    git_config.has_commit_type.side_effect = lambda v: v.lower() in git_config.commit_types
    git_config.default_base_branch = default_base_branch
    manager.git_config = git_config
    manager.adapter.get_current_branch.return_value = branch
    manager.commit_with_scope.return_value = "abc1234"

    state_engine = MagicMock()
    state = BranchState(
        branch=branch,
        issue_number=283,
        workflow_name="refactor",
        current_phase="ready",
        parent_branch=parent_branch,
    )
    state_engine.get_state.return_value = state
    state_engine.get_current_phase.return_value = "ready"

    return manager, state_engine  # type: ignore[return-value]


def _context_with_exclusions(*paths: str) -> NoteContext:
    """Return a NoteContext with ExclusionNote entries for each path."""
    ctx = NoteContext()
    for path in paths:
        ctx.produce(ExclusionNote(file_path=path))
    return ctx


# ---------------------------------------------------------------------------
# C8 — terminal route: neutralize_to_base called
# ---------------------------------------------------------------------------


class TestTerminalRoute:
    """When ExclusionNote entries are present, the terminal-phase route must fire."""

    @pytest.mark.asyncio
    async def test_neutralize_to_base_called_with_excluded_paths(self) -> None:
        """adapter.neutralize_to_base() called with excluded paths + resolved base."""
        manager, state_engine = _make_manager()
        tool = GitCommitTool(manager=manager, state_engine=state_engine)

        ctx = _context_with_exclusions(".st3/state.json", ".st3/deliverables.json")
        params = GitCommitInput(workflow_phase="ready", message="ignored in terminal route")

        await tool.execute(params, ctx)

        manager.adapter.neutralize_to_base.assert_called_once_with(
            frozenset({".st3/state.json", ".st3/deliverables.json"}),
            "main",  # default_base_branch fallback
        )

    @pytest.mark.asyncio
    async def test_commit_with_scope_called_files_none_skip_paths_empty(self) -> None:
        """commit_with_scope uses files=None and skip_paths=frozenset() in terminal route."""
        manager, state_engine = _make_manager()
        tool = GitCommitTool(manager=manager, state_engine=state_engine)

        ctx = _context_with_exclusions(".st3/state.json")
        params = GitCommitInput(workflow_phase="ready", message="should be ignored")

        await tool.execute(params, ctx)

        call_kwargs = manager.commit_with_scope.call_args.kwargs
        assert call_kwargs["files"] is None, "Terminal route must pass files=None"
        assert call_kwargs["skip_paths"] == frozenset(), (
            "Terminal route must pass skip_paths=frozenset() — neutralize handles exclusion"
        )

    @pytest.mark.asyncio
    async def test_params_message_ignored_in_terminal_route(self) -> None:
        """params.message is NOT used in terminal route; fixed neutralize message is used."""
        manager, state_engine = _make_manager()
        tool = GitCommitTool(manager=manager, state_engine=state_engine)

        ctx = _context_with_exclusions(".st3/state.json")
        params = GitCommitInput(workflow_phase="ready", message="caller supplied message")

        await tool.execute(params, ctx)

        call_kwargs = manager.commit_with_scope.call_args.kwargs
        assert "caller supplied message" not in call_kwargs["message"], (
            "Terminal route must not use params.message"
        )
        assert "neutralize" in call_kwargs["message"], (
            "Terminal route commit message must contain 'neutralize'"
        )

    @pytest.mark.asyncio
    async def test_base_resolution_tier1_explicit_params_base(self) -> None:
        """Tier 1: params.base takes precedence over state parent_branch and default."""
        manager, state_engine = _make_manager(parent_branch="epic/100-parent")
        tool = GitCommitTool(manager=manager, state_engine=state_engine)

        ctx = _context_with_exclusions(".st3/state.json")
        params = GitCommitInput(
            workflow_phase="ready",
            message="msg",
            base="feature/explicit-base",
        )

        await tool.execute(params, ctx)

        manager.adapter.neutralize_to_base.assert_called_once_with(
            ANY,
            "feature/explicit-base",
        )

    @pytest.mark.asyncio
    async def test_base_resolution_tier2_state_parent_branch(self) -> None:
        """Tier 2: state.parent_branch used when params.base is None."""
        manager, state_engine = _make_manager(parent_branch="epic/100-parent")
        tool = GitCommitTool(manager=manager, state_engine=state_engine)

        ctx = _context_with_exclusions(".st3/state.json")
        params = GitCommitInput(workflow_phase="ready", message="msg")  # no base

        await tool.execute(params, ctx)

        manager.adapter.neutralize_to_base.assert_called_once_with(
            ANY,
            "epic/100-parent",
        )

    @pytest.mark.asyncio
    async def test_base_resolution_tier3_git_config_default(self) -> None:
        """Tier 3: git_config.default_base_branch used when params.base is None and no parent."""
        manager, state_engine = _make_manager(
            default_base_branch="develop",
            parent_branch=None,  # no parent in state
        )
        tool = GitCommitTool(manager=manager, state_engine=state_engine)

        ctx = _context_with_exclusions(".st3/state.json")
        params = GitCommitInput(workflow_phase="ready", message="msg")  # no base

        await tool.execute(params, ctx)

        manager.adapter.neutralize_to_base.assert_called_once_with(
            ANY,
            "develop",
        )


# ---------------------------------------------------------------------------
# C8 — normal route: neutralize_to_base NOT called
# ---------------------------------------------------------------------------


class TestNormalRoute:
    """When no ExclusionNote entries are present, the normal commit route must fire."""

    @pytest.mark.asyncio
    async def test_neutralize_not_called_on_normal_route(self) -> None:
        """No ExclusionNotes → adapter.neutralize_to_base() must NOT be called."""
        manager, state_engine = _make_manager()
        tool = GitCommitTool(manager=manager, state_engine=state_engine)

        ctx = NoteContext()  # no ExclusionNotes
        params = GitCommitInput(
            workflow_phase="implementation",
            message="feat: add something",
            cycle_number=1,
        )

        await tool.execute(params, ctx)

        manager.adapter.neutralize_to_base.assert_not_called()

    @pytest.mark.asyncio
    async def test_params_message_used_on_normal_route(self) -> None:
        """Normal route uses params.message as commit message."""
        manager, state_engine = _make_manager()
        tool = GitCommitTool(manager=manager, state_engine=state_engine)

        ctx = NoteContext()
        params = GitCommitInput(
            workflow_phase="implementation",
            message="add feature",
            cycle_number=1,
        )

        await tool.execute(params, ctx)

        call_kwargs = manager.commit_with_scope.call_args.kwargs
        assert call_kwargs["message"] == "add feature"

    @pytest.mark.asyncio
    async def test_base_field_accepted_in_input(self) -> None:
        """GitCommitInput must accept base: str | None field without validation error."""
        params = GitCommitInput(
            workflow_phase="ready",
            message="test",
            base="main",
        )
        assert params.base == "main"

    @pytest.mark.asyncio
    async def test_base_field_defaults_to_none(self) -> None:
        """GitCommitInput.base defaults to None when not provided."""
        params = GitCommitInput(workflow_phase="research", message="test")
        assert params.base is None
