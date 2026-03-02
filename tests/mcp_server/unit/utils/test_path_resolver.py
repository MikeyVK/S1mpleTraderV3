# tests\mcp_server\unit\mcp_server\utils\test_path_resolver.py
# template=unit_test version=3d15d309 created=2026-02-27T06:07Z updated=
"""
Unit tests for mcp_server.utils.path_resolver.

Unit tests for resolve_input_paths utility (C34/F-9)

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.utils.path_resolver, unittest.mock]
@responsibilities:
    - Test TestResolveInputPaths functionality
    - Verify directory expansion, file preservation, deduplication and missing-path warnings
    - None
"""

# Standard library
from pathlib import Path

# Project modules
from mcp_server.utils.path_resolver import resolve_input_paths


class TestResolveInputPaths:
    """Unit tests for resolve_input_paths utility (C34/F-9).

    Verifies directory expansion, file preservation, deduplication and missing-path warnings.
    """

    def test_single_directory_expands_to_py_files(self, tmp_path: Path) -> None:
        """A directory input is expanded to all .py files within it."""
        pkg = tmp_path / "backend" / "dtos"
        pkg.mkdir(parents=True)
        (pkg / "causality.py").write_text("")
        (pkg / "product.py").write_text("")
        (pkg / "not_python.txt").write_text("")

        result, warnings = resolve_input_paths(["backend/dtos/"], tmp_path)

        assert sorted(result) == ["backend/dtos/causality.py", "backend/dtos/product.py"]
        assert warnings == []

    def test_mixed_file_and_directory(self, tmp_path: Path) -> None:
        """A mix of explicit file and directory is merged and deduplicated."""
        dtos = tmp_path / "backend" / "dtos"
        dtos.mkdir(parents=True)
        (dtos / "causality.py").write_text("")

        unit = tmp_path / "tests" / "unit"
        unit.mkdir(parents=True)
        (unit / "test_foo.py").write_text("")

        result, warnings = resolve_input_paths(
            ["backend/dtos/causality.py", "tests/unit/"], tmp_path
        )

        assert sorted(result) == [
            "backend/dtos/causality.py",
            "tests/unit/test_foo.py",
        ]
        assert warnings == []

    def test_nonexistent_path_produces_warning(self, tmp_path: Path) -> None:
        """A path that does not exist produces a warning and is excluded from results."""
        result, warnings = resolve_input_paths(["nonexistent/module.py"], tmp_path)

        assert result == []
        assert len(warnings) == 1
        assert "nonexistent/module.py" in warnings[0]

    def test_duplicate_paths_are_deduplicated(self, tmp_path: Path) -> None:
        """The same file listed twice (or via file + containing dir) appears once."""
        pkg = tmp_path / "mcp_server"
        pkg.mkdir(parents=True)
        (pkg / "server.py").write_text("")

        result, warnings = resolve_input_paths(
            ["mcp_server/server.py", "mcp_server/server.py"], tmp_path
        )

        assert result == ["mcp_server/server.py"]
        assert warnings == []

    def test_empty_input_returns_empty(self, tmp_path: Path) -> None:
        """Empty input list returns empty result and no warnings."""
        result, warnings = resolve_input_paths([], tmp_path)

        assert result == []
        assert warnings == []

    def test_directory_without_py_files_returns_empty_no_warning(self, tmp_path: Path) -> None:
        """A directory containing no .py files returns empty list (not a warning)."""
        empty_dir = tmp_path / "assets"
        empty_dir.mkdir()
        (empty_dir / "logo.png").write_text("")

        result, warnings = resolve_input_paths(["assets/"], tmp_path)

        assert result == []
        assert warnings == []
