"""Subprocess smoke tests for detect_sub_role.py.

Tests the complete I/O contract at the process boundary:
  - stdin JSON payload: {"prompt": str, "sessionId": str}
  - sys.argv[1] = role
  - writes SessionSubRoleState to .copilot/session-sub-role.json
  - always exits 0
  - idempotent on same session_id (state file not rewritten)

All tests are marked @pytest.mark.slow (spawn real subprocesses, tmp_path hermetic).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

_STATE_RELPATH = Path(".copilot") / "session-sub-role.json"


@pytest.mark.slow
class TestDetectSubRoleSmoke:
    def test_exits_zero_and_writes_state_for_matching_sub_role(self, hook_workspace: Path) -> None:
        """detect_sub_role.py exits 0 and writes correct sub_role to state file."""
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

    def test_idempotent_same_session_id_does_not_overwrite(self, hook_workspace: Path) -> None:
        """Second call with same session_id leaves state unchanged; exits 0."""
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

        # Second call -- different keyword but SAME session_id; state must NOT change
        second_payload = json.dumps(
            {"prompt": "researcher: investigate options", "sessionId": "sess-002"}
        )
        result = subprocess.run(
            [sys.executable, script, "imp"],
            input=second_payload,
            capture_output=True,
            text=True,
            cwd=str(hook_workspace),
        )
        assert result.returncode == 0
        assert json.loads(state_file.read_text())["sub_role"] == "validator"

    def test_exits_zero_for_empty_prompt_falls_back_to_default(self, hook_workspace: Path) -> None:
        """detect_sub_role.py exits 0 with empty prompt (falls back to role default)."""
        payload = json.dumps({"prompt": "", "sessionId": "sess-003"})
        result = subprocess.run(
            [sys.executable, str(hook_workspace / "detect_sub_role.py"), "imp"],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(hook_workspace),
        )
        assert result.returncode == 0
        state = json.loads((hook_workspace / _STATE_RELPATH).read_text())
        assert state["sub_role"] == "implementer"  # imp default
