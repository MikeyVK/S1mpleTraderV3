"""Tests for Test and Code tools."""
from unittest.mock import patch

import pytest

from mcp_server.core.exceptions import ValidationError
from mcp_server.tools.code_tools import CreateFileTool, CreateFileInput
from mcp_server.tools.test_tools import RunTestsTool, RunTestsInput


@pytest.mark.asyncio
async def test_run_tests_tool() -> None:
    """Test RunTestsTool executes pytest and returns output."""
    tool = RunTestsTool()

    with patch("mcp_server.tools.test_tools._run_pytest_sync") as mock_run:
        # Mock the sync function that runs in thread pool
        mock_run.return_value = ("Tests passed", "", 0)

        result = await tool.execute(RunTestsInput(path="tests/unit"))

        assert "Tests passed" in result.content[0]["text"]
        mock_run.assert_called_once()
        # Check that pytest and path are in the command
        call_args = mock_run.call_args[0]
        cmd = call_args[0]
        assert any("pytest" in str(arg) for arg in cmd)
        assert "tests/unit" in cmd

@pytest.mark.asyncio
async def test_create_file_tool(tmp_path, monkeypatch) -> None:
    """Test CreateFileTool creates file with correct content in subdirectory."""
    # Mock workspace root to tmp_path
    monkeypatch.setattr("mcp_server.config.settings.settings.server.workspace_root", str(tmp_path))

    tool = CreateFileTool()

    await tool.execute(CreateFileInput(path="new_dir/test.txt", content="hello world"))

    file_path = tmp_path / "new_dir/test.txt"
    assert file_path.exists()
    assert file_path.read_text() == "hello world"

@pytest.mark.asyncio
async def test_create_file_security_check(tmp_path, monkeypatch) -> None:
    """Test CreateFileTool rejects path traversal attempts."""
    monkeypatch.setattr("mcp_server.config.settings.settings.server.workspace_root", str(tmp_path))

    tool = CreateFileTool()

    with pytest.raises(ValidationError):
        await tool.execute(CreateFileInput(path="../outside.txt", content="bad"))
