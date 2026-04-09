# tests/mcp_server/unit/managers/test_enforcement_runner_c3.py
# template=unit_test version=3d15d309 created=2026-04-09T19:17Z updated=
"""
Unit tests for mcp_server.managers.enforcement_runner.

Tests for C3 action handlers: exclude_branch_local_artifacts and check_merge_readiness

@layer: Tests (Unit)
@dependencies: [json, pathlib, pytest, unittest.mock, mcp_server.managers.enforcement_runner,
    mcp_server.managers.phase_contract_resolver]
@responsibilities:
    - Test MergeReadinessContext dataclass contract
    - Test EnforcementRunner constructor injection of MergeReadinessContext
    - Test exclude_branch_local_artifacts handler (phase-gate, git rm, output format)
    - Test check_merge_readiness handler (phase check, tracked-artifact check, happy path)
    - Test enforcement.yaml new actions are registered without ConfigError
"""

# Standard library
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# Third-party
import pytest

# Project modules
from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.phase_contracts_config import BranchLocalArtifact
from mcp_server.core.exceptions import ValidationError
from mcp_server.managers.enforcement_runner import (
    EnforcementAction,
    EnforcementConfig,
    EnforcementContext,
    EnforcementRunner,
)
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent

_STATE_JSON = ".st3/state.json"
_DELIVERABLES_JSON = ".st3/deliverables.json"

_ARTIFACT_STATE = BranchLocalArtifact(
    path=_STATE_JSON,
    reason="MCP workflow state — branch-local, must never reach main",
)
_ARTIFACT_DELIVERABLES = BranchLocalArtifact(
    path=_DELIVERABLES_JSON,
    reason="MCP workflow deliverables — branch-local, must never reach main",
)


def _merge_ctx(
    terminal: str = "ready",
    allowed: str = "ready",
) -> MergeReadinessContext:
    return MergeReadinessContext(
        terminal_phase=terminal,
        pr_allowed_phase=allowed,
        branch_local_artifacts=(_ARTIFACT_STATE, _ARTIFACT_DELIVERABLES),
    )


def _make_runner(tmp_path: Path, ctx: MergeReadinessContext) -> EnforcementRunner:
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=EnforcementConfig(enforcement=[]),
        merge_readiness_context=ctx,
    )


def _write_state(tmp_path: Path, current_phase: str) -> None:
    state_dir = tmp_path / ".st3"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(
        json.dumps(
            {
                "branch": "refactor/283-test",
                "workflow_name": "refactor",
                "current_phase": current_phase,
            }
        ),
        encoding="utf-8",
    )


def _base_action() -> EnforcementAction:
    return EnforcementAction(type="exclude_branch_local_artifacts")


def _base_context(tmp_path: Path) -> EnforcementContext:
    return EnforcementContext(
        workspace_root=tmp_path,
        tool_name="git_add_or_commit",
        params=SimpleNamespace(),
    )


