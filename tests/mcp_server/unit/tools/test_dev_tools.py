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
from mcp_server.tools.test_tools import RunTestsInput, RunTestsTool
from tests.mcp_server.fixtures.fake_pytest_runner import FakePytestRunner


@pytest.mark.asyncio
async def test_run_tests_tool(tmp_path: Path) -> None:
    """Test RunTestsTool executes pytest and returns JSON output."""
    runner = FakePytestRunner(
        result=PytestResult(
            exit_code=0,
            duration_seconds=0.1,
            passed=2,
            failed=0,
            skipped=0,
            errors=0,
            failures=(),
            coverage_pct=None,
            lf_cache_was_empty=False,
            should_raise=False,
            note=None,
            is_error=False,
        )
    )
    tool = RunTestsTool(runner=runner, settings=Settings(server={"workspace_root": str(tmp_path)}))

    result = await tool.execute(RunTestsInput(path="tests/unit"), NoteContext())

    if hasattr(result, "content"):
        assert result.content[1]["type"] == "text"
        assert result.content[0]["json"]["summary"]["passed"] == 2
    else:
        assert result.success is True
        assert result.passed_count == 2
    assert runner.captured_cmd is not None
    assert any("pytest" in str(arg) for arg in runner.captured_cmd)
    assert "tests/unit" in runner.captured_cmd
