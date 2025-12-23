# tests/unit/mcp_server/tools/test_safe_edit_tool.py
# pylint: disable=redefined-outer-name
"""Tests for SafeEditTool."""
import tempfile
from pathlib import Path

import pytest

from mcp_server.tools.safe_edit_tool import SafeEditInput, SafeEditTool, LineEdit


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
