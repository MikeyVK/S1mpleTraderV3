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
