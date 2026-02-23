# tests/mcp_server/unit/mcp_server/managers/test_baseline_advance.py
"""
C19: When all gates pass, persist HEAD as baseline_sha and reset failed_files.
C20: Union newly failed files with persisted failed_files set.
"""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.managers.qa_manager import QAManager


def _state_with_quality_gates(
    tmp_path: Path,
    baseline_sha: str = "old_sha",
    failed_files: list[str] | None = None,
) -> Path:
    """Write a .st3/state.json with quality_gates section; returns state file path."""
    st3_dir = tmp_path / ".st3"
    st3_dir.mkdir(exist_ok=True)
    state_file = st3_dir / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "branch": "refactor/251-test",
                "issue_number": 251,
                "quality_gates": {
                    "baseline_sha": baseline_sha,
                    "failed_files": failed_files if failed_files is not None else [],
                },
            }
        )
    )
    return state_file


def _all_pass_config() -> MagicMock:
    """Return a QualityConfig mock with a single trivially-passing gate sentinel."""
    cfg = MagicMock()
    cfg.active_gates = []  # empty → no gates executed → overall_pass stays True
    # But empty active_gates triggers the "No active_gates" early-exit with overall_pass=False.
    # We therefore use a non-empty list and mock _execute_gate instead.
    return cfg


class TestBaselineAdvanceOnAllPass:
    """C19: Baseline advances to HEAD when every gate passes."""

    def test_workspace_root_accepted_by_constructor(self, tmp_path: Path) -> None:
        """QAManager(workspace_root=path) must be constructable (no TypeError)."""
        # RED: TypeError because __init__ does not yet accept workspace_root
        manager = QAManager(workspace_root=tmp_path)
        assert manager is not None

    def test_all_pass_writes_new_baseline_sha(self, tmp_path: Path) -> None:
        """After all gates pass, state.json.quality_gates.baseline_sha equals git HEAD."""
        state_file = _state_with_quality_gates(
            tmp_path,
            baseline_sha="old_sha_abc",
            failed_files=["mcp_server/old_failure.py"],
        )

        manager = QAManager(workspace_root=tmp_path)

        fake_sha = "newsha1234567890"
        _fake_subprocess_all_pass(fake_sha)

        config = MagicMock()
        config.active_gates = ["gate0_format"]
        config.gates = {}  # unknown gate → skipped (no failure)
        config.artifact_logging.enabled = False
        config.artifact_logging.output_dir = "temp/qa_logs"
        config.artifact_logging.max_files = 10

        with (
            patch(
                "mcp_server.managers.qa_manager.QualityConfig.load",
                return_value=config,
            ),
            patch(
                "subprocess.run",
                side_effect=lambda cmd, **kw: _fake_subprocess_all_pass(fake_sha, cmd),
            ),
        ):
            manager.run_quality_gates(files=["mcp_server/managers/qa_manager.py"])

        state = json.loads(state_file.read_text())
        assert state["quality_gates"]["baseline_sha"] == fake_sha

    def test_all_pass_clears_failed_files(self, tmp_path: Path) -> None:
        """After all gates pass, state.json.quality_gates.failed_files is []."""
        state_file = _state_with_quality_gates(
            tmp_path,
            baseline_sha="old_sha",
            failed_files=["mcp_server/foo.py", "mcp_server/bar.py"],
        )

        manager = QAManager(workspace_root=tmp_path)

        fake_sha = "cleansha000"

        config = MagicMock()
        config.active_gates = ["gate0_format"]
        config.gates = {}  # unknown gate → skipped
        config.artifact_logging.enabled = False
        config.artifact_logging.output_dir = "temp/qa_logs"
        config.artifact_logging.max_files = 10

        with (
            patch(
                "mcp_server.managers.qa_manager.QualityConfig.load",
                return_value=config,
            ),
            patch(
                "subprocess.run",
                side_effect=lambda cmd, **kw: _fake_subprocess_all_pass(fake_sha, cmd),
            ),
        ):
            manager.run_quality_gates(files=["mcp_server/managers/qa_manager.py"])

        state = json.loads(state_file.read_text())
        assert state["quality_gates"]["failed_files"] == []

    def test_all_pass_preserves_other_state_keys(self, tmp_path: Path) -> None:
        """State update must not overwrite branch/issue_number or other keys."""
        state_file = _state_with_quality_gates(tmp_path)

        manager = QAManager(workspace_root=tmp_path)

        fake_sha = "preserve_sha"
        config = MagicMock()
        config.active_gates = ["gate0_format"]
        config.gates = {}
        config.artifact_logging.enabled = False
        config.artifact_logging.output_dir = "temp/qa_logs"
        config.artifact_logging.max_files = 10

        with (
            patch(
                "mcp_server.managers.qa_manager.QualityConfig.load",
                return_value=config,
            ),
            patch(
                "subprocess.run",
                side_effect=lambda cmd, **kw: _fake_subprocess_all_pass(fake_sha, cmd),
            ),
        ):
            manager.run_quality_gates(files=["mcp_server/managers/qa_manager.py"])

        state = json.loads(state_file.read_text())
        assert state["branch"] == "refactor/251-test"
        assert state["issue_number"] == 251

    def test_no_state_file_all_pass_creates_quality_gates_section(
        self, tmp_path: Path
    ) -> None:
        """When state.json is absent, a successful run creates the quality_gates key."""
        st3_dir = tmp_path / ".st3"
        st3_dir.mkdir()
        state_file = st3_dir / "state.json"
        # Do NOT create state.json — it is absent

        manager = QAManager(workspace_root=tmp_path)

        fake_sha = "fresh_sha_999"
        config = MagicMock()
        config.active_gates = ["gate0_format"]
        config.gates = {}
        config.artifact_logging.enabled = False
        config.artifact_logging.output_dir = "temp/qa_logs"
        config.artifact_logging.max_files = 10

        with (
            patch(
                "mcp_server.managers.qa_manager.QualityConfig.load",
                return_value=config,
            ),
            patch(
                "subprocess.run",
                side_effect=lambda cmd, **kw: _fake_subprocess_all_pass(fake_sha, cmd),
            ),
        ):
            manager.run_quality_gates(files=["mcp_server/managers/qa_manager.py"])

        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["quality_gates"]["baseline_sha"] == fake_sha
        assert state["quality_gates"]["failed_files"] == []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_subprocess_all_pass(
    fake_sha: str, cmd: list[str] | None = None
) -> MagicMock:
    """Return a MagicMock subprocess result: exit 0, stdout=sha for rev-parse."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = 0
    result.stderr = ""
    if cmd and "rev-parse" in cmd:
        result.stdout = fake_sha + "\n"
    else:
        result.stdout = ""
    return result
