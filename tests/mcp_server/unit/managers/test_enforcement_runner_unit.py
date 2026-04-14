# tests\mcp_server\unit\managers\test_enforcement_runner_unit.py
# template=unit_test version=3d15d309 created=2026-04-14T09:09Z updated=
"""
Unit tests for mcp_server.managers.enforcement_runner.

C3 NoteContext wiring: EnforcementRunner.run() returns None, writes ExclusionNote
per excluded artifact, performs no git rm operations, and GitCommitTool.execute()
accepts context and reads ExclusionNote to build skip_paths.

@layer: Tests (Unit)
@dependencies: [json, pathlib, pytest, unittest.mock, mcp_server.core.operation_notes,
    mcp_server.managers.enforcement_runner, mcp_server.tools.git_tools]
@responsibilities:
    - Prove EnforcementRunner.run() returns None after C3 (not list[str])
    - Prove ExclusionNote written to NoteContext for each confirmed-tracked artifact
    - Prove no git rm --cached in _handle_exclude_branch_local_artifacts after C3
    - Prove GitCommitTool.execute() accepts context: NoteContext as second parameter
    - Prove GitCommitTool reads ExclusionNote.file_path and forwards as skip_paths
"""

# Standard library
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Third-party
import pytest

# Project modules
from mcp_server.config.schemas.phase_contracts_config import BranchLocalArtifact
from mcp_server.core.operation_notes import ExclusionNote, NoteContext
from mcp_server.managers.enforcement_runner import (
    EnforcementAction,
    EnforcementConfig,
    EnforcementContext,
    EnforcementRule,
    EnforcementRunner,
)
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext

_STATE_JSON = ".st3/state.json"
_DELIVERABLES_JSON = ".st3/deliverables.json"

_ARTIFACT_STATE = BranchLocalArtifact(
    path=_STATE_JSON,
    reason="workflow state — branch-local",
)
_ARTIFACT_DELIVERABLES = BranchLocalArtifact(
    path=_DELIVERABLES_JSON,
    reason="workflow deliverables — branch-local",
)


def _merge_ctx() -> MergeReadinessContext:
    return MergeReadinessContext(
        terminal_phase="ready",
        pr_allowed_phase="ready",
        branch_local_artifacts=(_ARTIFACT_STATE, _ARTIFACT_DELIVERABLES),
    )


def _make_runner(tmp_path: Path) -> EnforcementRunner:
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=EnforcementConfig(enforcement=[]),
        merge_readiness_context=_merge_ctx(),
    )


def _make_exclusion_runner(tmp_path: Path) -> EnforcementRunner:
    """Runner with the exclude_branch_local_artifacts rule wired for git_add_or_commit pre."""
    config = EnforcementConfig(
        enforcement=[
            EnforcementRule(
                event_source="tool",
                tool="git_add_or_commit",
                timing="pre",
                actions=[EnforcementAction(type="exclude_branch_local_artifacts")],
            )
        ]
    )
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=config,
        merge_readiness_context=_merge_ctx(),
    )


def _write_state(tmp_path: Path, current_phase: str) -> None:
    state_dir = tmp_path / ".st3"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(
        json.dumps({"current_phase": current_phase, "branch": "refactor/283"}),
        encoding="utf-8",
    )


