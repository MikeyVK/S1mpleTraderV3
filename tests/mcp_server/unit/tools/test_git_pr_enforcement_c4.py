# tests/mcp_server/unit/tools/test_git_pr_enforcement_c4.py
# template=unit_test version=manual-c4 created=2026-04-10T00:00Z updated=
"""
Unit + integration tests for C4: GitCommitTool and CreatePRTool enforcement event declarations.

Tests verify:
- GitCommitTool.enforcement_event == "git_add_or_commit"
- CreatePRTool.enforcement_event == "create_pr"
- Integration: runner.run() dispatched via GitCommitTool.enforcement_event
  excludes tracked artifacts
- Integration: runner.run() via CreatePRTool.enforcement_event blocks wrong phase
- Integration: runner.run() via CreatePRTool.enforcement_event blocks tracked artifacts
- Integration: runner.run() via CreatePRTool.enforcement_event succeeds on happy path

@layer: Tests (Unit/Integration)
@dependencies: [json, pathlib, pytest, unittest.mock, mcp_server.tools.git_tools,
    mcp_server.tools.pr_tools, mcp_server.managers.enforcement_runner,
    mcp_server.managers.phase_contract_resolver, mcp_server.config.loader]
@responsibilities:
    - Test enforcement_event class variable on GitCommitTool and CreatePRTool
    - Test end-to-end enforcement path via runner.run() using tool.enforcement_event
"""

# Standard library
import json
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
    EnforcementContext,
    EnforcementRunner,
)
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext
from mcp_server.tools.git_tools import GitCommitTool
from mcp_server.tools.pr_tools import CreatePRTool

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


def _make_runner(tmp_path: Path, ctx: MergeReadinessContext) -> EnforcementRunner:
    """Build an EnforcementRunner backed by the live enforcement.yaml."""
    enforcement_yaml = _REPO_ROOT / ".st3" / "config" / "enforcement.yaml"
    loader = ConfigLoader(config_root=_REPO_ROOT / ".st3" / "config")
    config = loader.load_enforcement_config(config_path=enforcement_yaml)
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=config,
        merge_readiness_context=ctx,
    )


class TestGitPREnforcementC4:
    """C4: enforcement_event declarations and end-to-end dispatch integration."""

    # ── Class variable declarations ───────────────────────────────────────────

    def test_git_commit_tool_enforcement_event(self) -> None:
        """GitCommitTool declares enforcement_event matching enforcement.yaml tool name."""
        assert GitCommitTool.enforcement_event == "git_add_or_commit"

    def test_create_pr_tool_enforcement_event(self) -> None:
        """CreatePRTool declares enforcement_event matching enforcement.yaml tool name."""
        assert CreatePRTool.enforcement_event == "create_pr"

    # ── Integration: runner.run() dispatches via tool.enforcement_event ───────

    def test_git_commit_in_terminal_phase_excludes_artifacts(self, tmp_path: Path) -> None:
        """runner.run() via GitCommitTool.enforcement_event excludes tracked artifacts."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx())
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=GitCommitTool.name,
            params=SimpleNamespace(),
        )

        with (
            patch(
                "mcp_server.managers.enforcement_runner._git_is_tracked",
                return_value=True,
            ),
            patch("mcp_server.managers.enforcement_runner._git_rm_cached"),
        ):
            notes = runner.run(
                event=GitCommitTool.enforcement_event,  # type: ignore[arg-type]
                timing="pre",
                context=ctx,
            )

        assert len(notes) > 0
        assert any("excluded" in n.lower() for n in notes)

    def test_create_pr_wrong_phase_blocked(self, tmp_path: Path) -> None:
        """runner.run() via CreatePRTool.enforcement_event raises ValidationError (wrong phase)."""
        _write_state(tmp_path, "implementation")
        runner = _make_runner(tmp_path, _merge_ctx(allowed="ready"))
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=CreatePRTool.name,
            params=SimpleNamespace(),
        )

        with pytest.raises(ValidationError, match="ready"):
            runner.run(
                event=CreatePRTool.enforcement_event,  # type: ignore[arg-type]
                timing="pre",
                context=ctx,
            )

    def test_create_pr_tracked_artifacts_blocked(self, tmp_path: Path) -> None:
        """runner.run() via CreatePRTool.enforcement_event raises ValidationError (tracked)."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx())
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=CreatePRTool.name,
            params=SimpleNamespace(),
        )

        with (
            patch(
                "mcp_server.managers.enforcement_runner._git_is_tracked",
                return_value=True,
            ),
            pytest.raises(ValidationError, match="git-tracked"),
        ):
            runner.run(
                event=CreatePRTool.enforcement_event,  # type: ignore[arg-type]
                timing="pre",
                context=ctx,
            )

    def test_create_pr_happy_path(self, tmp_path: Path) -> None:
        """runner.run() with CreatePRTool.enforcement_event returns no notes on happy path."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx())
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=CreatePRTool.name,
            params=SimpleNamespace(),
        )

        with patch(
            "mcp_server.managers.enforcement_runner._git_is_tracked",
            return_value=False,
        ):
            notes = runner.run(
                event=CreatePRTool.enforcement_event,  # type: ignore[arg-type]
                timing="pre",
                context=ctx,
            )

        assert notes == []
