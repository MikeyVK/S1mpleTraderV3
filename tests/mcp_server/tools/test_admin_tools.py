"""Tests for administrative tools (server restart functionality)."""

import json
import os
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
