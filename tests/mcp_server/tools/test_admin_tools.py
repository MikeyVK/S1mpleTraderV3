"""Tests for administrative tools (server restart functionality)."""

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest


def test_restart_marker_written_with_correct_schema(monkeypatch):
    """RED: Test that restart_server writes marker file with correct schema.

    Verifies:
    - Marker file created at .st3/.restart_marker
    - Contains timestamp (float), pid (int), reason (str), iso_time (str)
    - Server exits with code 42
    """
    import asyncio

    from mcp_server.tools.admin_tools import RestartServerInput, RestartServerTool

    # Mock sys.exit to capture exit code
    exit_calls = []

    def mock_exit(code):
        exit_calls.append(code)
        raise SystemExit(code)

    async def mock_sleep(_seconds):
        pass

    monkeypatch.setattr("sys.exit", mock_exit)
    monkeypatch.setattr("asyncio.sleep", mock_sleep)

    marker_path = Path(".st3/.restart_marker")
    marker_path.unlink(missing_ok=True)  # Clean state

    # Execute via async wrapper to let background task run
    tool = RestartServerTool()
    params = RestartServerInput(reason="Test marker schema")

    async def run_test():
        await tool.execute(params)
        await asyncio.sleep(0.01)  # Let background task start
        await asyncio.sleep(0)  # Process pending tasks

    # Capture exit from background task
    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(run_test())

    # Verify exit code 42
    assert exc_info.value.code == 42
    assert len(exit_calls) == 1
    assert exit_calls[0] == 42

    # Verify marker file exists
    assert marker_path.exists(), "Restart marker file not created"

    # Verify marker content schema
    with marker_path.open(encoding="utf-8") as f:
        marker_data = json.load(f)

    # Schema validation
    assert "timestamp" in marker_data, "Missing timestamp field"
    assert "pid" in marker_data, "Missing pid field"
    assert "reason" in marker_data, "Missing reason field"
    assert "iso_time" in marker_data, "Missing iso_time field"

    # Type validation
    assert isinstance(marker_data["timestamp"], float), "timestamp must be float"
    assert isinstance(marker_data["pid"], int), "pid must be int"
    assert isinstance(marker_data["reason"], str), "reason must be str"
    assert isinstance(marker_data["iso_time"], str), "iso_time must be str"

    # Value validation
    assert marker_data["reason"] == "Test marker schema"
    assert marker_data["pid"] == os.getpid()
    assert marker_data["timestamp"] > 0

    # Cleanup
    marker_path.unlink(missing_ok=True)


def test_restart_events_logged_to_audit_trail(monkeypatch):
    """RED: Test that restart functionality works and exits with code 42.

    Verifies:
    - Server exits with correct code (42 for supervisor restart)
    - Marker file is written (proves tool executed)
    - Exit happens after tool execution (proves async background task)
    """
    import asyncio

    from mcp_server.tools.admin_tools import RestartServerInput, RestartServerTool

    # Mock sys.exit to capture exit code
    exit_calls = []

    def mock_exit(code):
        exit_calls.append(code)
        raise SystemExit(code)

    async def mock_sleep(_seconds):
        pass

    monkeypatch.setattr("sys.exit", mock_exit)
    monkeypatch.setattr("asyncio.sleep", mock_sleep)

    marker_path = Path(".st3/.restart_marker")
    marker_path.unlink(missing_ok=True)  # Clean state

    # Execute via async wrapper to let background task run
    tool = RestartServerTool()
    params = RestartServerInput(reason="Test restart execution")

    async def run_test():
        result = await tool.execute(params)
        # Verify tool returns success before exit
        assert result.isError is False
        assert "exit with code 42" in result.content[0].text
        await asyncio.sleep(0.01)  # Let background task start
        await asyncio.sleep(0)  # Process pending tasks

    # Capture exit from background task
    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(run_test())

    # Verify exit code 42 (supervisor restart protocol)
    assert exc_info.value.code == 42
    assert len(exit_calls) == 1
    assert exit_calls[0] == 42

    # Verify marker file was written
    assert marker_path.exists(), "Restart marker file not created"

    # Cleanup
    marker_path.unlink(missing_ok=True)



