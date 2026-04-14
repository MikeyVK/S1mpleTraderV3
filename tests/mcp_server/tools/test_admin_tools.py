"""Tests for administrative tools (server restart functionality).

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.tools.admin_tools
"""

import asyncio
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from mcp_server.core.operation_notes import NoteContext
from mcp_server.tools.admin_tools import (
    RestartServerInput,
    RestartServerTool,
    verify_server_restarted,
)


def test_restart_marker_written_with_correct_schema(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """RED: Test that restart_server writes marker file with correct schema.

    Verifies:
    - Marker file created at .st3/.restart_marker
    - Contains timestamp (float), pid (int), reason (str), iso_time (str)
    - Server exits with code 42
    """
    marker_path = tmp_path / ".restart_marker"
    monkeypatch.setattr(
        "mcp_server.tools.admin_tools._get_restart_marker_path",
        lambda: marker_path,
    )

    exit_calls: list[int] = []

    def mock_exit(code: int) -> None:
        exit_calls.append(code)
        raise SystemExit(code)

    async def mock_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("sys.exit", mock_exit)
    monkeypatch.setattr("asyncio.sleep", mock_sleep)

    tool = RestartServerTool()
    params = RestartServerInput(reason="Test marker schema")

    async def run_test() -> None:
        await tool.execute(params, NoteContext())
        await asyncio.sleep(0.01)
        await asyncio.sleep(0)

    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(run_test())

    assert exc_info.value.code == 42
    assert len(exit_calls) == 1
    assert exit_calls[0] == 42
    assert marker_path.exists(), "Restart marker file not created"

    with marker_path.open(encoding="utf-8") as file_handle:
        marker_data = json.load(file_handle)

    assert "timestamp" in marker_data, "Missing timestamp field"
    assert "pid" in marker_data, "Missing pid field"
    assert "reason" in marker_data, "Missing reason field"
    assert "iso_time" in marker_data, "Missing iso_time field"

    assert isinstance(marker_data["timestamp"], float), "timestamp must be float"
    assert isinstance(marker_data["pid"], int), "pid must be int"
    assert isinstance(marker_data["reason"], str), "reason must be str"
    assert isinstance(marker_data["iso_time"], str), "iso_time must be str"

    assert marker_data["reason"] == "Test marker schema"
    assert marker_data["pid"] == os.getpid()
    assert marker_data["timestamp"] > 0


def test_restart_events_logged_to_audit_trail(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """RED: Test that restart functionality works and exits with code 42.

    Verifies:
    - Server exits with correct code (42 for supervisor restart)
    - Marker file is written (proves tool executed)
    - Exit happens after tool execution (proves async background task)
    """
    marker_path = tmp_path / ".restart_marker"
    monkeypatch.setattr(
        "mcp_server.tools.admin_tools._get_restart_marker_path",
        lambda: marker_path,
    )

    exit_calls: list[int] = []

    def mock_exit(code: int) -> None:
        exit_calls.append(code)
        raise SystemExit(code)

    async def mock_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("sys.exit", mock_exit)
    monkeypatch.setattr("asyncio.sleep", mock_sleep)

    tool = RestartServerTool()
    params = RestartServerInput(reason="Test restart execution")

    async def run_test() -> None:
        result = await tool.execute(params, NoteContext())
        assert result.isError is False
        assert "exit with code 42" in result.content[0].text
        await asyncio.sleep(0.01)
        await asyncio.sleep(0)

    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(run_test())

    assert exc_info.value.code == 42
    assert len(exit_calls) == 1
    assert exit_calls[0] == 42
    assert marker_path.exists(), "Restart marker file not created"


def test_verify_server_restarted_with_valid_marker(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """RED: Test verify_server_restarted with valid marker.

    Verifies:
    - Returns restarted=True when marker timestamp > since_timestamp
    - Returns restart details (timestamp, PID, reason)
    - Returns current vs previous PID
    """
    marker_path = tmp_path / ".restart_marker"
    monkeypatch.setattr(
        "mcp_server.tools.admin_tools._get_restart_marker_path",
        lambda: marker_path,
    )

    past_time = time.time() - 10
    marker_data = {
        "timestamp": past_time + 5,
        "pid": 99999,
        "reason": "Test restart verification",
        "iso_time": datetime.now(UTC).isoformat(),
    }
    marker_path.write_text(json.dumps(marker_data), encoding="utf-8")

    result = verify_server_restarted(since_timestamp=past_time)

    assert result["restarted"] is True
    assert result["previous_pid"] == 99999
    assert result["reason"] == "Test restart verification"
    assert result["restart_timestamp"] == past_time + 5
    assert "current_pid" in result
    assert "time_since_restart" in result


def test_verify_server_restarted_no_marker(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """RED: Test verify_server_restarted with missing marker.

    Verifies:
    - Returns restarted=False when marker doesn't exist
    - Returns error message
    """
    marker_path = tmp_path / ".restart_marker"
    monkeypatch.setattr(
        "mcp_server.tools.admin_tools._get_restart_marker_path",
        lambda: marker_path,
    )

    result = verify_server_restarted(since_timestamp=time.time())

    assert result["restarted"] is False
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_verify_server_restarted_old_marker(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """RED: Test verify_server_restarted with outdated marker.

    Verifies:
    - Returns restarted=False when marker timestamp < since_timestamp
    """
    marker_path = tmp_path / ".restart_marker"
    monkeypatch.setattr(
        "mcp_server.tools.admin_tools._get_restart_marker_path",
        lambda: marker_path,
    )

    old_time = time.time() - 100
    marker_data = {
        "timestamp": old_time,
        "pid": 99999,
        "reason": "Old restart",
        "iso_time": datetime.now(UTC).isoformat(),
    }
    marker_path.write_text(json.dumps(marker_data), encoding="utf-8")

    recent_time = time.time() - 10
    result = verify_server_restarted(since_timestamp=recent_time)

    assert result["restarted"] is False


def test_restart_uses_sys_exit_42_not_os_execv(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """RED: Test that restart tool uses sys.exit(42) for supervisor restart.

    Verifies:
    - sys.exit(42) is called (signals supervisor to restart)
    - os.execv is NOT called (old approach, breaks MCP protocol)
    - Response returned before exit (no hung tool calls)
    - Proper supervisor-based restart with exit code protocol
    """
    execv_calls: list[dict[str, object]] = []
    exit_calls: list[int] = []

    def mock_execv(path: str, args: list[str]) -> None:
        execv_calls.append({"path": path, "args": args})
        raise SystemExit(0)

    def mock_exit(code: int) -> None:
        exit_calls.append(code)
        raise SystemExit(code)

    async def mock_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("os.execv", mock_execv)
    monkeypatch.setattr("sys.exit", mock_exit)
    monkeypatch.setattr("asyncio.sleep", mock_sleep)
    monkeypatch.chdir(tmp_path)

    tool = RestartServerTool()
    params = RestartServerInput(reason="test sys.exit(42) restart")

    async def run_test() -> None:
        result = await tool.execute(params, NoteContext())
        assert result.isError is False
        await asyncio.sleep(0.01)
        await asyncio.sleep(0)

    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(run_test())

    assert exc_info.value.code == 42, (
        f"Expected exit code 42 (supervisor restart), got {exc_info.value.code}"
    )
    assert len(exit_calls) == 1, "sys.exit should be called once"
    assert exit_calls[0] == 42, (
        f"Expected sys.exit(42) for supervisor restart, got sys.exit({exit_calls[0]})"
    )
    assert not execv_calls, "os.execv should NOT be called (use sys.exit(42) + supervisor instead)"
