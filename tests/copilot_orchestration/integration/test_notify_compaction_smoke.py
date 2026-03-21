"""Subprocess smoke tests for notify_compaction.py.

Tests the complete I/O contract at the process boundary:
  - stdin JSON payload: {"sessionId": str}
  - stdout JSON: {"systemMessage": str} when state matches, {} otherwise
  - always exits 0 (soft failure: hook errors must not break agent session)

All tests are marked @pytest.mark.slow (spawn real subprocesses, tmp_path hermetic).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

_STATE_RELPATH = Path(".copilot") / "session-sub-role.json"


@pytest.mark.slow
class TestNotifyCompactionSmoke:
    def test_returns_empty_dict_when_state_absent(self, hook_workspace: Path) -> None:
        """notify_compaction.py returns {} when state file does not exist."""
        payload = json.dumps({"sessionId": "sess-nc-001"})
        result = subprocess.run(
            [sys.executable, str(hook_workspace / "notify_compaction.py")],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(hook_workspace),
        )
        assert result.returncode == 0
        assert json.loads(result.stdout) == {}

    def test_returns_system_message_for_matching_session_id(self, hook_workspace: Path) -> None:
        """Returns systemMessage with correct sub_role when session_id matches."""
        state = {
            "session_id": "sess-nc-002",
            "role": "imp",
            "sub_role": "validator",
            "detected_at": "2026-03-21T14:00:00Z",
        }
        (hook_workspace / _STATE_RELPATH).write_text(json.dumps(state))

        payload = json.dumps({"sessionId": "sess-nc-002"})
        result = subprocess.run(
            [sys.executable, str(hook_workspace / "notify_compaction.py")],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(hook_workspace),
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert "systemMessage" in output
        assert "validator" in output["systemMessage"]

    def test_exits_zero_with_corrupted_state_file(self, hook_workspace: Path) -> None:
        """notify_compaction.py exits 0 even when state file contains invalid JSON."""
        (hook_workspace / _STATE_RELPATH).write_text("NOT JSON{{{")

        payload = json.dumps({"sessionId": "sess-nc-003"})
        result = subprocess.run(
            [sys.executable, str(hook_workspace / "notify_compaction.py")],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(hook_workspace),
        )
        assert result.returncode == 0

    def test_returns_empty_dict_for_mismatched_session_id(self, hook_workspace: Path) -> None:
        """Returns {} when state file exists but session_id does not match payload."""
        state = {"session_id": "other-session", "sub_role": "researcher"}
        (hook_workspace / _STATE_RELPATH).write_text(json.dumps(state))

        payload = json.dumps({"sessionId": "sess-nc-different"})
        result = subprocess.run(
            [sys.executable, str(hook_workspace / "notify_compaction.py")],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(hook_workspace),
        )
        assert result.returncode == 0
        assert json.loads(result.stdout) == {}
