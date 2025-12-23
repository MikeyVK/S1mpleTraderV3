# tests/unit/mcp_server/tools/test_safe_edit_tool.py
# pylint: disable=redefined-outer-name
"""Tests for SafeEditTool."""
import tempfile
from pathlib import Path

import pytest

from mcp_server.tools.safe_edit_tool import SafeEditInput, SafeEditTool


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


def get_text_content(result):
    """Extract text content from ToolResult."""
    return result.content[0]["text"]


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
