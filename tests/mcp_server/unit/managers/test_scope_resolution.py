# tests/mcp_server/unit/mcp_server/managers/test_scope_resolution.py
"""
C21: Resolve scope=project from project_scope globs (expand globs against workspace root).
C22: Resolve scope=branch using git diff parent..HEAD.
"""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_server.managers.qa_manager import QAManager


def _make_workspace(tmp_path: Path, files: list[str]) -> None:
    """Create stub Python files in tmp_path at the given relative paths."""
    for rel in files:
        full = tmp_path / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("# stub\n")


def _project_scope_config(include_globs: list[str]) -> MagicMock:
    """Return a mock QualityConfig with project_scope set to include_globs."""
    scope = MagicMock()
    scope.include_globs = include_globs

    cfg = MagicMock()
    cfg.project_scope = scope
    cfg.active_gates = []
    cfg.artifact_logging.enabled = False
    cfg.artifact_logging.output_dir = "temp/qa_logs"
    cfg.artifact_logging.max_files = 10
    return cfg


class TestScopeResolutionBranch:
    """C22: _resolve_scope('branch') returns Python files from git diff <parent>..HEAD."""

    def test_branch_scope_returns_changed_py_files(self, tmp_path: Path) -> None:
        """Changed .py files from git diff <parent>..HEAD are returned as sorted list."""
        manager = QAManager(workspace_root=tmp_path)

        diff_output = "mcp_server/foo.py\nmcp_server/bar.py\n"

        def fake_git_diff(_cmd: list[str], **_kw: object) -> MagicMock:
            result = MagicMock(spec=subprocess.CompletedProcess)
            result.returncode = 0
            result.stdout = diff_output
            return result

        with patch("subprocess.run", side_effect=fake_git_diff):
            result = manager._resolve_scope("branch")

        assert "mcp_server/bar.py" in result
        assert "mcp_server/foo.py" in result

    def test_branch_scope_sorted(self, tmp_path: Path) -> None:
        """Result list is sorted after git diff."""
        manager = QAManager(workspace_root=tmp_path)

        diff_output = "z_file.py\na_file.py\nm_file.py\n"

        def fake_git_diff(_cmd: list[str], **_kw: object) -> MagicMock:
            result = MagicMock(spec=subprocess.CompletedProcess)
            result.returncode = 0
            result.stdout = diff_output
            return result

        with patch("subprocess.run", side_effect=fake_git_diff):
            result = manager._resolve_scope("branch")

        assert result == sorted(result)

    def test_branch_scope_excludes_non_py_files(self, tmp_path: Path) -> None:
        """Non-Python files are excluded from the result."""
        manager = QAManager(workspace_root=tmp_path)

        diff_output = "mcp_server/logic.py\ndocs/README.md\n.st3/state.json\n"

        def fake_git_diff(_cmd: list[str], **_kw: object) -> MagicMock:
            result = MagicMock(spec=subprocess.CompletedProcess)
            result.returncode = 0
            result.stdout = diff_output
            return result

        with patch("subprocess.run", side_effect=fake_git_diff):
            result = manager._resolve_scope("branch")

        assert "docs/README.md" not in result
        assert ".st3/state.json" not in result
        assert "mcp_server/logic.py" in result

    def test_branch_scope_git_error_returns_empty(self, tmp_path: Path) -> None:
        """When git diff fails (non-zero exit), scope=branch returns [] gracefully."""
        manager = QAManager(workspace_root=tmp_path)

        def fake_git_fail(_cmd: list[str], **_kw: object) -> MagicMock:
            result = MagicMock(spec=subprocess.CompletedProcess)
            result.returncode = 128
            result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=fake_git_fail):
            result = manager._resolve_scope("branch")

        assert result == []

    def test_branch_scope_empty_diff_returns_empty(self, tmp_path: Path) -> None:
        """When git diff output is empty, scope=branch returns []."""
        manager = QAManager(workspace_root=tmp_path)

        def fake_git_empty(_cmd: list[str], **_kw: object) -> MagicMock:
            result = MagicMock(spec=subprocess.CompletedProcess)
            result.returncode = 0
            result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=fake_git_empty):
            result = manager._resolve_scope("branch")

        assert result == []

    def test_branch_scope_uses_parent_from_state_json(self, tmp_path: Path) -> None:
        """When state.json contains top-level parent_branch, that branch is used as diff base."""
        state = {"parent_branch": "feature/parent-branch"}
        state_path = tmp_path / ".st3" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state))

        manager = QAManager(workspace_root=tmp_path)
        captured_cmd: list[list[str]] = []

        def fake_git(_cmd: list[str], **_kw: object) -> MagicMock:
            captured_cmd.append(_cmd)
            result = MagicMock(spec=subprocess.CompletedProcess)
            result.returncode = 0
            result.stdout = "mcp_server/foo.py\n"
            return result

        with patch("subprocess.run", side_effect=fake_git):
            manager._resolve_scope("branch")

        assert captured_cmd, "subprocess.run was not called"
        assert "feature/parent-branch..HEAD" in captured_cmd[0]

    def test_branch_scope_reads_top_level_parent_branch(self, tmp_path: Path) -> None:
        """parent_branch lives at top level in state.json, not nested under workflow."""
        state = {"parent_branch": "epic/76-quality-gates"}
        state_path = tmp_path / ".st3" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state))

        manager = QAManager(workspace_root=tmp_path)
        captured_cmd: list[list[str]] = []

        def fake_git(_cmd: list[str], **_kw: object) -> MagicMock:
            captured_cmd.append(_cmd)
            result = MagicMock(spec=subprocess.CompletedProcess)
            result.returncode = 0
            result.stdout = "mcp_server/bar.py\n"
            return result

        with patch("subprocess.run", side_effect=fake_git):
            manager._resolve_scope("branch")

        assert captured_cmd, "subprocess.run was not called"
        assert "epic/76-quality-gates..HEAD" in captured_cmd[0], (
            f"Expected epic/76-quality-gates..HEAD in git cmd, got: {captured_cmd[0]}"
        )

    def test_branch_scope_git_cmd_includes_diff_filter_d(self, tmp_path: Path) -> None:
        """F-20: git diff command MUST include --diff-filter=d to exclude deleted files.

        When a file is deleted on the branch vs the parent (status D in git diff),
        it no longer exists at HEAD.  Without --diff-filter=d the stale path would
        reach File Validation and produce spurious 'File not found' errors.
        """
        manager = QAManager(workspace_root=tmp_path)
        captured_cmd: list[list[str]] = []

        def fake_git(_cmd: list[str], **_kw: object) -> MagicMock:
            captured_cmd.append(_cmd)
            result = MagicMock(spec=subprocess.CompletedProcess)
            result.returncode = 0
            result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=fake_git):
            manager._resolve_scope("branch")

        assert captured_cmd, "subprocess.run was not called"
        git_cmd = captured_cmd[0]
        assert "--diff-filter=d" in git_cmd, (
            f"F-20 regression: --diff-filter=d missing from git diff command: {git_cmd}"
        )

    def test_branch_scope_falls_back_to_main_without_state(self, tmp_path: Path) -> None:
        """When state.json is absent, git diff falls back to main..HEAD."""
        manager = QAManager(workspace_root=tmp_path)
        captured_cmd: list[list[str]] = []

        def fake_git(_cmd: list[str], **_kw: object) -> MagicMock:
            captured_cmd.append(_cmd)
            result = MagicMock(spec=subprocess.CompletedProcess)
            result.returncode = 0
            result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=fake_git):
            manager._resolve_scope("branch")

        assert captured_cmd, "subprocess.run was not called"
        assert "main..HEAD" in captured_cmd[0]


