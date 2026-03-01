# tests/mcp_server/unit/mcp_server/managers/test_baseline_advance.py
"""
C19: When all gates pass, persist HEAD as baseline_sha and reset failed_files.
C20: Union newly failed files with persisted failed_files set.
"""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_advance_baseline_creates_state_file_if_absent(self, tmp_path: Path) -> None:
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

    def test_run_quality_gates_calls_advance_on_all_pass(self, tmp_path: Path) -> None:
        """run_quality_gates invokes _advance_baseline_on_all_pass when overall_pass=True."""
        manager = QAManager(workspace_root=tmp_path)

        test_file = tmp_path / "ok.py"
        test_file.write_text("print('ok')\n", encoding="utf-8")

        with (
            patch.object(manager, "_advance_baseline_on_all_pass") as mock_advance,
            patch.object(manager, "_accumulate_failed_files_on_failure") as mock_acc,
            patch("mcp_server.managers.qa_manager.QualityConfig.load") as mock_cfg,
            patch.object(
                manager,
                "_execute_gate",
                return_value={
                    "gate_number": 1,
                    "name": "Gate 1: Stub",
                    "passed": True,
                    "status": "passed",
                    "score": "Pass",
                    "issues": [],
                    "duration_ms": 0,
                },
            ),
        ):
            cfg = MagicMock()
            cfg.active_gates = ["gate1_stub"]
            gate = MagicMock()
            gate.name = "Gate 1: Stub"
            gate.scope = None
            gate.capabilities.file_types = [".py"]
            cfg.gates = {"gate1_stub": gate}
            cfg.artifact_logging.enabled = False
            cfg.artifact_logging.output_dir = "temp/qa_logs"
            cfg.artifact_logging.max_files = 10
            mock_cfg.return_value = cfg

            result = manager.run_quality_gates(files=[str(test_file)])

        assert result["overall_pass"] is True
        mock_advance.assert_called_once()
        mock_acc.assert_not_called()


class TestFailureAccumulation:
    """C20: failed_files is the union of old persisted failures and newly failed files."""

    def test_accumulate_uses_set_union(self, tmp_path: Path) -> None:
        """New failures are merged with existing failed_files (not overwritten)."""
        state_file = _state_with_quality_gates(
            tmp_path,
            baseline_sha="sha_preserved",
            failed_files=["mcp_server/old_fail.py"],
        )

        manager = QAManager(workspace_root=tmp_path)
        # RED: _accumulate_failed_files_on_failure does not exist yet → AttributeError
        manager._accumulate_failed_files_on_failure(["mcp_server/new_fail.py"])

        state = json.loads(state_file.read_text())
        assert set(state["quality_gates"]["failed_files"]) == {
            "mcp_server/old_fail.py",
            "mcp_server/new_fail.py",
        }

    def test_accumulate_sorted_deterministic(self, tmp_path: Path) -> None:
        """failed_files list is deterministically sorted after union."""
        state_file = _state_with_quality_gates(
            tmp_path,
            baseline_sha="sha_preserved",
            failed_files=["mcp_server/z_last.py", "mcp_server/a_first.py"],
        )

        manager = QAManager(workspace_root=tmp_path)
        manager._accumulate_failed_files_on_failure(["mcp_server/m_middle.py"])

        state = json.loads(state_file.read_text())
        failed = state["quality_gates"]["failed_files"]
        assert failed == sorted(failed)

    def test_accumulate_no_duplicates(self, tmp_path: Path) -> None:
        """File already in failed_files is not duplicated after re-failure."""
        state_file = _state_with_quality_gates(
            tmp_path,
            baseline_sha="sha",
            failed_files=["mcp_server/common.py"],
        )

        manager = QAManager(workspace_root=tmp_path)
        manager._accumulate_failed_files_on_failure(["mcp_server/common.py"])

        state = json.loads(state_file.read_text())
        assert state["quality_gates"]["failed_files"].count("mcp_server/common.py") == 1

    def test_accumulate_baseline_sha_unchanged(self, tmp_path: Path) -> None:
        """baseline_sha must not change when accumulating failures."""
        original_sha = "keep_this_sha"
        state_file = _state_with_quality_gates(
            tmp_path,
            baseline_sha=original_sha,
            failed_files=[],
        )

        manager = QAManager(workspace_root=tmp_path)
        manager._accumulate_failed_files_on_failure(["mcp_server/failing.py"])

        state = json.loads(state_file.read_text())
        assert state["quality_gates"]["baseline_sha"] == original_sha

    def test_run_quality_gates_calls_accumulate_on_failure(self, tmp_path: Path) -> None:
        """run_quality_gates calls _accumulate_failed_files_on_failure when overall_pass=False."""
        manager = QAManager(workspace_root=tmp_path)

        with (
            patch.object(manager, "_accumulate_failed_files_on_failure") as mock_acc,
            patch("mcp_server.managers.qa_manager.QualityConfig.load") as mock_cfg,
        ):
            cfg = MagicMock()
            # Use an unknown gate (not in catalog) → overall_pass=False via normal code path.
            # active_gates=[] would trigger early-return before the state-update block.
            cfg.active_gates = ["unknown_gate_not_in_catalog"]
            cfg.gates = {}  # empty catalog → gate not found → passed=False → overall_pass=False
            cfg.artifact_logging.enabled = False
            cfg.artifact_logging.output_dir = "temp/qa_logs"
            cfg.artifact_logging.max_files = 10
            mock_cfg.return_value = cfg

            result = manager.run_quality_gates(files=["mcp_server/managers/qa_manager.py"])

        # unknown gate sets overall_pass=False → accumulate should be called
        assert not result["overall_pass"]
        mock_acc.assert_called_once_with(["mcp_server/managers/qa_manager.py"])


