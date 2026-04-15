# tests/mcp_server/unit/managers/test_enforcement_runner_c9_default_base.py
"""Unit tests for C9: EnforcementRunner.default_base_branch injection.

Tests the new `default_base_branch` constructor parameter on EnforcementRunner
and its propagation into _handle_check_merge_readiness.

Contracts tested:
  - EnforcementRunner accepts `default_base_branch` parameter (defaults to "main")
  - When context.get_param("base") is None/empty, default_base_branch is used
  - When context.get_param("base") is set, it takes precedence over default_base_branch
  - `default_base_branch="main"` is the fallback when not supplied (backward compat)

@layer: Tests (Unit)
@dependencies: [pytest, unittest.mock, mcp_server.managers.enforcement_runner]
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.core.exceptions import ValidationError
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.enforcement_runner import (
    EnforcementAction,
    EnforcementConfig,
    EnforcementContext,
    EnforcementRule,
    EnforcementRunner,
)
from mcp_server.managers.phase_contract_resolver import BranchLocalArtifact, MergeReadinessContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PR_ALLOWED_PHASE = "ready"
_TERMINAL_PHASE = "ready"
_ARTIFACT_PATH = ".st3/state.json"


def _make_merge_readiness_context(
    artifact_path: str = _ARTIFACT_PATH,
    pr_allowed_phase: str = _PR_ALLOWED_PHASE,
    terminal_phase: str = _TERMINAL_PHASE,
) -> MergeReadinessContext:
    return MergeReadinessContext(
        terminal_phase=terminal_phase,
        pr_allowed_phase=pr_allowed_phase,
        branch_local_artifacts=(BranchLocalArtifact(path=artifact_path, reason="branch-local"),),
    )


def _check_merge_readiness_config() -> EnforcementConfig:
    """Minimal enforcement config with one check_merge_readiness action."""
    return EnforcementConfig(
        enforcement=[
            EnforcementRule(
                event_source="tool",
                tool="create_pr",
                timing="pre",
                actions=[EnforcementAction(type="check_merge_readiness")],
            )
        ]
    )


def _make_runner(
    tmp_path: Path,
    *,
    default_base_branch: str = "main",
    merge_readiness_context: MergeReadinessContext | None = None,
) -> EnforcementRunner:
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=_check_merge_readiness_config(),
        merge_readiness_context=merge_readiness_context or _make_merge_readiness_context(),
        default_base_branch=default_base_branch,
    )


def _enforcement_context(base: str | None = None) -> EnforcementContext:
    ctx = MagicMock(spec=EnforcementContext)
    ctx.get_param.side_effect = lambda key: base if key == "base" else None
    return ctx


# ---------------------------------------------------------------------------
# C9 — default_base_branch injection tests
# ---------------------------------------------------------------------------


class TestDefaultBaseBranchInjection:
    """EnforcementRunner must accept and use default_base_branch in merge readiness check."""

    def test_constructor_accepts_default_base_branch(self, tmp_path: Path) -> None:
        """EnforcementRunner constructor must accept default_base_branch without error."""
        runner = _make_runner(tmp_path, default_base_branch="develop")
        assert runner.default_base_branch == "develop"

    def test_constructor_defaults_to_main(self, tmp_path: Path) -> None:
        """When default_base_branch not supplied, must default to 'main' (backward compat)."""
        runner = _make_runner(tmp_path)
        assert runner.default_base_branch == "main"

    def test_default_base_branch_used_when_context_base_is_none(self, tmp_path: Path) -> None:
        """Uses default_base_branch when context.get_param('base') is None."""
        runner = _make_runner(tmp_path, default_base_branch="develop")
        ctx = _enforcement_context(base=None)
        note_ctx = NoteContext()

        # Patch current_phase to pass phase gate, and _has_net_diff_for_path to pass artifact gate
        with (
            patch(
                "mcp_server.managers.enforcement_runner._read_current_phase",
                return_value=_PR_ALLOWED_PHASE,
            ),
            patch(
                "mcp_server.managers.enforcement_runner._has_net_diff_for_path",
                return_value=False,
            ) as mock_diff,
        ):
            runner.run("create_pr", "pre", ctx, note_ctx)

        # base passed to _has_net_diff_for_path must be the injected default, not "main"
        mock_diff.assert_called_once_with(tmp_path, _ARTIFACT_PATH, "develop")

    def test_context_base_overrides_default_base_branch(self, tmp_path: Path) -> None:
        """When context.get_param('base') is set, it takes precedence over default_base_branch."""
        runner = _make_runner(tmp_path, default_base_branch="develop")
        ctx = _enforcement_context(base="feature/custom-base")
        note_ctx = NoteContext()

        with (
            patch(
                "mcp_server.managers.enforcement_runner._read_current_phase",
                return_value=_PR_ALLOWED_PHASE,
            ),
            patch(
                "mcp_server.managers.enforcement_runner._has_net_diff_for_path",
                return_value=False,
            ) as mock_diff,
        ):
            runner.run("create_pr", "pre", ctx, note_ctx)

        mock_diff.assert_called_once_with(tmp_path, _ARTIFACT_PATH, "feature/custom-base")

    def test_hardcoded_main_was_removed(self, tmp_path: Path) -> None:
        """Regression: when default_base_branch='master', 'main' must NOT be used as fallback."""
        runner = _make_runner(tmp_path, default_base_branch="master")
        ctx = _enforcement_context(base=None)
        note_ctx = NoteContext()

        with (
            patch(
                "mcp_server.managers.enforcement_runner._read_current_phase",
                return_value=_PR_ALLOWED_PHASE,
            ),
            patch(
                "mcp_server.managers.enforcement_runner._has_net_diff_for_path",
                return_value=False,
            ) as mock_diff,
        ):
            runner.run("create_pr", "pre", ctx, note_ctx)

        # Must NOT be called with "main" when default_base_branch="master"
        base_used = mock_diff.call_args.args[2]
        assert base_used == "master", (
            f"Expected 'master' but got '{base_used}': hardcoded 'main' fallback not removed"
        )

    def test_merge_readiness_raises_when_artifact_has_net_diff(self, tmp_path: Path) -> None:
        """Artifact with net diff blocks PR — base read from default_base_branch not 'main'."""
        runner = _make_runner(tmp_path, default_base_branch="develop")
        ctx = _enforcement_context(base=None)
        note_ctx = NoteContext()

        with (
            patch(
                "mcp_server.managers.enforcement_runner._read_current_phase",
                return_value=_PR_ALLOWED_PHASE,
            ),
            patch(
                "mcp_server.managers.enforcement_runner._has_net_diff_for_path",
                return_value=True,
            ),
            pytest.raises(ValidationError),
        ):
            runner.run("create_pr", "pre", ctx, note_ctx)
