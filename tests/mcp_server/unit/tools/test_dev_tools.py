"""Tests for Test and Code tools."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pytest import MonkeyPatch

from mcp_server.tools.code_tools import CreateFileInput, CreateFileTool
from mcp_server.tools.test_tools import RunTestsInput, RunTestsTool


@pytest.mark.asyncio
async def test_run_tests_tool() -> None:
    """Test RunTestsTool executes pytest and returns output."""

    tool = RunTestsTool()

    with patch("mcp_server.tools.test_tools._run_pytest_sync") as mock_run:
        mock_run.return_value = ("Tests passed", "", 0)

        result = await tool.execute(RunTestsInput(path="tests/unit"))

        assert "Tests passed" in result.content[0]["text"]
        mock_run.assert_called_once()

        call_args = mock_run.call_args[0]
        cmd = call_args[0]
        assert any("pytest" in str(arg) for arg in cmd)
        assert "tests/unit" in cmd


@pytest.mark.asyncio
async def test_create_file_tool(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test CreateFileTool creates file with correct content in subdirectory."""

    monkeypatch.setattr("mcp_server.config.settings.settings.server.workspace_root", str(tmp_path))

    tool = CreateFileTool()

    await tool.execute(CreateFileInput(path="new_dir/test.txt", content="hello world"))

    file_path = tmp_path / "new_dir/test.txt"
    assert file_path.exists()
    assert file_path.read_text() == "hello world"


@pytest.mark.asyncio
async def test_create_file_security_check(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Test CreateFileTool rejects path traversal attempts."""

    monkeypatch.setattr("mcp_server.config.settings.settings.server.workspace_root", str(tmp_path))

    tool = CreateFileTool()

    result = await tool.execute(CreateFileInput(path="../outside.txt", content="bad"))

    assert result.is_error
    assert "Access denied" in result.content[0]["text"]
