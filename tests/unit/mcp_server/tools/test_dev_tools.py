"""Tests for Test and Code tools."""
import pytest
from unittest.mock import patch, AsyncMock, Mock
from mcp_server.tools.test_tools import RunTestsTool
from mcp_server.tools.code_tools import CreateFileTool

@pytest.mark.asyncio
async def test_run_tests_tool():
    tool = RunTestsTool()

    with patch("mcp_server.tools.test_tools._run_pytest_sync") as mock_run:
        # Mock the sync function that runs in thread pool
        mock_run.return_value = ("Tests passed", "", 0)

        result = await tool.execute(path="tests/unit")

        assert "Tests passed" in result.content[0]["text"]
        mock_run.assert_called_once()
        # Check that pytest and path are in the command
        call_args = mock_run.call_args[0]
        cmd = call_args[0]
        assert any("pytest" in str(arg) for arg in cmd)
        assert "tests/unit" in cmd

@pytest.mark.asyncio
async def test_create_file_tool(tmp_path, monkeypatch):
    # Mock workspace root to tmp_path
    monkeypatch.setattr("mcp_server.config.settings.settings.server.workspace_root", str(tmp_path))

    tool = CreateFileTool()

    await tool.execute(path="new_dir/test.txt", content="hello world")

    file_path = tmp_path / "new_dir/test.txt"
    assert file_path.exists()
    assert file_path.read_text() == "hello world"

@pytest.mark.asyncio
async def test_create_file_security_check(tmp_path, monkeypatch):
    monkeypatch.setattr("mcp_server.config.settings.settings.server.workspace_root", str(tmp_path))

    tool = CreateFileTool()

    from mcp_server.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        await tool.execute(path="../outside.txt", content="bad")
