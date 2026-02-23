# tests/mcp_server/unit/mcp_server/managers/test_scope_resolution.py
"""
C21: Resolve scope=project from project_scope globs (expand globs against workspace root).
C22: Resolve scope=branch using git diff parent..HEAD.
"""
# pyright: reportPrivateUsage=false

from __future__ import annotations

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
