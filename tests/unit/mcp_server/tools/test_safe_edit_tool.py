# tests/unit/mcp_server/tools/test_safe_edit_tool.py
# pylint: disable=redefined-outer-name
"""Tests for SafeEditTool."""
import tempfile
from pathlib import Path

import pytest

from mcp_server.tools.safe_edit_tool import (
    SafeEditInput, SafeEditTool, LineEdit, SearchReplace, InsertLine
)


@pytest.fixture
def safe_edit_tool():
    """Create SafeEditTool instance."""
    return SafeEditTool()


@pytest.fixture
def temp_file():
    """Create temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_path = Path(f.name)
        f.write("Original content\n")

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def multiline_file():
    """Create temporary file with multiple lines."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_path = Path(f.name)
        f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def search_replace_file():
    """Create temporary file for search/replace testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_path = Path(f.name)
        f.write("Hello world\nHello Python\nGoodbye world\n")

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


def get_text_content(result):
    """Extract text content from ToolResult."""
    return result.content[0]["text"]


# --- Diff Preview Tests ---

@pytest.mark.asyncio
async def test_diff_preview_shown_by_default(safe_edit_tool, temp_file):
    """Test that diff preview is shown by default when show_diff=True."""
    params = SafeEditInput(
        path=str(temp_file),
        content="New content\n",
        mode="strict",
        show_diff=True
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    # Should contain diff preview
    assert "**Diff Preview:**" in text
    assert "```diff" in text
    assert "-Original content" in text
    assert "+New content" in text


@pytest.mark.asyncio
async def test_diff_preview_can_be_disabled(safe_edit_tool, temp_file):
    """Test that diff preview can be disabled with show_diff=False."""
    params = SafeEditInput(
        path=str(temp_file),
        content="New content\n",
        mode="strict",
        show_diff=False
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    # Should NOT contain diff preview
    assert "**Diff Preview:**" not in text
    assert "```diff" not in text


@pytest.mark.asyncio
async def test_diff_preview_empty_for_no_changes(safe_edit_tool, temp_file):
    """Test that diff preview is empty when content is unchanged."""
    # Read original content
    original = temp_file.read_text()

    params = SafeEditInput(
        path=str(temp_file),
        content=original,
        mode="strict",
        show_diff=True
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    # Should not show diff if no changes (empty diff should not be displayed)
    assert "**Diff Preview:**" not in text


@pytest.mark.asyncio
async def test_diff_preview_for_new_file(safe_edit_tool):
    """Test that diff preview works for new files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        new_file = Path(tmpdir) / "new_file.txt"

        params = SafeEditInput(
            path=str(new_file),
            content="New file content\n",
            mode="strict",
            show_diff=True
        )

        result = await safe_edit_tool.execute(params)
        text = get_text_content(result)

        # Should show diff with + lines only (new file)
        assert "**Diff Preview:**" in text
        assert "+New file content" in text


