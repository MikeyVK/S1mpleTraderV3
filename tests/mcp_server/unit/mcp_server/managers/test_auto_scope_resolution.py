# tests/mcp_server/unit/mcp_server/managers/test_auto_scope_resolution.py
"""
C23: Resolve scope=auto happy path — baseline present.

Union of git diff --name-only baseline_sha..HEAD and persisted failed_files.
"""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_server.managers.qa_manager import QAManager


def _write_state(tmp_path: Path, baseline_sha: str, failed_files: list[str]) -> None:
    """Write a .st3/state.json with quality_gates section."""
    state = {
        "branch": "refactor/251-refactor-run-quality-gates",
        "quality_gates": {
            "baseline_sha": baseline_sha,
            "failed_files": failed_files,
        },
    }
    state_path = tmp_path / ".st3" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")


def _fake_diff(py_files: list[str]) -> MagicMock:
    """Return a subprocess.CompletedProcess mock with the given .py files as stdout."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = 0
    result.stdout = "\n".join(py_files) + ("\n" if py_files else "")
    return result


class TestAutoScopeHappyPath:
    """C23: scope=auto with baseline_sha present returns union of diff + failed_files."""

    def test_auto_scope_returns_failed_files_when_diff_empty(self, tmp_path: Path) -> None:
        """Test A: failed_files present, diff empty → auto-scope returns failed_files."""
        _write_state(tmp_path, baseline_sha="abc123", failed_files=["old_fail.py"])
        manager = QAManager(workspace_root=tmp_path)

        with patch("subprocess.run", return_value=_fake_diff([])):
            result = manager._resolve_scope("auto")

        assert result == ["old_fail.py"], (
            f"Expected ['old_fail.py'] but got {result!r}. "
            "scope=auto must include persisted failed_files even when diff is empty."
        )

    def test_auto_scope_returns_diff_files_when_no_failed_files(self, tmp_path: Path) -> None:
        """Test B: diff has files, failed_files empty → auto-scope returns diff files."""
        _write_state(tmp_path, baseline_sha="abc123", failed_files=[])
        manager = QAManager(workspace_root=tmp_path)

        with patch("subprocess.run", return_value=_fake_diff(["changed.py"])):
            result = manager._resolve_scope("auto")

        assert result == ["changed.py"], (
            f"Expected ['changed.py'] but got {result!r}. "
            "scope=auto must include files from git diff baseline_sha..HEAD."
        )

    def test_auto_scope_returns_union_of_diff_and_failed_files(self, tmp_path: Path) -> None:
        """Test C: both diff and failed_files present → result is the union of both."""
        _write_state(
            tmp_path,
            baseline_sha="abc123",
            failed_files=["old_fail.py", "another_fail.py"],
        )
        manager = QAManager(workspace_root=tmp_path)

        with patch("subprocess.run", return_value=_fake_diff(["changed.py", "old_fail.py"])):
            result = manager._resolve_scope("auto")

        assert set(result) == {"old_fail.py", "another_fail.py", "changed.py"}, (
            f"Expected union of diff + failed_files but got {result!r}."
        )

    def test_auto_scope_result_is_sorted(self, tmp_path: Path) -> None:
        """Result list is sorted (deterministic)."""
        _write_state(
            tmp_path,
            baseline_sha="abc123",
            failed_files=["z_fail.py"],
        )
        manager = QAManager(workspace_root=tmp_path)

        with patch("subprocess.run", return_value=_fake_diff(["a_changed.py", "m_changed.py"])):
            result = manager._resolve_scope("auto")

        assert result == sorted(result), f"Result is not sorted: {result!r}"

    def test_auto_scope_no_duplicates_when_overlap(self, tmp_path: Path) -> None:
        """Overlap between diff and failed_files produces no duplicates."""
        _write_state(
            tmp_path,
            baseline_sha="abc123",
            failed_files=["shared.py"],
        )
        manager = QAManager(workspace_root=tmp_path)

        with patch("subprocess.run", return_value=_fake_diff(["shared.py"])):
            result = manager._resolve_scope("auto")

        assert result.count("shared.py") == 1, (
            f"Duplicate entry in result: {result!r}"
        )

    def test_auto_scope_uses_baseline_sha_not_parent_branch(self, tmp_path: Path) -> None:
        """Git diff uses baseline_sha..HEAD, not workflow.parent_branch..HEAD."""
        _write_state(tmp_path, baseline_sha="deadbeef", failed_files=[])
        # Also write a workflow.parent_branch to ensure it is NOT used
        state_path = tmp_path / ".st3" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["workflow"] = {"parent_branch": "main"}
        state_path.write_text(json.dumps(state), encoding="utf-8")

        manager = QAManager(workspace_root=tmp_path)
        captured: list[list[str]] = []

        def fake_git(cmd: list[str], **_kw: object) -> MagicMock:
            captured.append(cmd)
            return _fake_diff(["mcp_server/foo.py"])

        with patch("subprocess.run", side_effect=fake_git):
            manager._resolve_scope("auto")

        assert captured, "subprocess.run was not called"
        assert "deadbeef..HEAD" in captured[0], (
            f"Expected 'deadbeef..HEAD' in git diff args, got: {captured[0]}"
        )
        assert "main..HEAD" not in captured[0], (
            "scope=auto must NOT use workflow.parent_branch — it must use quality_gates.baseline_sha"
        )

    def test_auto_scope_excludes_non_py_files_from_diff(self, tmp_path: Path) -> None:
        """Non-.py files in git diff output are excluded from the result."""
        _write_state(tmp_path, baseline_sha="abc123", failed_files=[])
        manager = QAManager(workspace_root=tmp_path)

        raw_result = MagicMock(spec=subprocess.CompletedProcess)
        raw_result.returncode = 0
        raw_result.stdout = "mcp_server/logic.py\ndocs/README.md\n.st3/state.json\n"

        with patch("subprocess.run", return_value=raw_result):
            result = manager._resolve_scope("auto")

        assert "docs/README.md" not in result
        assert ".st3/state.json" not in result
        assert "mcp_server/logic.py" in result
