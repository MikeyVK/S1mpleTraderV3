# tests/mcp_server/unit/core/test_note_context_unit.py
"""
Unit tests for NoteContext and typed note entries.

Verifies the Cycle 1 note-context contract before later wiring cycles.

@layer: Tests (Unit)
@dependencies: [importlib, types, mcp_server.tools.tool_result]
@responsibilities:
    - Verify operation_notes module importability
    - Verify NoteContext produce/of_type insertion-order behavior
    - Verify render_to_response behavior for renderable and non-renderable notes
"""

# Standard library
import importlib
from types import ModuleType
from typing import Any

# Project modules
from mcp_server.tools.tool_result import ToolResult


def _load_operation_notes_module() -> ModuleType:
    """Import the operation_notes module on demand for RED/GREEN flow."""
    return importlib.import_module("mcp_server.core.operation_notes")


def _get_attr(module: ModuleType, name: str) -> Any:  # noqa: ANN401
    """Return a named attribute from the imported module."""
    return getattr(module, name)


def test_operation_notes_module_exists() -> None:
    """operation_notes module must exist and expose NoteContext."""
    module = _load_operation_notes_module()
    note_context = _get_attr(module, "NoteContext")
    assert note_context is not None


def test_note_context_produce_of_type_insertion_order() -> None:
    """produce() and of_type() preserve insertion order for matching variants."""
    module = _load_operation_notes_module()
    note_context_type = _get_attr(module, "NoteContext")
    exclusion_note_type = _get_attr(module, "ExclusionNote")

    context = note_context_type()
    context.produce(exclusion_note_type(file_path="a.json"))
    context.produce(exclusion_note_type(file_path="b.json"))
    context.produce(exclusion_note_type(file_path="c.json"))

    notes = context.of_type(exclusion_note_type)
    file_paths = [note.file_path for note in notes]
    assert file_paths == ["a.json", "b.json", "c.json"]


def test_render_empty_returns_base_unchanged() -> None:
    """render_to_response returns the original ToolResult when nothing is renderable."""
    module = _load_operation_notes_module()
    note_context_type = _get_attr(module, "NoteContext")

    context = note_context_type()
    base = ToolResult.text("ok")

    result = context.render_to_response(base)

    assert result is base


def test_render_renderable_appends_text_content() -> None:
    """Renderable notes append one TextContent block in insertion order."""
    module = _load_operation_notes_module()
    note_context_type = _get_attr(module, "NoteContext")
    exclusion_note_type = _get_attr(module, "ExclusionNote")
    suggestion_note_type = _get_attr(module, "SuggestionNote")

    context = note_context_type()
    context.produce(exclusion_note_type(file_path=".st3/state.json"))
    context.produce(suggestion_note_type(message="Verify phase names"))
    base = ToolResult.text("ok")

    result = context.render_to_response(base)

    assert result is not base
    assert len(result.content) == 2
    assert result.content[0] == {"type": "text", "text": "ok"}
    assert result.content[1]["type"] == "text"
    assert result.content[1]["text"] == (
        "Excluded from commit index: .st3/state.json\nSuggestion: Verify phase names"
    )


def test_commit_note_not_renderable() -> None:
    """CommitNote must stay machine-only and never appear in rendered output."""
    module = _load_operation_notes_module()
    note_context_type = _get_attr(module, "NoteContext")
    commit_note_type = _get_attr(module, "CommitNote")
    renderable_type = _get_attr(module, "Renderable")

    context = note_context_type()
    commit_note = commit_note_type(commit_hash="abc123")
    context.produce(commit_note)
    base = ToolResult.text("abc123")

    result = context.render_to_response(base)

    assert not isinstance(commit_note, renderable_type)
    assert not hasattr(commit_note, "to_message")
    assert result is base
