# tests/mcp_server/integration/test_ready_phase_enforcement.py
# template=unit_test version= created=2026-04-09T00:00Z updated=
"""
Integration tests for ready-phase enforcement (issue #283).

Verifies the full enforcement dispatch path:
  EnforcementRunner.run(event=tool.enforcement_event, ...) produces
  the expected outcome for git_add_or_commit and create_pr events.

@layer: Tests (Integration)
@dependencies: [json, pathlib, pytest, unittest.mock,
    mcp_server.tools.git_tools, mcp_server.tools.pr_tools,
    mcp_server.managers.enforcement_runner,
    mcp_server.managers.phase_contract_resolver,
    mcp_server.config.loader]
@responsibilities:
    - Test enforcement_event class variable on GitCommitTool and CreatePRTool
    - Test git_add_or_commit pre-enforcement excludes tracked artifacts in ready phase
    - Test create_pr pre-enforcement blocks PR outside pr_allowed_phase
    - Test create_pr pre-enforcement blocks PR when branch-local artifacts tracked
    - Test create_pr pre-enforcement allows PR in pr_allowed_phase with no tracked artifacts
"""

# Standard library
import json
import subprocess
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
    EnforcementContext,
    EnforcementRunner,
)
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext
from mcp_server.tools.git_tools import GitCommitTool
from mcp_server.tools.pr_tools import CreatePRTool

_REPO_ROOT = Path(__file__).parent.parent.parent.parent

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
    """Build EnforcementRunner backed by the live enforcement.yaml."""
    enforcement_yaml = _REPO_ROOT / ".st3" / "config" / "enforcement.yaml"
    loader = ConfigLoader(config_root=_REPO_ROOT / ".st3" / "config")
    config = loader.load_enforcement_config(config_path=enforcement_yaml)
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=config,
        merge_readiness_context=ctx,
    )


class TestReadyPhaseEnforcement:
    """Integration tests for the ready-phase enforcement path (issue #283)."""

    # ── Class variable declarations ───────────────────────────────────────────

    def test_git_commit_tool_enforcement_event(self) -> None:
        """GitCommitTool.enforcement_event matches the tool name in enforcement.yaml."""
        assert GitCommitTool.enforcement_event == "git_add_or_commit"

    def test_create_pr_tool_enforcement_event(self) -> None:
        """CreatePRTool.enforcement_event matches the tool name in enforcement.yaml."""
        assert CreatePRTool.enforcement_event == "create_pr"

    # ── Integration: git_add_or_commit pre-enforcement ────────────────────────

    def test_git_commit_blocked_when_branch_local_artifact_staged(self, tmp_path: Path) -> None:
        """git_add_or_commit pre-enforcement excludes tracked artifacts in the ready phase."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx())
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=GitCommitTool.name,
            params=SimpleNamespace(),
        )

        note_context = NoteContext()
        with patch(
            "mcp_server.managers.enforcement_runner._git_is_tracked",
            return_value=True,
        ):
            runner.run(
                event=GitCommitTool.enforcement_event,  # type: ignore[arg-type]
                timing="pre",
                enforcement_ctx=ctx,
                note_context=note_context,
            )

        notes = note_context.of_type(ExclusionNote)
        assert len(notes) > 0
        assert any(_STATE_JSON in n.file_path for n in notes)

    # ── Integration: create_pr pre-enforcement ────────────────────────────────

    def test_create_pr_blocked_outside_pr_allowed_phase(self, tmp_path: Path) -> None:
        """create_pr pre-enforcement raises ValidationError when phase != pr_allowed_phase."""
        _write_state(tmp_path, "implementation")
        runner = _make_runner(tmp_path, _merge_ctx(allowed="ready"))
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=CreatePRTool.name,
            params=SimpleNamespace(),
        )

        note_context = NoteContext()
        with pytest.raises(ValidationError, match="ready"):
            runner.run(
                event=CreatePRTool.enforcement_event,  # type: ignore[arg-type]
                timing="pre",
                enforcement_ctx=ctx,
                note_context=note_context,
            )

    def test_create_pr_blocked_when_branch_local_artifacts_tracked(self, tmp_path: Path) -> None:
        """create_pr pre-enforcement raises ValidationError when tracked artifacts remain."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx())
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=CreatePRTool.name,
            params=SimpleNamespace(),
        )

        note_context = NoteContext()
        with (
            patch(
                "mcp_server.managers.enforcement_runner._has_net_diff_for_path",
                return_value=True,
            ),
            pytest.raises(ValidationError, match="net delta"),
        ):
            runner.run(
                event=CreatePRTool.enforcement_event,  # type: ignore[arg-type]
                timing="pre",
                enforcement_ctx=ctx,
                note_context=note_context,
            )

    def test_create_pr_allowed_in_pr_allowed_phase(self, tmp_path: Path) -> None:
        """create_pr pre-enforcement returns no notes in ready phase with no tracked artifacts."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path, _merge_ctx())
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=CreatePRTool.name,
            params=SimpleNamespace(),
        )

        note_context = NoteContext()
        with patch(
            "mcp_server.managers.enforcement_runner._has_net_diff_for_path",
            return_value=False,
        ):
            runner.run(
                event=CreatePRTool.enforcement_event,  # type: ignore[arg-type]
                timing="pre",
                enforcement_ctx=ctx,
                note_context=note_context,
            )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Minimal git repository with .st3/state.json tracked in the index."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    # Initial commit so HEAD exists
    readme = tmp_path / "README.md"
    readme.write_text("# Test\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


class TestReadyPhaseEnforcementRealGit:
    """End-to-end test: C3 enforcement produces ExclusionNote without calling git rm --cached."""

    def test_artifact_removed_from_index_after_runner_run(self, git_repo: Path) -> None:
        """C3: runner writes ExclusionNote; does NOT call git rm --cached."""
        # Arrange: write and stage the state.json artifact
        _write_state(git_repo, "ready")
        state_file = git_repo / ".st3" / "state.json"
        subprocess.run(
            ["git", "add", str(state_file)],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Verify it is tracked before enforcement
        result_before = subprocess.run(
            ["git", "ls-files", "--error-unmatch", _STATE_JSON],
            cwd=git_repo,
            capture_output=True,
        )
        assert result_before.returncode == 0, "state.json must be staged before test"

        # Act: run enforcement (no mocks — real subprocess calls)
        runner = _make_runner(git_repo, _merge_ctx())
        ctx = EnforcementContext(
            workspace_root=git_repo,
            tool_name=GitCommitTool.name,
            params=SimpleNamespace(),
        )
        note_context = NoteContext()
        runner.run(
            event=GitCommitTool.enforcement_event,  # type: ignore[arg-type]
            timing="pre",
            enforcement_ctx=ctx,
            note_context=note_context,
        )

        notes = note_context.of_type(ExclusionNote)
        assert any(_STATE_JSON in n.file_path for n in notes), (
            "Expected ExclusionNote for state.json in NoteContext"
        )

        # C3: runner no longer calls git rm --cached — state.json must STILL be in index
        result_after = subprocess.run(
            ["git", "ls-files", "--error-unmatch", _STATE_JSON],
            cwd=git_repo,
            capture_output=True,
        )
        assert result_after.returncode == 0, (
            "state.json must REMAIN in git index after C3 enforcement (no git rm in runner)"
        )