class TestEnforcementRunnerC3:
    """Test suite for C3 MergeReadinessContext, enforcement handlers, and yaml registration."""

    # ── MergeReadinessContext contract ────────────────────────────────────────

    def test_merge_readiness_context_is_frozen(self) -> None:
        """MergeReadinessContext rejects mutation (frozen dataclass)."""
        ctx = _merge_ctx()

        with pytest.raises(FrozenInstanceError):
            ctx.terminal_phase = "other"  # type: ignore[misc]

    def test_enforcement_runner_accepts_merge_readiness_context(self, tmp_path: Path) -> None:
        """EnforcementRunner stores injected MergeReadinessContext verbatim."""
        ctx = _merge_ctx()
        runner = _make_runner(tmp_path, ctx)

        assert runner._merge_readiness_context is ctx  # pyright: ignore[reportPrivateUsage]

    # ── exclude_branch_local_artifacts handler ────────────────────────────────

    def test_exclude_handler_only_runs_in_terminal_phase(self, tmp_path: Path) -> None:
        """exclude_branch_local_artifacts returns None when current phase ≠ terminal phase."""
        _write_state(tmp_path, "implementation")
        runner = _make_runner(tmp_path, _merge_ctx(terminal="ready"))
        action = _base_action()
        ctx = _base_context(tmp_path)

        result = runner._handle_exclude_branch_local_artifacts(  # pyright: ignore[reportPrivateUsage]
            action, ctx, tmp_path
        )

        assert result is None

    def test_exclude_handler_skips_untracked_artifacts(self, tmp_path: Path) -> None:
        """exclude_branch_local_artifacts returns None when no artifacts are git-tracked."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx())
        action = _base_action()
        ctx = _base_context(tmp_path)

        with patch(
            "mcp_server.managers.enforcement_runner._git_is_tracked",
            return_value=False,
        ):
            result = runner._handle_exclude_branch_local_artifacts(  # pyright: ignore[reportPrivateUsage]
                action, ctx, tmp_path
            )

        assert result is None

    def test_exclude_handler_removes_tracked_artifacts(self, tmp_path: Path) -> None:
        """exclude_branch_local_artifacts calls git rm --cached for each tracked artifact."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx())
        action = _base_action()
        ctx = _base_context(tmp_path)

        with (
            patch(
                "mcp_server.managers.enforcement_runner._git_is_tracked",
                return_value=True,
            ),
            patch(
                "mcp_server.managers.enforcement_runner._git_rm_cached",
            ) as mock_rm,
        ):
            runner._handle_exclude_branch_local_artifacts(  # pyright: ignore[reportPrivateUsage]
                action, ctx, tmp_path
            )

        assert mock_rm.call_count == 2
        mock_rm.assert_any_call(tmp_path, _STATE_JSON)
        mock_rm.assert_any_call(tmp_path, _DELIVERABLES_JSON)

    def test_exclude_handler_output_format(self, tmp_path: Path) -> None:
        """exclude_branch_local_artifacts return value matches the §2.9 format exactly."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx())
        action = _base_action()
        ctx = _base_context(tmp_path)

        with (
            patch(
                "mcp_server.managers.enforcement_runner._git_is_tracked",
                return_value=True,
            ),
            patch("mcp_server.managers.enforcement_runner._git_rm_cached"),
        ):
            result = runner._handle_exclude_branch_local_artifacts(  # pyright: ignore[reportPrivateUsage]
                action, ctx, tmp_path
            )

        assert result is not None
        assert "Branch-local artifacts excluded from commit index:" in result
        assert f"  - {_STATE_JSON}" in result
        assert f"    Reason: {_ARTIFACT_STATE.reason}" in result
        assert f"  - {_DELIVERABLES_JSON}" in result
        assert (
            "Source: .st3/config/phase_contracts.yaml → merge_policy.branch_local_artifacts"
            in result
        )

    # ── check_merge_readiness handler ─────────────────────────────────────────

    def test_check_merge_readiness_blocks_wrong_phase(self, tmp_path: Path) -> None:
        """check_merge_readiness raises ValidationError when current_phase ≠ pr_allowed_phase."""
        _write_state(tmp_path, "implementation")
        runner = _make_runner(tmp_path, _merge_ctx(allowed="ready"))
        action = EnforcementAction(type="check_merge_readiness")
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="create_pr",
            params=SimpleNamespace(),
        )

        with pytest.raises(ValidationError, match="ready"):
            runner._handle_check_merge_readiness(  # pyright: ignore[reportPrivateUsage]
                action, ctx, tmp_path
            )

    def test_check_merge_readiness_blocks_tracked_artifacts(self, tmp_path: Path) -> None:
        """check_merge_readiness raises ValidationError when tracked artifacts remain."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx())
        action = EnforcementAction(type="check_merge_readiness")
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="create_pr",
            params=SimpleNamespace(),
        )

        with (
            patch(
                "mcp_server.managers.enforcement_runner._git_is_tracked",
                return_value=True,
            ),
            pytest.raises(ValidationError, match="git-tracked"),
        ):
            runner._handle_check_merge_readiness(  # pyright: ignore[reportPrivateUsage]
                action, ctx, tmp_path
            )

    def test_check_merge_readiness_happy_path(self, tmp_path: Path) -> None:
        """check_merge_readiness returns None when phase is correct and no artifacts tracked."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx())
        action = EnforcementAction(type="check_merge_readiness")
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="create_pr",
            params=SimpleNamespace(),
        )

        with patch(
            "mcp_server.managers.enforcement_runner._git_is_tracked",
            return_value=False,
        ):
            result = runner._handle_check_merge_readiness(  # pyright: ignore[reportPrivateUsage]
                action, ctx, tmp_path
            )

        assert result is None

    # ── enforcement.yaml registration ─────────────────────────────────────────

    def test_enforcement_yaml_new_actions_registered(self, tmp_path: Path) -> None:
        """_validate_registered_actions does not raise after C3 handlers are registered."""
        enforcement_yaml = _REPO_ROOT / ".st3" / "config" / "enforcement.yaml"
        loader = ConfigLoader(config_root=_REPO_ROOT / ".st3" / "config")
        config = loader.load_enforcement_config(config_path=enforcement_yaml)

        # Should not raise ConfigError — both new action types must be registered
        EnforcementRunner(workspace_root=tmp_path, config=config)