@pytest.mark.asyncio
async def test_diff_preview_in_verify_only_mode(safe_edit_tool, temp_file):
    """Test that diff preview is shown in verify_only mode."""
    params = SafeEditInput(
        path=str(temp_file),
        content="New content\n",
        mode="verify_only",
        show_diff=True
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    # Should contain diff preview and validation result
    assert "**Diff Preview:**" in text
    assert "```diff" in text
    # File should not actually be written
    assert "Original content" in temp_file.read_text()


# --- Line Edit Tests ---

@pytest.mark.asyncio
async def test_line_edit_single_line(safe_edit_tool, multiline_file):
    """Test editing a single line."""
    params = SafeEditInput(
        path=str(multiline_file),
        line_edits=[LineEdit(start_line=2, end_line=2, new_content="Modified Line 2\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "✅ File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "Line 1"
    assert lines[1] == "Modified Line 2"
    assert lines[2] == "Line 3"


@pytest.mark.asyncio
async def test_line_edit_multiple_non_overlapping(safe_edit_tool, multiline_file):
    """Test editing multiple non-overlapping lines."""
    params = SafeEditInput(
        path=str(multiline_file),
        line_edits=[
            LineEdit(start_line=1, end_line=1, new_content="New Line 1\n"),
            LineEdit(start_line=3, end_line=3, new_content="New Line 3\n"),
        ],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "✅ File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "New Line 1"
    assert lines[1] == "Line 2"
    assert lines[2] == "New Line 3"
    assert lines[3] == "Line 4"


@pytest.mark.asyncio
async def test_line_edit_range(safe_edit_tool, multiline_file):
    """Test editing a range of lines."""
    params = SafeEditInput(
        path=str(multiline_file),
        line_edits=[LineEdit(start_line=2, end_line=4, new_content="Replacement\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "✅ File saved successfully" in text

    # Verify file content - lines 2-4 replaced with single line
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "Line 1"
    assert lines[1] == "Replacement"
    assert lines[2] == "Line 5"


@pytest.mark.asyncio
async def test_line_edit_out_of_bounds(safe_edit_tool, multiline_file):
    """Test that out-of-bounds line edits are rejected."""
    params = SafeEditInput(
        path=str(multiline_file),
        line_edits=[LineEdit(start_line=10, end_line=10, new_content="New Line\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)

    assert result.is_error
    text = get_text_content(result)
    assert "out of bounds" in text.lower()


@pytest.mark.asyncio
async def test_line_edit_overlapping_rejected(safe_edit_tool, multiline_file):
    """Test that overlapping line edits are rejected."""
    params = SafeEditInput(
        path=str(multiline_file),
        line_edits=[
            LineEdit(start_line=2, end_line=4, new_content="Edit 1\n"),
            LineEdit(start_line=3, end_line=5, new_content="Edit 2\n"),
        ],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)

    assert result.is_error
    text = get_text_content(result)
    assert "overlapping" in text.lower()


@pytest.mark.asyncio
async def test_line_edit_on_new_file_rejected(safe_edit_tool):
    """Test that line edits on non-existent files are rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        new_file = Path(tmpdir) / "nonexistent.txt"

        params = SafeEditInput(
            path=str(new_file),
            line_edits=[LineEdit(start_line=1, end_line=1, new_content="Line 1\n")],
            mode="strict"
        )

        result = await safe_edit_tool.execute(params)

        assert result.is_error
        text = get_text_content(result)
        assert "non-existent" in text.lower()


# --- Search/Replace Tests ---

@pytest.mark.asyncio
async def test_search_replace_literal_single_occurrence(safe_edit_tool, search_replace_file):
    """Test literal search/replace with single occurrence."""
    params = SafeEditInput(
        path=str(search_replace_file),
        search_replace=SearchReplace(search="world", replace="universe"),
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "✅ File saved successfully" in text

    # Verify file content - both occurrences should be replaced
    content = search_replace_file.read_text()
    assert "Hello universe" in content
    assert "Goodbye universe" in content
    assert "world" not in content


@pytest.mark.asyncio
async def test_search_replace_with_count_limit(safe_edit_tool, search_replace_file):
    """Test search/replace with count limit."""
    params = SafeEditInput(
        path=str(search_replace_file),
        search_replace=SearchReplace(search="Hello", replace="Hi", count=1),
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "✅ File saved successfully" in text

    # Verify only first occurrence was replaced
    content = search_replace_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "Hi world"
    assert lines[1] == "Hello Python"  # Second "Hello" unchanged


@pytest.mark.asyncio
async def test_search_replace_regex_mode(safe_edit_tool, search_replace_file):
    """Test regex-based search/replace."""
    params = SafeEditInput(
        path=str(search_replace_file),
        search_replace=SearchReplace(search=r"Hello \w+", replace="Greetings", regex=True),
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "✅ File saved successfully" in text

    # Verify regex replacement
    content = search_replace_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "Greetings"
    assert lines[1] == "Greetings"


@pytest.mark.asyncio
async def test_search_replace_pattern_not_found_strict(safe_edit_tool, search_replace_file):
    """Test that pattern not found in strict mode returns error."""
    params = SafeEditInput(
        path=str(search_replace_file),
        search_replace=SearchReplace(search="nonexistent", replace="replacement"),
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)

    assert result.is_error
    text = get_text_content(result)
    assert "not found" in text.lower()


@pytest.mark.asyncio
async def test_search_replace_invalid_regex(safe_edit_tool, search_replace_file):
    """Test that invalid regex pattern is rejected."""
    params = SafeEditInput(
        path=str(search_replace_file),
        search_replace=SearchReplace(search="[invalid(", replace="test", regex=True),
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)

    assert result.is_error
    text = get_text_content(result)
    assert "regex" in text.lower() or "pattern" in text.lower()


# --- Insert Lines Tests (RED PHASE) ---

@pytest.mark.asyncio
async def test_insert_line_at_beginning(safe_edit_tool, multiline_file):
    """Test inserting a line at the beginning of file."""
    params = SafeEditInput(
        path=str(multiline_file),
        insert_lines=[InsertLine(at_line=1, content="# Header comment\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "✅ File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "# Header comment"
    assert lines[1] == "Line 1"
    assert lines[2] == "Line 2"


@pytest.mark.asyncio
async def test_insert_line_in_middle(safe_edit_tool, multiline_file):
    """Test inserting a line in the middle of file."""
    params = SafeEditInput(
        path=str(multiline_file),
        insert_lines=[InsertLine(at_line=3, content="# Inserted line\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "✅ File saved successfully" in text

    # Verify file content - inserted before line 3
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "Line 1"
    assert lines[1] == "Line 2"
    assert lines[2] == "# Inserted line"
    assert lines[3] == "Line 3"
    assert lines[4] == "Line 4"


@pytest.mark.asyncio
async def test_insert_line_at_end(safe_edit_tool, multiline_file):
    """Test inserting a line at the end of file."""
    params = SafeEditInput(
        path=str(multiline_file),
        insert_lines=[InsertLine(at_line=6, content="# Footer comment\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "✅ File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[5] == "# Footer comment"


@pytest.mark.asyncio
async def test_insert_multiple_lines(safe_edit_tool, multiline_file):
    """Test inserting multiple lines at different positions."""
    params = SafeEditInput(
        path=str(multiline_file),
        insert_lines=[
            InsertLine(at_line=2, content="# Comment after Line 1\n"),
            InsertLine(at_line=5, content="# Comment before Line 4\n"),
        ],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "✅ File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "Line 1"
    assert lines[1] == "# Comment after Line 1"
    assert lines[2] == "Line 2"
    assert lines[3] == "Line 3"
    assert lines[4] == "# Comment before Line 4"
    assert lines[5] == "Line 4"


@pytest.mark.asyncio
async def test_insert_line_out_of_bounds(safe_edit_tool, multiline_file):
    """Test that out-of-bounds insert is rejected."""
    params = SafeEditInput(
        path=str(multiline_file),
        insert_lines=[InsertLine(at_line=100, content="Too far\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)

    assert result.is_error
    text = get_text_content(result)
    assert "out of bounds" in text.lower()


@pytest.mark.asyncio
async def test_insert_line_on_new_file_rejected(safe_edit_tool):
    """Test that inserts on non-existent files are rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        new_file = Path(tmpdir) / "nonexistent.txt"

        params = SafeEditInput(
            path=str(new_file),
            insert_lines=[InsertLine(at_line=1, content="New line\n")],
            mode="strict"
        )

        result = await safe_edit_tool.execute(params)

        assert result.is_error
        text = get_text_content(result)
        assert "non-existent" in text.lower()