class TestScopeResolutionProject:
    """C21: _resolve_scope('project') expands include_globs from config against workspace_root."""

    def test_project_scope_returns_matching_files(self, tmp_path: Path) -> None:
        """Files matching include_globs are returned as sorted relative paths."""
        _make_workspace(
            tmp_path,
            [
                "mcp_server/alpha.py",
                "mcp_server/beta.py",
                "tests/test_alpha.py",
            ],
        )

        manager = QAManager(workspace_root=tmp_path)
        cfg = _project_scope_config(include_globs=["mcp_server/*.py"])

        with patch(
            "mcp_server.managers.qa_manager.QualityConfig.load",
            return_value=cfg,
        ):
            # RED: _resolve_scope does not exist yet → AttributeError
            result = manager._resolve_scope("project")

        assert "mcp_server/alpha.py" in result or "mcp_server\\alpha.py" in result

    def test_project_scope_sorted_deterministic(self, tmp_path: Path) -> None:
        """Returned file list is sorted (deterministic across OS file-system ordering)."""
        _make_workspace(
            tmp_path,
            ["pkg/z_last.py", "pkg/a_first.py", "pkg/m_middle.py"],
        )

        manager = QAManager(workspace_root=tmp_path)
        cfg = _project_scope_config(include_globs=["pkg/*.py"])

        with patch(
            "mcp_server.managers.qa_manager.QualityConfig.load",
            return_value=cfg,
        ):
            result = manager._resolve_scope("project")

        assert result == sorted(result)

    def test_project_scope_no_duplicates(self, tmp_path: Path) -> None:
        """Overlapping globs do not produce duplicate paths."""
        _make_workspace(tmp_path, ["src/util.py"])

        manager = QAManager(workspace_root=tmp_path)
        # Two overlapping globs both match src/util.py
        cfg = _project_scope_config(include_globs=["src/*.py", "src/util.py"])

        with patch(
            "mcp_server.managers.qa_manager.QualityConfig.load",
            return_value=cfg,
        ):
            result = manager._resolve_scope("project")

        assert result.count(result[0]) == 1 if result else True

    def test_project_scope_empty_globs_returns_empty(self, tmp_path: Path) -> None:
        """When include_globs is empty, scope=project returns []."""
        _make_workspace(tmp_path, ["mcp_server/foo.py"])

        manager = QAManager(workspace_root=tmp_path)
        cfg = _project_scope_config(include_globs=[])

        with patch(
            "mcp_server.managers.qa_manager.QualityConfig.load",
            return_value=cfg,
        ):
            result = manager._resolve_scope("project")

        assert result == []

    def test_project_scope_no_workspace_root_returns_empty(self) -> None:
        """When workspace_root is None, scope=project returns [] (graceful no-op)."""
        manager = QAManager(workspace_root=None)

        with patch(
            "mcp_server.managers.qa_manager.QualityConfig.load",
        ):
            result = manager._resolve_scope("project")

        assert result == []
