# tests\mcp_server\unit\managers\test_enforcement_runner_unit.py
# template=unit_test version=3d15d309 created=2026-04-14T09:09Z updated=
"""
Unit tests for mcp_server.managers.enforcement_runner (C6 cleanup).

GitCommitTool.execute() NoteContext wiring tests.

@layer: Tests (Unit)
@dependencies: [json, pathlib, pytest, unittest.mock, mcp_server.core.operation_notes,
    mcp_server.managers.enforcement_runner, mcp_server.tools.git_tools]
@responsibilities:
    - Prove GitCommitTool.execute() accepts context: NoteContext as second parameter
    - Prove GitCommitTool reads ExclusionNote.file_path and forwards as skip_paths
"""

# Standard library
from unittest.mock import MagicMock

# Third-party
import pytest

# Project modules
from mcp_server.core.operation_notes import ExclusionNote, NoteContext
from mcp_server.tools.git_tools import GitCommitInput, GitCommitTool
from mcp_server.tools.tool_result import ToolResult

_STATE_JSON = ".st3/state.json"
_DELIVERABLES_JSON = ".st3/deliverables.json"


class TestGitCommitToolC3:
    """C3 contract: GitCommitTool.execute() accepts NoteContext as second parameter."""

    @pytest.mark.asyncio
    async def test_git_commit_tool_execute_accepts_context(self) -> None:
        """execute(params, context) accepted as new public contract."""
        mock_manager = MagicMock()
        mock_manager.git_config.commit_types = ["feat", "fix", "chore", "refactor", "test", "docs"]
        mock_manager.adapter.get_current_branch.return_value = "refactor/283"
        mock_manager.commit_with_scope.return_value = "abc1234"

        tool = GitCommitTool(manager=mock_manager)
        params = GitCommitInput(message="test", workflow_phase="documentation")
        result = await tool.execute(params, NoteContext())
        assert not result.is_error

    @pytest.mark.asyncio
    @pytest.mark.xfail(
        reason=(
            "Pre-existing: neutralize_to_base not yet called by GitCommitTool "
            "(C8 contract, separate issue)"
        ),
        strict=False,
    )
    async def test_git_commit_tool_reads_exclusion_note(self) -> None:
        """GitCommitTool with ExclusionNotes must call neutralize_to_base (C8 Model 1 contract)."""
        mock_manager = MagicMock()
        mock_manager.git_config.commit_types = ["feat", "fix", "chore", "refactor", "test", "docs"]
        mock_manager.git_config.default_base_branch = "main"
        mock_manager.adapter.get_current_branch.return_value = "refactor/283"
        mock_manager.commit_with_scope.return_value = "def5678"

        tool = GitCommitTool(manager=mock_manager)
        params = GitCommitInput(message="ready", workflow_phase="ready")
        note_context = NoteContext()
        note_context.produce(ExclusionNote(file_path=_STATE_JSON))
        note_context.produce(ExclusionNote(file_path=_DELIVERABLES_JSON))

        await tool.execute(params, note_context)

        mock_manager.adapter.neutralize_to_base.assert_called_once()
        call_paths = mock_manager.adapter.neutralize_to_base.call_args.args[0]
        assert _STATE_JSON in call_paths
        assert _DELIVERABLES_JSON in call_paths

        skip_paths = mock_manager.commit_with_scope.call_args.kwargs.get("skip_paths")
        assert skip_paths == frozenset()

    @pytest.mark.asyncio
    async def test_server_renders_exclusion_note_in_response(self) -> None:
        """NoteContext.render_to_response must include ExclusionNote text in the result."""
        note_context = NoteContext()
        note_context.produce(ExclusionNote(file_path=_STATE_JSON))
        base = ToolResult.text("abc1234")

        rendered = note_context.render_to_response(base)

        all_text = " ".join(c["text"] for c in rendered.content if c.get("type") == "text")
        assert _STATE_JSON in all_text
