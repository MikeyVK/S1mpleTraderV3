"""Subprocess smoke tests for stop_handover_guard.py.

Tests the complete I/O contract at the process boundary:
  - stdin JSON payload: {"sessionId": str, "stop_hook_active"?: bool}
  - sys.argv[1] = role (optional, defaults to "")
  - stdout JSON: {"hookSpecificOutput": {"decision": "block", ...}} OR {}
  - always exits 0 -- blocking is signalled via decision field, NOT exit code

All tests are marked @pytest.mark.slow (spawn real subprocesses, tmp_path hermetic).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

_STATE_RELPATH_IMP = Path(".copilot") / "session-sub-role-imp.json"
_STATE_RELPATH_QA = Path(".copilot") / "session-sub-role-qa.json"


def _run_guard(hook_workspace: Path, role: str, payload: dict) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    return subprocess.run(
        [sys.executable, str(hook_workspace / "stop_handover_guard.py"), role],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(hook_workspace),
    )


@pytest.mark.slow
class TestStopHandoverGuardSmoke:
    def test_decision_block_for_imp_validator_without_stop_hook_active(
        self, hook_workspace: Path
    ) -> None:
        """imp/validator without stop_hook_active → decision: block in output, exit 0."""
        state = {
            "session_id": "sess-shg-001",
            "role": "imp",
            "sub_role": "validator",
        }
        (hook_workspace / _STATE_RELPATH_IMP).write_text(json.dumps(state))

        result = _run_guard(hook_workspace, "imp", {"sessionId": "sess-shg-001"})

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["decision"] == "block"

    def test_pass_through_when_stop_hook_active(self, hook_workspace: Path) -> None:
        """stop_hook_active: true → output is {}, exit 0 (no block)."""
        state = {
            "session_id": "sess-shg-002",
            "role": "imp",
            "sub_role": "implementer",
        }
        (hook_workspace / _STATE_RELPATH_IMP).write_text(json.dumps(state))

        result = _run_guard(
            hook_workspace, "imp", {"sessionId": "sess-shg-002", "stopHookActive": True}
        )

        assert result.returncode == 0
        assert json.loads(result.stdout) == {}

    def test_exploration_mode_no_state_file_returns_empty_dict_for_imp(
        self, hook_workspace: Path
    ) -> None:
        """No state file for imp → exploration mode → output is {}, exit 0."""
        state_path = hook_workspace / _STATE_RELPATH_IMP
        if state_path.exists():
            state_path.unlink()

        result = _run_guard(hook_workspace, "imp", {"sessionId": "sess-shg-003"})

        assert result.returncode == 0
        assert json.loads(result.stdout) == {}

    def test_exploration_mode_no_state_file_returns_empty_dict_for_qa(
        self, hook_workspace: Path
    ) -> None:
        """No state file for qa → exploration mode → output is {}, exit 0."""
        state_path = hook_workspace / _STATE_RELPATH_QA
        if state_path.exists():
            state_path.unlink()

        result = _run_guard(hook_workspace, "qa", {"sessionId": "sess-shg-004"})

        assert result.returncode == 0
        assert json.loads(result.stdout) == {}
