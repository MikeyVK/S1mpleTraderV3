"""Tests for Test and Code tools."""
import pytest
from unittest.mock import patch, Mock
from mcp_server.tools.test_tools import RunTestsTool
from mcp_server.tools.code_tools import CreateFileTool

@pytest.mark.asyncio
async def test_run_tests_tool():
    tool = RunTestsTool()

    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.stdout = "Tests passed"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = await tool.execute(path="tests/unit")

        assert "Tests passed" in result.content[0]["text"]
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "pytest" in args
        assert "tests/unit" in args

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
