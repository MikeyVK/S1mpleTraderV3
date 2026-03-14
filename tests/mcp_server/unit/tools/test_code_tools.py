"""Unit tests for code_tools.py."""

from pathlib import Path

import pytest

from mcp_server.config.settings import Settings
from mcp_server.tools.code_tools import CreateFileInput, CreateFileTool


@pytest.mark.asyncio
async def test_create_file_tool_success(tmp_path: Path) -> None:
    tool = CreateFileTool(settings=Settings(server={"workspace_root": str(tmp_path)}))
    params = CreateFileInput(path="test.txt", content="hello")

    result = await tool.execute(params)

    assert "File created: test.txt" in result.content[0]["text"]
    assert (tmp_path / "test.txt").read_text(encoding="utf-8") == "hello"


@pytest.mark.asyncio
async def test_create_file_tool_security_error(tmp_path: Path) -> None:
    tool = CreateFileTool(settings=Settings(server={"workspace_root": str(tmp_path)}))
    params = CreateFileInput(path="../outside.txt", content="bad")

    result = await tool.execute(params)

    assert result.is_error
    assert "Access denied" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_create_file_tool_deprecation_warning(tmp_path: Path) -> None:
    tool = CreateFileTool(settings=Settings(server={"workspace_root": str(tmp_path)}))
    params = CreateFileInput(path="test.txt", content="hello")

    with pytest.warns(DeprecationWarning, match="create_file is deprecated"):
        await tool.execute(params)
