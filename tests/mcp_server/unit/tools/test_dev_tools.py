"""Tests for Test and Code tools.

@layer: Tests (Unit)
@dependencies: [pytest, pathlib, mcp_server.tools.test_tools]
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.config.settings import Settings
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.pytest_runner import PytestResult
from mcp_server.tools.code_tools import CreateFileInput, CreateFileTool
from mcp_server.tools.test_tools import RunTestsInput, RunTestsTool
from tests.mcp_server.fixtures.fake_pytest_runner import FakePytestRunner


@pytest.mark.asyncio
async def test_run_tests_tool(tmp_path: Path) -> None:
    """Test RunTestsTool executes pytest and returns JSON output."""
    runner = FakePytestRunner(
        result=PytestResult(
            exit_code=0,
            summary_line="2 passed in 0.10s",
            passed=2,
            failed=0,
            skipped=0,
            errors=0,
            failures=(),
            coverage_pct=None,
            lf_cache_was_empty=False,
            should_raise=False,
            note=None,
        )
    )
    tool = RunTestsTool(runner=runner, settings=Settings(server={"workspace_root": str(tmp_path)}))

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    assert result.content[0]["type"] == "text"
    assert result.content[1]["json"]["summary"]["passed"] == 2
    assert runner.captured_cmd is not None
    assert any("pytest" in str(arg) for arg in runner.captured_cmd)
    assert "tests/unit" in runner.captured_cmd


@pytest.mark.asyncio
async def test_create_file_tool(tmp_path: Path) -> None:
    """Test CreateFileTool creates file with correct content in subdirectory."""
    tool = CreateFileTool(settings=Settings(server={"workspace_root": str(tmp_path)}))

    await tool.execute(
        CreateFileInput(path="new_dir/test.txt", content="hello world"), NoteContext()
    )

    file_path = tmp_path / "new_dir/test.txt"
    assert file_path.exists()
    assert file_path.read_text() == "hello world"


@pytest.mark.asyncio
async def test_create_file_security_check(tmp_path: Path) -> None:
    """Test CreateFileTool rejects path traversal attempts."""
    tool = CreateFileTool(settings=Settings(server={"workspace_root": str(tmp_path)}))

    result = await tool.execute(
        CreateFileInput(path="../outside.txt", content="bad"), NoteContext()
    )

    assert result.is_error
    assert "Access denied" in result.content[0]["text"]
