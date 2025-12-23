# tests/unit/mcp_server/tools/test_safe_edit_tool.py
"""Tests for SafeEditTool."""
import tempfile
from pathlib import Path

import pytest

from mcp_server.tools.safe_edit_tool import (
    LineEdit,
    InsertLine,
    SafeEditInput,
    SafeEditTool,
    SearchReplace,
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
        f.write("Hello World\n")

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

    # Should contain diff markers
    assert "**Diff Preview:**" in text
    assert "```diff" in text
    assert "-Hello World" in text
    assert "+New content" in text


@pytest.mark.asyncio
async def test_diff_preview_can_be_disabled(safe_edit_tool, temp_file):
    """Test that diff preview can be disabled."""
    params = SafeEditInput(
        path=str(temp_file),
        content="New content\n",
        mode="strict",
        show_diff=False
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    # Should NOT contain diff
    assert "**Diff Preview:**" not in text
    assert "```diff" not in text


@pytest.mark.asyncio
async def test_diff_preview_empty_when_no_changes(safe_edit_tool, temp_file):
    """Test that diff preview is empty when there are no changes."""
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

    # Should mention success but no diff shown (empty diff)
    assert "âœ… File saved successfully" in text
    # Diff section should not appear if no changes
    assert "**Diff Preview:**" not in text or "```diff\n\n```" in text


@pytest.mark.asyncio
async def test_diff_preview_for_new_file(safe_edit_tool):
    """Test that diff preview works for new files (no original content)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        new_file_path = Path(tmpdir) / "new_file.txt"

        params = SafeEditInput(
            path=str(new_file_path),
            content="New file content\n",
            mode="strict",
            show_diff=True
        )

        result = await safe_edit_tool.execute(params)
        text = get_text_content(result)

        # Should show diff adding content
        assert "**Diff Preview:**" in text
        assert "```diff" in text
        assert "+New file content" in text

        # Verify file was created
        assert new_file_path.exists()
        assert new_file_path.read_text() == "New file content\n"


@pytest.mark.asyncio
async def test_diff_preview_in_verify_only_mode(safe_edit_tool, temp_file):
    """Test that diff preview is shown in verify_only mode without writing."""
    params = SafeEditInput(
        path=str(temp_file),
        content="New content\n",
        mode="verify_only",
        show_diff=True
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    # Should show diff
    assert "**Diff Preview:**" in text
    assert "-Hello World" in text
    assert "+New content" in text

    # Should indicate validation passed
    assert "âœ… Validation Passed" in text

    # File should NOT be modified
    assert temp_file.read_text() == "Hello World\n"


# --- Line Edit Tests ---

@pytest.mark.asyncio
async def test_line_edit_single_line(safe_edit_tool, multiline_file):
    """Test editing a single line."""
    params = SafeEditInput(
        path=str(multiline_file),
        line_edits=[LineEdit(start_line=3, end_line=3, new_content="Modified Line 3\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "âœ… File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "Line 1"
    assert lines[1] == "Line 2"
    assert lines[2] == "Modified Line 3"
    assert lines[3] == "Line 4"
    assert lines[4] == "Line 5"


@pytest.mark.asyncio
async def test_line_edit_multiple_non_overlapping(safe_edit_tool, multiline_file):
    """Test editing multiple non-overlapping lines."""
    params = SafeEditInput(
        path=str(multiline_file),
        line_edits=[
            LineEdit(start_line=1, end_line=1, new_content="Modified Line 1\n"),
            LineEdit(start_line=5, end_line=5, new_content="Modified Line 5\n"),
        ],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "âœ… File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "Modified Line 1"
    assert lines[1] == "Line 2"
    assert lines[2] == "Line 3"
    assert lines[3] == "Line 4"
    assert lines[4] == "Modified Line 5"


@pytest.mark.asyncio
async def test_line_edit_range(safe_edit_tool, multiline_file):
    """Test editing a range of lines."""
    params = SafeEditInput(
        path=str(multiline_file),
        line_edits=[LineEdit(start_line=2, end_line=4, new_content="Merged Lines 2-4\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "âœ… File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "Line 1"
    assert lines[1] == "Merged Lines 2-4"
    assert lines[2] == "Line 5"


@pytest.mark.asyncio
async def test_line_edit_out_of_bounds(safe_edit_tool, multiline_file):
    """Test that out of bounds line edits are rejected."""
    params = SafeEditInput(
        path=str(multiline_file),
        line_edits=[LineEdit(start_line=10, end_line=10, new_content="Invalid\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "Line edit failed:" in text
    assert "out of bounds" in text


@pytest.mark.asyncio
async def test_line_edit_overlapping_ranges_rejected(safe_edit_tool, multiline_file):
    """Test that overlapping line edits are rejected."""
    params = SafeEditInput(
        path=str(multiline_file),
        line_edits=[
            LineEdit(start_line=2, end_line=4, new_content="Range 1\n"),
            LineEdit(start_line=3, end_line=5, new_content="Range 2\n"),
        ],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "Line edit failed:" in text
    assert "Overlapping edits detected" in text


@pytest.mark.asyncio
async def test_line_edit_on_new_file_rejected(safe_edit_tool):
    """Test that line edits on non-existent files are rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent_file = Path(tmpdir) / "does_not_exist.txt"

        params = SafeEditInput(
            path=str(non_existent_file),
            line_edits=[LineEdit(start_line=1, end_line=1, new_content="Content\n")],
            mode="strict"
        )

        result = await safe_edit_tool.execute(params)
        text = get_text_content(result)

        assert "Cannot apply line edits to non-existent file" in text


# --- Search/Replace Tests ---

@pytest.mark.asyncio
async def test_search_replace_literal(safe_edit_tool, search_replace_file):
    """Test literal search and replace."""
    params = SafeEditInput(
        path=str(search_replace_file),
        search_replace=SearchReplace(search="Hello", replace="Hi", regex=False),
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "âœ… File saved successfully" in text

    # Verify file content
    content = search_replace_file.read_text()
    assert "Hi world" in content
    assert "Hi Python" in content
    assert "Goodbye world" in content


@pytest.mark.asyncio
async def test_search_replace_with_count_limit(safe_edit_tool, search_replace_file):
    """Test search and replace with count limit."""
    params = SafeEditInput(
        path=str(search_replace_file),
        search_replace=SearchReplace(search="Hello", replace="Hi", regex=False, count=1),
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "âœ… File saved successfully" in text

    # Verify only one replacement
    content = search_replace_file.read_text()
    assert content.count("Hi") == 1
    assert content.count("Hello") == 1  # One remains


@pytest.mark.asyncio
async def test_search_replace_regex(safe_edit_tool, search_replace_file):
    """Test regex search and replace."""
    params = SafeEditInput(
        path=str(search_replace_file),
        search_replace=SearchReplace(
            search=r"Hello (\w+)",
            replace=r"Greetings \1",
            regex=True
        ),
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "âœ… File saved successfully" in text

    # Verify file content
    content = search_replace_file.read_text()
    assert "Greetings world" in content
    assert "Greetings Python" in content
    assert "Goodbye world" in content


@pytest.mark.asyncio
async def test_search_replace_pattern_not_found(safe_edit_tool, search_replace_file):
    """Test that pattern not found is handled in strict mode."""
    params = SafeEditInput(
        path=str(search_replace_file),
        search_replace=SearchReplace(search="NonExistent", replace="Something", regex=False),
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "Pattern 'NonExistent' not found in file" in text


@pytest.mark.asyncio
async def test_search_replace_invalid_regex(safe_edit_tool, search_replace_file):
    """Test that invalid regex is rejected."""
    params = SafeEditInput(
        path=str(search_replace_file),
        search_replace=SearchReplace(search="[invalid(", replace="Something", regex=True),
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "Search/replace failed:" in text
    assert "Invalid regex pattern" in text


# --- Insert Lines Tests ---

@pytest.mark.asyncio
async def test_insert_line_at_beginning(safe_edit_tool, multiline_file):
    """Test inserting a line at the beginning of the file."""
    params = SafeEditInput(
        path=str(multiline_file),
        insert_lines=[InsertLine(at_line=1, content="# Header\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "âœ… File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "# Header"
    assert lines[1] == "Line 1"
    assert lines[2] == "Line 2"


@pytest.mark.asyncio
async def test_insert_line_in_middle(safe_edit_tool, multiline_file):
    """Test inserting a line in the middle of the file."""
    params = SafeEditInput(
        path=str(multiline_file),
        insert_lines=[InsertLine(at_line=3, content="# Comment\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "âœ… File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "Line 1"
    assert lines[1] == "Line 2"
    assert lines[2] == "# Comment"
    assert lines[3] == "Line 3"


@pytest.mark.asyncio
async def test_insert_line_at_end(safe_edit_tool, multiline_file):
    """Test inserting a line at the end of the file."""
    params = SafeEditInput(
        path=str(multiline_file),
        insert_lines=[InsertLine(at_line=6, content="# Footer\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "âœ… File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[5] == "# Footer"


@pytest.mark.asyncio
async def test_insert_multiple_lines(safe_edit_tool, multiline_file):
    """Test inserting multiple lines at different positions."""
    params = SafeEditInput(
        path=str(multiline_file),
        insert_lines=[
            InsertLine(at_line=2, content="# Comment after Line 1\n"),
            InsertLine(at_line=4, content="# Comment before Line 4\n"),
        ],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "âœ… File saved successfully" in text

    # Verify file content
    content = multiline_file.read_text()
    lines = content.splitlines()
    assert lines[0] == "Line 1"
    assert lines[1] == "# Comment after Line 1"
    assert lines[2] == "Line 2"
    assert lines[3] == "Line 3"
    assert lines[4] == "# Comment before Line 4"
    assert lines[5] == "Line 4"
    assert lines[6] == "Line 5"


@pytest.mark.asyncio
async def test_insert_line_out_of_bounds(safe_edit_tool, multiline_file):
    """Test that out of bounds insert is rejected."""
    params = SafeEditInput(
        path=str(multiline_file),
        insert_lines=[InsertLine(at_line=10, content="Invalid\n")],
        mode="strict"
    )

    result = await safe_edit_tool.execute(params)
    text = get_text_content(result)

    assert "Insert lines failed:" in text
    assert "out of bounds" in text


@pytest.mark.asyncio
async def test_insert_line_on_new_file_rejected(safe_edit_tool):
    """Test that insert on non-existent file is rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        non_existent_file = Path(tmpdir) / "does_not_exist.txt"

        params = SafeEditInput(
            path=str(non_existent_file),
            insert_lines=[InsertLine(at_line=1, content="Content\n")],
            mode="strict"
        )

        result = await safe_edit_tool.execute(params)
        text = get_text_content(result)

        assert "Cannot insert lines into non-existent file" in text


# --- Input Validation Tests ---

def test_no_edit_mode_specified():
    """Test that specifying no edit mode raises ValidationError."""
    with pytest.raises(ValueError, match="At least one edit mode must be specified"):
        SafeEditInput(
            path="test.py",
            mode="strict"
        )


def test_multiple_edit_modes_rejected():
    """Test that specifying multiple edit modes raises ValidationError."""
    with pytest.raises(ValueError, match="Only one edit mode can be specified"):
        SafeEditInput(
            path="test.py",
            content="New content",
            line_edits=[LineEdit(start_line=1, end_line=1, new_content="Edit")],
            mode="strict"
        )


def test_single_edit_mode_valid():
    """Test that specifying a single edit mode is valid."""
    # Should not raise - content only
    SafeEditInput(path="test.py", content="Content", mode="strict")
    
    # Should not raise - line_edits only
    SafeEditInput(
        path="test.py",
        line_edits=[LineEdit(start_line=1, end_line=1, new_content="Edit")],
        mode="strict"
    )
    
    # Should not raise - insert_lines only
    SafeEditInput(
        path="test.py",
        insert_lines=[InsertLine(at_line=1, content="Insert")],
        mode="strict"
    )
    
    # Should not raise - search_replace only
    SafeEditInput(
        path="test.py",
        search_replace=SearchReplace(search="old", replace="new"),
        mode="strict"
    )


def test_all_edit_modes_rejected():
    """Test that specifying all edit modes raises ValidationError."""
    with pytest.raises(ValueError, match="Only one edit mode can be specified"):
        SafeEditInput(
            path="test.py",
            content="Content",
            line_edits=[LineEdit(start_line=1, end_line=1, new_content="Edit")],
            insert_lines=[InsertLine(at_line=1, content="Insert")],
            search_replace=SearchReplace(search="old", replace="new"),
            mode="strict"
        )