class TestScopeLifecycleGuard:
    """Cycle 41 refactor coverage: explicit scope-guard behavior."""

    def test_files_scope_failure_does_not_accumulate_failed_files(self, tmp_path: Path) -> None:
        """Failing scope='files' run must not mutate auto failed_files lifecycle state."""
        manager = QAManager(workspace_root=tmp_path)

        test_file = tmp_path / "failing.py"
        test_file.write_text("print('x')\n", encoding="utf-8")

        with (
            patch.object(manager, "_advance_baseline_on_all_pass") as mock_advance,
            patch.object(manager, "_accumulate_failed_files_on_failure") as mock_acc,
            patch("mcp_server.managers.qa_manager.QualityConfig.load") as mock_cfg,
            patch.object(
                manager,
                "_execute_gate",
                return_value={
                    "gate_number": 1,
                    "name": "Gate 1: Stub",
                    "passed": False,
                    "status": "failed",
                    "score": "Fail",
                    "issues": [{"file": str(test_file), "message": "boom"}],
                    "duration_ms": 0,
                },
            ),
        ):
            cfg = MagicMock()
            cfg.active_gates = ["gate1_stub"]
            gate = MagicMock()
            gate.name = "Gate 1: Stub"
            gate.scope = None
            gate.capabilities.file_types = [".py"]
            cfg.gates = {"gate1_stub": gate}
            cfg.artifact_logging.enabled = False
            cfg.artifact_logging.output_dir = "temp/qa_logs"
            cfg.artifact_logging.max_files = 10
            mock_cfg.return_value = cfg

            result = manager.run_quality_gates(
                files=[str(test_file)],
                effective_scope="files",
            )

        assert result["overall_pass"] is False
        mock_advance.assert_not_called()
        mock_acc.assert_not_called()

    def test_is_auto_lifecycle_scope_normalized_variants(self) -> None:
        """_is_auto_lifecycle_scope accepts case/whitespace variants for auto."""
        assert QAManager._is_auto_lifecycle_scope("auto") is True
        assert QAManager._is_auto_lifecycle_scope("AUTO") is True
        assert QAManager._is_auto_lifecycle_scope(" Auto ") is True
        assert QAManager._is_auto_lifecycle_scope("files") is False


class TestFailedSubsetExtractionC42:
    """Cycle 42 hardening: subset extraction edge-case coverage."""

    def test_collect_failed_files_fallback_to_evaluated_set_when_no_file_fields(self) -> None:
        """When failed issues have no file key, fallback to full evaluated set."""
        results = {
            "gates": [
                {
                    "name": "Gate 1",
                    "passed": False,
                    "status": "failed",
                    "issues": [{"message": "compilation error"}],
                }
            ]
        }
        evaluated = ["a.py", "b.py"]

        collected = QAManager._collect_failed_files_from_results(results, evaluated)
        assert collected == ["a.py", "b.py"]

    def test_collect_failed_files_ignores_issues_outside_evaluated_set(self) -> None:
        """Issue files not in evaluated set are excluded from failed subset."""
        results = {
            "gates": [
                {
                    "name": "Gate 1",
                    "passed": False,
                    "status": "failed",
                    "issues": [
                        {"file": "a.py", "message": "local fail"},
                        {"file": "external/lib.py", "message": "external fail"},
                    ],
                }
            ]
        }
        evaluated = ["a.py", "b.py"]

        collected = QAManager._collect_failed_files_from_results(results, evaluated)
        assert collected == ["a.py"]

    def test_collect_failed_files_unions_multiple_failed_gates(self) -> None:
        """Failed subset includes union of file hits across multiple failed gates."""
        results = {
            "gates": [
                {
                    "name": "Gate 1",
                    "passed": False,
                    "status": "failed",
                    "issues": [{"file": "a.py", "message": "lint"}],
                },
                {
                    "name": "Gate 2",
                    "passed": False,
                    "status": "failed",
                    "issues": [{"file": "b.py", "message": "types"}],
                },
            ]
        }
        evaluated = ["a.py", "b.py", "c.py"]

        collected = QAManager._collect_failed_files_from_results(results, evaluated)
        assert collected == ["a.py", "b.py"]


class TestGateStatusStamping:
    """Refactor hardening: resolved gate status is stamped back into gate result."""

    def test_update_summary_stamps_resolved_status(self) -> None:
        manager = QAManager()
        results = {
            "summary": {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "total_violations": 0,
                "auto_fixable": 0,
            },
            "gates": [],
            "overall_pass": True,
        }
        gate_result = {
            "name": "Gate X",
            "passed": False,
            "score": "Fail",
            "issues": [{"file": "a.py", "message": "boom"}],
        }

        manager._update_summary_and_append_gate(results, gate_result)

        assert gate_result["status"] == "failed"
