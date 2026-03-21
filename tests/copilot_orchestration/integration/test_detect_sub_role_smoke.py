"""Subprocess smoke tests for detect_sub_role.py.

Tests the complete I/O contract at the process boundary:
  - stdin JSON payload: {"prompt": str, "sessionId": str}
  - sys.argv[1] = role
  - writes SessionSubRoleState to .copilot/session-sub-role-{role}.json
  - always exits 0
  - idempotency lock removed: every matching prompt overwrites file

All tests are marked @pytest.mark.slow (spawn real subprocesses, tmp_path hermetic).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

_STATE_RELPATH = Path(".copilot") / "session-sub-role-imp.json"


@pytest.mark.slow
class TestDetectSubRoleSmoke:
    def test_exits_zero_and_writes_state_for_matching_sub_role(self, hook_workspace: Path) -> None:
        """detect_sub_role.py exits 0 and writes correct sub_role to role-scoped state file."""
        payload = json.dumps({"prompt": "implementer: start cycle", "sessionId": "sess-001"})
        result = subprocess.run(
            [sys.executable, str(hook_workspace / "detect_sub_role.py"), "imp"],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(hook_workspace),
        )
        assert result.returncode == 0

        state_file = hook_workspace / _STATE_RELPATH
        assert state_file.exists(), "State file must be written after first call"
        state = json.loads(state_file.read_text())
        assert state["sub_role"] == "implementer"
        assert state["session_id"] == "sess-001"

    def test_mid_session_change_overwrites_sub_role(self, hook_workspace: Path) -> None:
        """Second call with different keyword overwrites state (idempotency lock removed)."""
        script = str(hook_workspace / "detect_sub_role.py")
        state_file = hook_workspace / _STATE_RELPATH

        # First call -- validator keyword
        first_payload = json.dumps(
            {"prompt": "validator: write smoke tests", "sessionId": "sess-002"}
        )
        subprocess.run(
            [sys.executable, script, "imp"],
            input=first_payload,
            capture_output=True,
            text=True,
            cwd=str(hook_workspace),
        )
        assert json.loads(state_file.read_text())["sub_role"] == "validator"

        # Second call -- different keyword AND different session_id; state MUST change
        second_payload = json.dumps(
            {"prompt": "researcher: investigate options", "sessionId": "sess-002b"}
        )
        result = subprocess.run(
            [sys.executable, script, "imp"],
            input=second_payload,
            capture_output=True,
            text=True,
            cwd=str(hook_workspace),
        )
        assert result.returncode == 0
        assert json.loads(state_file.read_text())["sub_role"] == "researcher"

    def test_exploration_mode_no_match_writes_no_file(self, hook_workspace: Path) -> None:
        """Exploration mode: empty prompt → no match → role-scoped state file NOT written."""
        payload = json.dumps({"prompt": "", "sessionId": "sess-003"})
        result = subprocess.run(
            [sys.executable, str(hook_workspace / "detect_sub_role.py"), "imp"],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(hook_workspace),
        )
        assert result.returncode == 0
        assert not (hook_workspace / _STATE_RELPATH).exists(), (
            "State file must NOT be written when no sub_role keyword is detected"
        )
