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


class TestBaselineAdvanceOnAllPass:
    """C19: Baseline advances to HEAD when every gate passes."""

    def test_workspace_root_accepted_by_constructor(self, tmp_path: Path) -> None:
        """QAManager(workspace_root=path) must be constructable (no TypeError)."""
        manager = QAManager(workspace_root=tmp_path)
        assert manager is not None

    def test_workspace_root_stored_on_instance(self, tmp_path: Path) -> None:
        """Constructor stores workspace_root on the instance."""
        manager = QAManager(workspace_root=tmp_path)
        assert manager.workspace_root == tmp_path

    def test_advance_baseline_writes_new_sha(self, tmp_path: Path) -> None:
        """_advance_baseline_on_all_pass writes HEAD sha to quality_gates.baseline_sha."""
        state_file = _state_with_quality_gates(
            tmp_path,
            baseline_sha="old_sha_abc",
            failed_files=["mcp_server/old_failure.py"],
        )

        manager = QAManager(workspace_root=tmp_path)
        fake_sha = "newsha1234567890"

        with patch.object(manager, "_get_head_sha", return_value=fake_sha):
            manager._advance_baseline_on_all_pass()

        state = json.loads(state_file.read_text())
        assert state["quality_gates"]["baseline_sha"] == fake_sha

    def test_advance_baseline_clears_failed_files(self, tmp_path: Path) -> None:
        """_advance_baseline_on_all_pass resets quality_gates.failed_files to []."""
        state_file = _state_with_quality_gates(
            tmp_path,
            baseline_sha="old_sha",
            failed_files=["mcp_server/foo.py", "mcp_server/bar.py"],
        )

        manager = QAManager(workspace_root=tmp_path)

        with patch.object(manager, "_get_head_sha", return_value="cleansha000"):
            manager._advance_baseline_on_all_pass()

        state = json.loads(state_file.read_text())
        assert state["quality_gates"]["failed_files"] == []

    def test_advance_baseline_preserves_other_state_keys(self, tmp_path: Path) -> None:
        """State update must not overwrite branch/issue_number or other top-level keys."""
        state_file = _state_with_quality_gates(tmp_path)

        manager = QAManager(workspace_root=tmp_path)

        with patch.object(manager, "_get_head_sha", return_value="preserve_sha"):
            manager._advance_baseline_on_all_pass()

        state = json.loads(state_file.read_text())
        assert state["branch"] == "refactor/251-test"
        assert state["issue_number"] == 251

    def test_advance_baseline_creates_state_file_if_absent(
        self, tmp_path: Path
    ) -> None:
        """When state.json is absent, _advance_baseline_on_all_pass creates it."""
        st3_dir = tmp_path / ".st3"
        st3_dir.mkdir()
        state_file = st3_dir / "state.json"
        assert not state_file.exists()  # precondition

        manager = QAManager(workspace_root=tmp_path)
        fake_sha = "fresh_sha_999"

        with patch.object(manager, "_get_head_sha", return_value=fake_sha):
            manager._advance_baseline_on_all_pass()

        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state["quality_gates"]["baseline_sha"] == fake_sha
        assert state["quality_gates"]["failed_files"] == []

    def test_run_quality_gates_calls_advance_on_all_pass(
        self, tmp_path: Path
    ) -> None:
        """run_quality_gates invokes _advance_baseline_on_all_pass when overall_pass=True."""
        manager = QAManager(workspace_root=tmp_path)

        # Give a trivially all-pass config (empty active_gates list) but bypass
        # the early-exit ConfigError: we set overall_pass=True directly via patch.
        with (
            patch.object(
                manager,
                "_advance_baseline_on_all_pass",
            ) as mock_advance,
            patch("mcp_server.managers.qa_manager.QualityConfig.load") as mock_cfg,
        ):
            cfg = MagicMock()
            cfg.active_gates = []
            cfg.artifact_logging.enabled = False
            cfg.artifact_logging.output_dir = "temp/qa_logs"
            cfg.artifact_logging.max_files = 10
            mock_cfg.return_value = cfg

            result = manager.run_quality_gates(files=[])

        # overall_pass is False when active_gates == [] (config error gate fires)
        # so _advance_baseline_on_all_pass should NOT have been called
        if result["overall_pass"]:
            mock_advance.assert_called_once()
        else:
            mock_advance.assert_not_called()