class TestEnforcementRunnerC3:
    """C3 contract: run() returns None and writes ExclusionNote per excluded artifact."""

    def test_enforcement_runner_run_returns_none(self, tmp_path: Path) -> None:
        """run() must return None — not list[str] — after C3 rewrite."""
        runner = _make_runner(tmp_path)
        _write_state(tmp_path, "ready")
        enforcement_ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="git_add_or_commit",
            params={},
        )
        note_context = NoteContext()

        with patch(
            "mcp_server.managers.enforcement_runner._git_is_tracked",
            return_value=False,
        ):
            result = runner.run(
                event="git_add_or_commit",
                timing="pre",
                enforcement_ctx=enforcement_ctx,
                note_context=note_context,
            )

        assert result is None, f"Expected None but got {result!r}"

    def test_enforcement_runner_writes_exclusion_note(self, tmp_path: Path) -> None:
        """Confirmed-tracked artifacts must produce ExclusionNote entries in NoteContext.

        Planning.md C3 deliverable #1: run() writes ExclusionNote per excluded path.
        """
        runner = _make_exclusion_runner(tmp_path)
        _write_state(tmp_path, "ready")
        enforcement_ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="git_add_or_commit",
            params={},
        )
        note_context = NoteContext()

        with patch(
            "mcp_server.managers.enforcement_runner._git_is_tracked",
            return_value=True,
        ):
            runner.run(
                event="git_add_or_commit",
                timing="pre",
                enforcement_ctx=enforcement_ctx,
                note_context=note_context,
            )

        notes = note_context.of_type(ExclusionNote)
        paths = {n.file_path for n in notes}
        assert _STATE_JSON in paths, (
            f"Expected ExclusionNote for '{_STATE_JSON}' in paths: {sorted(paths)}"
        )
        assert _DELIVERABLES_JSON in paths, (
            f"Expected ExclusionNote for '{_DELIVERABLES_JSON}' in paths: {sorted(paths)}"
        )

    def test_enforcement_runner_no_git_ops(self, tmp_path: Path) -> None:
        """_handle_exclude_branch_local_artifacts must not call _git_rm_cached after C3."""
        runner = _make_exclusion_runner(tmp_path)
        _write_state(tmp_path, "ready")
        enforcement_ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="git_add_or_commit",
            params={},
        )
        note_context = NoteContext()

        with (
            patch(
                "mcp_server.managers.enforcement_runner._git_is_tracked",
                return_value=True,
            ),
            patch(
                "mcp_server.managers.enforcement_runner._git_rm_cached"
            ) as mock_rm,
        ):
            runner.run(
                event="git_add_or_commit",
                timing="pre",
                enforcement_ctx=enforcement_ctx,
                note_context=note_context,
            )

        mock_rm.assert_not_called()


class TestGitCommitToolC3:
    """C3 contract: GitCommitTool.execute() accepts NoteContext as second parameter."""

    @pytest.mark.asyncio
    async def test_git_commit_tool_execute_accepts_context(self) -> None:
        """execute(params, context) accepted as new public contract."""
        from mcp_server.tools.git_tools import GitCommitInput, GitCommitTool

        mock_manager = MagicMock()
        mock_manager.git_config.commit_types = ["feat", "fix", "chore", "refactor", "test", "docs"]
        mock_manager.adapter.get_current_branch.return_value = "refactor/283"
        mock_manager.commit_with_scope.return_value = "abc1234"

        tool = GitCommitTool(manager=mock_manager)
        params = GitCommitInput(message="test", workflow_phase="documentation")
        result = await tool.execute(params, NoteContext())
        assert not result.is_error

    @pytest.mark.asyncio
    async def test_git_commit_tool_reads_exclusion_note(self) -> None:
        """GitCommitTool must read ExclusionNote entries and pass as skip_paths."""
        from mcp_server.tools.git_tools import GitCommitInput, GitCommitTool

        mock_manager = MagicMock()
        mock_manager.git_config.commit_types = ["feat", "fix", "chore", "refactor", "test", "docs"]
        mock_manager.adapter.get_current_branch.return_value = "refactor/283"
        mock_manager.commit_with_scope.return_value = "def5678"

        tool = GitCommitTool(manager=mock_manager)
        params = GitCommitInput(message="ready", workflow_phase="documentation")
        note_context = NoteContext()
        note_context.produce(ExclusionNote(file_path=_STATE_JSON))
        note_context.produce(ExclusionNote(file_path=_DELIVERABLES_JSON))

        await tool.execute(params, note_context)

        skip_paths = mock_manager.commit_with_scope.call_args.kwargs.get(
            "skip_paths", frozenset()
        )
        assert _STATE_JSON in skip_paths, (
            f"Expected '{_STATE_JSON}' in skip_paths but got: {skip_paths}"
        )
        assert _DELIVERABLES_JSON in skip_paths, (
            f"Expected '{_DELIVERABLES_JSON}' in skip_paths but got: {skip_paths}"
        )

    @pytest.mark.asyncio
    async def test_server_renders_exclusion_note_in_response(self) -> None:
        """NoteContext.render_to_response must include ExclusionNote text in the result."""
        from mcp_server.tools.tool_result import ToolResult

        note_context = NoteContext()
        note_context.produce(ExclusionNote(file_path=_STATE_JSON))
        base = ToolResult.text("abc1234")

        rendered = note_context.render_to_response(base)

        all_text = " ".join(
            c["text"] for c in rendered.content if c.get("type") == "text"
        )
        assert _STATE_JSON in all_text, (
            f"Expected '{_STATE_JSON}' in rendered content but got: {all_text!r}"
        )
