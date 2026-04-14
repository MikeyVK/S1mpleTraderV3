"""
Integration tests for blocker and recovery note dispatch.

E2E scenario: enforcement_runner and git_manager produce typed notes
(BlockerNote, RecoveryNote, SuggestionNote) that survive through
@tool_error_handler and get rendered by NoteContext.render_to_response().

@layer: Tests (Integration)
@dependencies: [pytest, mcp_server.core.operation_notes, mcp_server.core.exceptions]
@responsibilities:
    - Test end-to-end typed note dispatch through error paths
    - Verify NoteContext preserves notes even when exception is caught
    - Validate render_to_response appends notes as TextContent
"""

# Third-party
import pytest

# Project modules
from mcp_server.core.exceptions import ExecutionError, PreflightError, ValidationError
from mcp_server.core.operation_notes import (
    BlockerNote,
    NoteContext,
    RecoveryNote,
    SuggestionNote,
)
from mcp_server.tools.tool_result import ToolResult


class TestBlockerRecoveryNoteDispatch:
    """C4 proof: typed notes replace hints/blockers/recovery kwargs."""

    def test_blocker_note_survives_exception(self) -> None:
        """BlockerNote produced before PreflightError survives in NoteContext."""
        ctx = NoteContext()

        # Simulate what git_manager.create_branch does
        ctx.produce(BlockerNote(message="Working tree has uncommitted changes"))

        # Exception is raised (and would be caught by tool_error_handler)
        with pytest.raises(PreflightError):
            raise PreflightError("Preflight checks failed")

        # Notes survive because NoteContext is a mutable reference
        blockers = ctx.of_type(BlockerNote)
        assert len(blockers) == 1
        assert "uncommitted changes" in blockers[0].message

    def test_recovery_note_survives_exception(self) -> None:
        """RecoveryNote produced before ExecutionError survives in NoteContext."""
        ctx = NoteContext()

        # Simulate what enforcement_runner._git_rm_cached does
        ctx.produce(RecoveryNote(message="Run 'git status' to inspect working tree"))
        ctx.produce(RecoveryNote(message="Manual: git rm --cached <file>"))

        with pytest.raises(ExecutionError):
            raise ExecutionError("Failed to exclude files from commit index")

        recoveries = ctx.of_type(RecoveryNote)
        assert len(recoveries) == 2
        assert "git status" in recoveries[0].message
        assert "git rm --cached" in recoveries[1].message

    def test_suggestion_note_survives_exception(self) -> None:
        """SuggestionNote produced before ValidationError survives in NoteContext."""
        ctx = NoteContext()

        ctx.produce(SuggestionNote(message="Use transition_phase to advance to 'ready'"))

        with pytest.raises(ValidationError):
            raise ValidationError("Current phase 'implementation' is not 'ready'")

        suggestions = ctx.of_type(SuggestionNote)
        assert len(suggestions) == 1
        assert "transition_phase" in suggestions[0].message

    def test_render_to_response_appends_notes_to_error_result(self) -> None:
        """render_to_response appends Renderable notes as extra TextContent."""
        ctx = NoteContext()

        # Produce notes before the error
        ctx.produce(BlockerNote(message="Branch is dirty"))
        ctx.produce(SuggestionNote(message="Commit or stash your changes"))

        # Simulate what tool_error_handler returns
        error_result = ToolResult.error(
            message="Preflight checks failed",
            error_code="ERR_PREFLIGHT",
        )

        # Server calls render_to_response
        rendered = ctx.render_to_response(error_result)

        # Original content preserved
        assert rendered.is_error
        assert rendered.error_code == "ERR_PREFLIGHT"
        assert "Preflight checks failed" in rendered.content[0]["text"]

        # Notes appended as additional TextContent block
        assert len(rendered.content) == 2
        notes_text = rendered.content[1]["text"]
        assert "Blocker: Branch is dirty" in notes_text
        assert "Suggestion: Commit or stash your changes" in notes_text

    def test_render_to_response_no_notes_returns_base(self) -> None:
        """render_to_response returns base unchanged when no Renderable notes."""
        ctx = NoteContext()

        base = ToolResult.error(message="Some error", error_code="ERR_TEST")
        rendered = ctx.render_to_response(base)

        assert rendered is base
        assert len(rendered.content) == 1

    def test_render_to_response_appends_notes_to_success_result(self) -> None:
        """render_to_response works on success results too."""
        ctx = NoteContext()
        ctx.produce(SuggestionNote(message="Consider running quality gates"))

        success = ToolResult.text("Operation completed")
        rendered = ctx.render_to_response(success)

        assert not rendered.is_error
        assert len(rendered.content) == 2
        assert "Operation completed" in rendered.content[0]["text"]
        assert "Suggestion: Consider running quality gates" in rendered.content[1]["text"]

    def test_multiple_note_types_rendered_in_order(self) -> None:
        """Multiple note types rendered in insertion order."""
        ctx = NoteContext()

        ctx.produce(BlockerNote(message="First blocker"))
        ctx.produce(RecoveryNote(message="Try this recovery"))
        ctx.produce(SuggestionNote(message="Also a suggestion"))
        ctx.produce(BlockerNote(message="Second blocker"))

        base = ToolResult.error(message="Error", error_code="ERR_TEST")
        rendered = ctx.render_to_response(base)

        notes_text = rendered.content[1]["text"]
        lines = notes_text.split("\n")
        assert lines[0] == "Blocker: First blocker"
        assert lines[1] == "Recovery: Try this recovery"
        assert lines[2] == "Suggestion: Also a suggestion"
        assert lines[3] == "Blocker: Second blocker"