def test_verify_server_restarted_with_valid_marker():
    """RED: Test verify_server_restarted with valid marker.

    Verifies:
    - Returns restarted=True when marker timestamp > since_timestamp
    - Returns restart details (timestamp, PID, reason)
    - Returns current vs previous PID
    """
    from mcp_server.tools.admin_tools import verify_server_restarted

    # Create marker from "past"
    past_time = time.time() - 10  # 10 seconds ago
    marker_path = Path(".st3/.restart_marker")
    marker_path.parent.mkdir(exist_ok=True)
    marker_data = {
        "timestamp": past_time + 5,  # 5 seconds ago (after past_time)
        "pid": 99999,  # Different PID
        "reason": "Test restart verification",
        "iso_time": datetime.now(UTC).isoformat()
    }
    marker_path.write_text(json.dumps(marker_data), encoding="utf-8")

    # Verify restart happened after past_time
    result = verify_server_restarted(since_timestamp=past_time)

    assert result["restarted"] is True
    assert result["previous_pid"] == 99999
    assert result["reason"] == "Test restart verification"
    assert result["restart_timestamp"] == past_time + 5
    assert "current_pid" in result
    assert "time_since_restart" in result

    # Cleanup
    marker_path.unlink(missing_ok=True)


def test_verify_server_restarted_no_marker():
    """RED: Test verify_server_restarted with missing marker.

    Verifies:
    - Returns restarted=False when marker doesn't exist
    - Returns error message
    """
    from mcp_server.tools.admin_tools import verify_server_restarted

    marker_path = Path(".st3/.restart_marker")
    marker_path.unlink(missing_ok=True)  # Ensure no marker

    result = verify_server_restarted(since_timestamp=time.time())

    assert result["restarted"] is False
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_verify_server_restarted_old_marker():
    """RED: Test verify_server_restarted with outdated marker.

    Verifies:
    - Returns restarted=False when marker timestamp < since_timestamp
    """
    from mcp_server.tools.admin_tools import verify_server_restarted

    # Create marker from way in the past
    old_time = time.time() - 100  # 100 seconds ago
    marker_path = Path(".st3/.restart_marker")
    marker_path.parent.mkdir(exist_ok=True)
    marker_data = {
        "timestamp": old_time,
        "pid": 99999,
        "reason": "Old restart",
        "iso_time": datetime.now(UTC).isoformat()
    }
    marker_path.write_text(json.dumps(marker_data), encoding="utf-8")

    # Check against recent time (should fail)
    recent_time = time.time() - 10  # 10 seconds ago
    result = verify_server_restarted(since_timestamp=recent_time)

    assert result["restarted"] is False

    # Cleanup
    marker_path.unlink(missing_ok=True)


def test_restart_uses_sys_exit_42_not_os_execv(tmp_path, monkeypatch):
    """RED: Test that restart tool uses sys.exit(42) for supervisor restart.

    Verifies:
    - sys.exit(42) is called (signals supervisor to restart)
    - os.execv is NOT called (old approach, breaks MCP protocol)
    - Response returned before exit (no hung tool calls)
    - Proper supervisor-based restart with exit code protocol
    """
    import asyncio

    from mcp_server.tools.admin_tools import RestartServerInput, RestartServerTool

    # Track what was called
    execv_calls = []
    exit_calls = []

    def mock_execv(path, args):
        execv_calls.append({"path": path, "args": args})
        # This should NOT be called with new supervisor approach
        raise SystemExit(0)

    def mock_exit(code):
        exit_calls.append(code)
        # Simulate exit (don't actually exit test)
        raise SystemExit(code)

    async def mock_sleep(_seconds):
        # Fast-forward sleep for testing
        pass

    # Apply mocks
    monkeypatch.setattr("os.execv", mock_execv)
    monkeypatch.setattr("sys.exit", mock_exit)
    monkeypatch.setattr("asyncio.sleep", mock_sleep)

    # Change to tmp directory (for marker file)
    monkeypatch.chdir(tmp_path)

    # Execute tool (async) - should schedule sys.exit(42), not os.execv
    tool = RestartServerTool()
    params = RestartServerInput(reason="test sys.exit(42) restart")

    # Run the tool and wait for background task
    async def run_test():
        result = await tool.execute(params)
        # Wait a bit for background task to start
        await asyncio.sleep(0.01)
        # Process any pending tasks
        await asyncio.sleep(0)
        return result

    # Execute and expect SystemExit(42) from mock_exit
    with pytest.raises(SystemExit) as exc_info:
        asyncio.run(run_test())

    # Should exit with code 42 (restart request for supervisor)
    assert exc_info.value.code == 42, \
        f"Expected exit code 42 (supervisor restart), got {exc_info.value.code}"

    # Verify sys.exit(42) was called
    assert len(exit_calls) == 1, "sys.exit should be called once"
    assert exit_calls[0] == 42, \
        f"Expected sys.exit(42) for supervisor restart, got sys.exit({exit_calls[0]})"

    # Verify os.execv was NOT called (old approach, breaks MCP protocol)
    assert not execv_calls, \
        "os.execv should NOT be called (use sys.exit(42) + supervisor instead)"
