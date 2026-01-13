"""Tests for administrative tools (server restart functionality)."""

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest


def test_restart_marker_written_with_correct_schema():
    """RED: Test that restart_server writes marker file with correct schema.

    Verifies:
    - Marker file created at .st3/.restart_marker
    - Contains timestamp (float), pid (int), reason (str), iso_time (str)
    - Server exits with code 42
    """
    from mcp_server.tools.admin_tools import restart_server

    marker_path = Path(".st3/.restart_marker")
    marker_path.unlink(missing_ok=True)  # Clean state

    # Capture exit
    with pytest.raises(SystemExit) as exc_info:
        restart_server(reason="Test marker schema")

    # Verify exit code 42
    assert exc_info.value.code == 42

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


def test_restart_events_logged_to_audit_trail(caplog):
    """RED: Test that restart events are logged to audit trail.

    Verifies three lifecycle events are logged:
    1. "Server restart requested" with reason, pid, timestamp
    2. "Restart marker written" with marker_path, marker_content
    3. "Server exiting for restart" with exit_code, reason
    """
    from mcp_server.tools.admin_tools import restart_server

    marker_path = Path(".st3/.restart_marker")
    marker_path.unlink(missing_ok=True)  # Clean state

    # Capture logs at INFO level
    with caplog.at_level("INFO", logger="tools.admin"):
        # Capture exit
        with pytest.raises(SystemExit) as exc_info:
            restart_server(reason="Test audit logging")

    assert exc_info.value.code == 42

    # Verify all three audit events logged
    log_messages = [record.message for record in caplog.records]

    assert "Server restart requested" in log_messages
    assert "Restart marker written" in log_messages
    assert "Server exiting for restart" in log_messages

    # Verify first event has correct extra props
    restart_requested = [r for r in caplog.records if "restart requested" in r.message][0]
    assert hasattr(restart_requested, "props")
    assert restart_requested.props["reason"] == "Test audit logging"
    assert restart_requested.props["event_type"] == "server_restart_requested"
    assert "pid" in restart_requested.props
    assert "timestamp" in restart_requested.props

    # Verify second event has marker details
    marker_written = [r for r in caplog.records if "marker written" in r.message][0]
    assert hasattr(marker_written, "props")
    assert "marker_path" in marker_written.props
    assert "marker_content" in marker_written.props

    # Verify third event has exit code
    exiting = [r for r in caplog.records if "exiting for restart" in r.message][0]
    assert hasattr(exiting, "props")
    assert exiting.props["exit_code"] == 42
    assert exiting.props["reason"] == "Test audit logging"

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


def test_restart_uses_os_execv_not_sys_exit(tmp_path, monkeypatch):
    """RED: Test that restart tool uses os.execv() instead of sys.exit().

    Verifies:
    - os.execv is called with correct Python executable and args
    - sys.exit is NOT called (replaced by execv)
    - Proper in-process restart without exit code
    """
    import sys
    from mcp_server.tools.admin_tools import restart_server

    # Track what was called
    execv_calls = []
    exit_calls = []

    def mock_execv(path, args):
        execv_calls.append({"path": path, "args": args})
        # Don't actually replace process - raise SystemExit to simulate restart
        raise SystemExit(0)

    def mock_exit(code):
        exit_calls.append(code)
        raise SystemExit(code)

    # Apply mocks
    monkeypatch.setattr("os.execv", mock_execv)
    monkeypatch.setattr("sys.exit", mock_exit)

    # Change to tmp directory (for marker file)
    monkeypatch.chdir(tmp_path)

    # Call restart - should use execv, not sys.exit
    with pytest.raises(SystemExit) as exc_info:
        restart_server("test os.execv restart")

    # Should exit cleanly (from mock_execv)
    assert not exc_info.value.code

    # Verify os.execv was called with correct arguments
    assert len(execv_calls) == 1, "os.execv should be called once"
    assert execv_calls[0]["path"] == sys.executable
    assert execv_calls[0]["args"] == [sys.executable, "-m", "mcp_server"]

    # Verify sys.exit was NOT called
    assert not exit_calls, "sys.exit should not be called (use os.execv instead)"
