# tests/mcp_server/unit/managers/test_enforcement_runner_c3.py
# template=unit_test version=3d15d309 created=2026-04-09T19:17Z updated=
"""
Unit tests for mcp_server.managers.enforcement_runner.

Tests for C3 action handlers: exclude_branch_local_artifacts and check_merge_readiness.
C6 rewrite: all tests use the public run() API (Principle 14 compliance).

@layer: Tests (Unit)
@dependencies: [json, pathlib, pytest, unittest.mock, mcp_server.managers.enforcement_runner,
    mcp_server.managers.phase_contract_resolver]
@responsibilities:
    - Test MergeReadinessContext dataclass contract
    - Test EnforcementRunner constructor injection of MergeReadinessContext
    - Test exclude_branch_local_artifacts handler (phase-gate, git rm, output format)
    - Test check_merge_readiness handler (phase check, net-diff-artifact check, happy path)
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
from mcp_server.core.operation_notes import ExclusionNote, NoteContext
from mcp_server.managers.enforcement_runner import (
    EnforcementAction,
    EnforcementConfig,
    EnforcementContext,
    EnforcementRule,
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

# ── Inline enforcement configs for unit tests (no YAML file I/O) ──────────────

_GIT_COMMIT_CONFIG = EnforcementConfig(
    enforcement=[
        EnforcementRule(
            event_source="tool",
            tool="git_add_or_commit",
            timing="pre",
            actions=[EnforcementAction(type="exclude_branch_local_artifacts")],
        )
    ]
)

_CREATE_PR_CONFIG = EnforcementConfig(
    enforcement=[
        EnforcementRule(
            event_source="tool",
            tool="create_pr",
            timing="pre",
            actions=[EnforcementAction(type="check_merge_readiness")],
        )
    ]
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


def _make_runner(
    tmp_path: Path,
    ctx: MergeReadinessContext,
    config: EnforcementConfig | None = None,
) -> EnforcementRunner:
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=config or EnforcementConfig(enforcement=[]),
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


def _base_context(tmp_path: Path) -> EnforcementContext:
    return EnforcementContext(
        workspace_root=tmp_path,
        tool_name="git_add_or_commit",
        params=SimpleNamespace(),
    )


def _create_pr_context(tmp_path: Path) -> EnforcementContext:
    return EnforcementContext(
        workspace_root=tmp_path,
        tool_name="create_pr",
        params=SimpleNamespace(),
    )


class TestEnforcementRunnerC3:
    """Test suite for C3 MergeReadinessContext, enforcement handlers, and yaml registration."""

    # ── MergeReadinessContext contract ────────────────────────────────────────

    def test_readiness_ctx_is_frozen(self) -> None:
        """MergeReadinessContext rejects mutation (frozen dataclass)."""
        ctx = _merge_ctx()

        with pytest.raises(FrozenInstanceError):
            ctx.terminal_phase = "other"  # type: ignore[misc]

    def test_runner_uses_injected_readiness_ctx(self, tmp_path: Path) -> None:
        """EnforcementRunner correctly uses the injected MergeReadinessContext.

        C6: public behavioral test via runner.run() — no private attribute access.
        Verifies that terminal_phase from the injected ctx is respected: the
        exclude handler must NOT run in a non-terminal phase.
        """
        _write_state(tmp_path, "implementation")
        ctx = _merge_ctx(terminal="ready")
        runner = _make_runner(tmp_path, ctx, config=_GIT_COMMIT_CONFIG)
        note_context = NoteContext()

        # In "implementation" phase, exclude handler must NOT run (terminal="ready")
        runner.run(
            event="git_add_or_commit",
            timing="pre",
            enforcement_ctx=_base_context(tmp_path),
            note_context=note_context,
        )

        # No exclusion notes — runner correctly used terminal_phase="ready" from injected ctx
        assert len(note_context.of_type(ExclusionNote)) == 0

    # ── exclude_branch_local_artifacts handler ────────────────────────────────

    def test_exclude_handler_only_runs_in_terminal_phase(self, tmp_path: Path) -> None:
        """exclude_branch_local_artifacts does not emit notes when phase ≠ terminal."""
        _write_state(tmp_path, "implementation")
        runner = _make_runner(tmp_path, _merge_ctx(terminal="ready"), config=_GIT_COMMIT_CONFIG)
        note_context = NoteContext()

        runner.run(
            event="git_add_or_commit",
            timing="pre",
            enforcement_ctx=_base_context(tmp_path),
            note_context=note_context,
        )

        assert len(note_context.of_type(ExclusionNote)) == 0

    def test_exclude_handler_skips_untracked_artifacts(self, tmp_path: Path) -> None:
        """exclude_branch_local_artifacts emits no notes when no artifacts are git-tracked."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx(), config=_GIT_COMMIT_CONFIG)
        note_context = NoteContext()

        with patch(
            "mcp_server.managers.enforcement_runner._git_is_tracked",
            return_value=False,
        ):
            runner.run(
                event="git_add_or_commit",
                timing="pre",
                enforcement_ctx=_base_context(tmp_path),
                note_context=note_context,
            )

        assert len(note_context.of_type(ExclusionNote)) == 0

    def test_exclude_handler_removes_tracked_artifacts(self, tmp_path: Path) -> None:
        """exclude_branch_local_artifacts produces ExclusionNote entries, no git rm calls."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx(), config=_GIT_COMMIT_CONFIG)
        note_context = NoteContext()

        with (
            patch(
                "mcp_server.managers.enforcement_runner._git_is_tracked",
                return_value=True,
            ),
            patch(
                "mcp_server.managers.enforcement_runner._git_rm_cached",
            ) as mock_rm,
        ):
            runner.run(
                event="git_add_or_commit",
                timing="pre",
                enforcement_ctx=_base_context(tmp_path),
                note_context=note_context,
            )

        mock_rm.assert_not_called()
        paths = {n.file_path for n in note_context.of_type(ExclusionNote)}
        assert _STATE_JSON in paths
        assert _DELIVERABLES_JSON in paths

    def test_exclude_handler_output_format(self, tmp_path: Path) -> None:
        """exclude_branch_local_artifacts produces exactly one ExclusionNote per artifact."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx(), config=_GIT_COMMIT_CONFIG)
        note_context = NoteContext()

        with (
            patch(
                "mcp_server.managers.enforcement_runner._git_is_tracked",
                return_value=True,
            ),
            patch("mcp_server.managers.enforcement_runner._git_rm_cached"),
        ):
            runner.run(
                event="git_add_or_commit",
                timing="pre",
                enforcement_ctx=_base_context(tmp_path),
                note_context=note_context,
            )

        notes = note_context.of_type(ExclusionNote)
        paths = {n.file_path for n in notes}
        assert _STATE_JSON in paths
        assert _DELIVERABLES_JSON in paths
        assert len(notes) == 2

    def test_exclude_handler_no_git_rm_cached_even_with_subprocess_failure(
        self, tmp_path: Path
    ) -> None:
        """exclude_branch_local_artifacts does not call _git_rm_cached after C3.

        Verifies that even when subprocess.run would return a failure code, no
        ExecutionError is raised — because _git_rm_cached is never called in C3.
        """
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx(), config=_GIT_COMMIT_CONFIG)
        note_context = NoteContext()
        failing_result = SimpleNamespace(returncode=1, stderr=b"fatal: pathspec error")

        with (
            patch(
                "mcp_server.managers.enforcement_runner._git_is_tracked",
                return_value=True,
            ),
            patch(
                "mcp_server.managers.enforcement_runner.subprocess.run",
                return_value=failing_result,
            ),
        ):
            # Should NOT raise — no git rm call, so subprocess failure is irrelevant
            runner.run(
                event="git_add_or_commit",
                timing="pre",
                enforcement_ctx=_base_context(tmp_path),
                note_context=note_context,
            )

        paths = {n.file_path for n in note_context.of_type(ExclusionNote)}
        assert _STATE_JSON in paths

    # ── check_merge_readiness handler ─────────────────────────────────────────

    def test_check_merge_readiness_blocks_wrong_phase(self, tmp_path: Path) -> None:
        """check_merge_readiness raises ValidationError when current_phase ≠ pr_allowed_phase."""
        _write_state(tmp_path, "implementation")
        runner = _make_runner(tmp_path, _merge_ctx(allowed="ready"), config=_CREATE_PR_CONFIG)

        with pytest.raises(ValidationError, match="ready"):
            runner.run(
                event="create_pr",
                timing="pre",
                enforcement_ctx=_create_pr_context(tmp_path),
                note_context=NoteContext(),
            )

    def test_check_merge_readiness_blocks_tracked_artifacts(self, tmp_path: Path) -> None:
        """check_merge_readiness raises ValidationError when net-diff artifacts remain."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx(), config=_CREATE_PR_CONFIG)

        with (
            patch(
                "mcp_server.managers.enforcement_runner._has_net_diff_for_path",
                return_value=True,
            ),
            pytest.raises(ValidationError, match="git-tracked"),
        ):
            runner.run(
                event="create_pr",
                timing="pre",
                enforcement_ctx=_create_pr_context(tmp_path),
                note_context=NoteContext(),
            )

    def test_check_merge_readiness_happy_path(self, tmp_path: Path) -> None:
        """check_merge_readiness does not raise when phase correct and no net-diff artifacts."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx(), config=_CREATE_PR_CONFIG)

        with patch(
            "mcp_server.managers.enforcement_runner._has_net_diff_for_path",
            return_value=False,
        ):
            runner.run(
                event="create_pr",
                timing="pre",
                enforcement_ctx=_create_pr_context(tmp_path),
                note_context=NoteContext(),
            )

    # ── enforcement.yaml registration ─────────────────────────────────────────

    def test_enforcement_yaml_new_actions_registered(self, tmp_path: Path) -> None:
        """_validate_registered_actions does not raise after C3 handlers are registered."""
        enforcement_yaml = _REPO_ROOT / ".st3" / "config" / "enforcement.yaml"
        loader = ConfigLoader(config_root=_REPO_ROOT / ".st3" / "config")
        config = loader.load_enforcement_config(config_path=enforcement_yaml)

        # Should not raise ConfigError — both new action types must be registered
        EnforcementRunner(workspace_root=tmp_path, config=config)
