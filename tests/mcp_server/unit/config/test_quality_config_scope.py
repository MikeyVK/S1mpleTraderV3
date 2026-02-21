"""Unit tests for GateScope model and scope filtering (QA Alignment)."""

from mcp_server.config.quality_config import GateScope


class TestGateScopeModel:
    """Test GateScope model validation."""

    def test_scope_with_includes_and_excludes(self) -> None:
        """GateScope should accept include and exclude globs."""
        scope = GateScope(
            include_globs=["backend/**/*.py", "mcp_server/**/*.py"], exclude_globs=["tests/**/*.py"]
        )

        assert len(scope.include_globs) == 2
        assert len(scope.exclude_globs) == 1
        assert "backend/**/*.py" in scope.include_globs
        assert "tests/**/*.py" in scope.exclude_globs

    def test_scope_with_includes_only(self) -> None:
        """GateScope should work with includes only (no excludes)."""
        scope = GateScope(include_globs=["mcp_server/**/*.py"])

        assert len(scope.include_globs) == 1
        assert not scope.exclude_globs

    def test_empty_scope_defaults(self) -> None:
        """Empty GateScope should default to empty lists."""
        scope = GateScope()

        assert scope.include_globs == []
        assert scope.exclude_globs == []


class TestScopeFiltering:
    """Test file filtering logic based on GateScope."""

    def test_filter_includes_matching_files(self) -> None:
        """Should include files matching include globs."""
        scope = GateScope(include_globs=["mcp_server/**/*.py"])
        files = ["mcp_server/config/quality_config.py", "tests/unit/test_qa.py", "backend/core.py"]

        filtered = scope.filter_files(files)

        assert len(filtered) == 1
        assert "mcp_server/config/quality_config.py" in filtered

    def test_filter_excludes_matching_files(self) -> None:
        """Should exclude files matching exclude globs."""
        scope = GateScope(include_globs=["**/*.py"], exclude_globs=["tests/**/*.py"])
        files = ["mcp_server/config/quality_config.py", "tests/unit/test_qa.py", "backend/core.py"]

        filtered = scope.filter_files(files)

        assert len(filtered) == 2
        assert "mcp_server/config/quality_config.py" in filtered
        assert "backend/core.py" in filtered
        assert "tests/unit/test_qa.py" not in filtered

    def test_empty_scope_returns_all_files(self) -> None:
        """Empty scope should return all files (no filtering)."""
        scope = GateScope()
        files = ["mcp_server/config/quality_config.py", "tests/unit/test_qa.py"]

        filtered = scope.filter_files(files)

        assert len(filtered) == 2
        assert set(filtered) == set(files)

    def test_windows_paths_normalized_to_posix(self) -> None:
        """Should handle Windows backslash paths."""
        scope = GateScope(include_globs=["mcp_server/**/*.py"])
        files = [r"mcp_server\config\quality_config.py", r"tests\unit\test_qa.py"]

        filtered = scope.filter_files(files)

        assert len(filtered) == 1
        # Normalized to POSIX for matching
        assert any("quality_config.py" in f for f in filtered)
