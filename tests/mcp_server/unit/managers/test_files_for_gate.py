from __future__ import annotations

import pytest

from mcp_server.config.quality_config import (
    CapabilitiesMetadata,
    ExecutionConfig,
    QualityGate,
    SuccessCriteria,
)
from mcp_server.managers.qa_manager import QAManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXEC = ExecutionConfig(command=["ruff", "check"], timeout_seconds=10)
_SUCCESS = SuccessCriteria(exit_codes_ok=[0])


def _make_gate(file_types: list[str]) -> QualityGate:
    return QualityGate(
        name="test-gate",
        execution=_EXEC,
        success=_SUCCESS,
        capabilities=CapabilitiesMetadata(
            file_types=file_types,
            supports_autofix=False,
        ),
    )


def _pytest_gate() -> QualityGate:
    """Gate whose command contains 'pytest' → repo-scoped."""
    return QualityGate(
        name="pytest-gate",
        execution=ExecutionConfig(command=["python", "-m", "pytest"], timeout_seconds=60),
        success=_SUCCESS,
        capabilities=CapabilitiesMetadata(
            file_types=[".py"],
            supports_autofix=False,
        ),
    )


@pytest.fixture()
def manager() -> QAManager:
    return QAManager()


# ---------------------------------------------------------------------------
# Tests: extension filtering by file_types
# ---------------------------------------------------------------------------


class TestFilesForGateExtensionFiltering:
    """_files_for_gate must return only files matching gate.capabilities.file_types."""

    def test_py_gate_returns_only_py_files(self, manager: QAManager) -> None:
        """Gate with .py file_types excludes non-Python files."""
        gate = _make_gate([".py"])
        files = ["src/main.py", "src/types.ts", "README.md"]
        result = manager._files_for_gate(gate, files)
        assert result == ["src/main.py"]

    def test_ts_gate_returns_only_ts_files(self, manager: QAManager) -> None:
        """Gate with .ts file_types returns only TypeScript files."""
        gate = _make_gate([".ts"])
        files = ["src/main.py", "src/types.ts", "src/app.ts"]
        result = manager._files_for_gate(gate, files)
        assert result == ["src/types.ts", "src/app.ts"]

    def test_multiple_extensions_returns_all_matching(self, manager: QAManager) -> None:
        """Gate with [.py, .ts] returns both Python and TypeScript files."""
        gate = _make_gate([".py", ".ts"])
        files = ["a.py", "b.ts", "c.md", "d.yaml"]
        result = manager._files_for_gate(gate, files)
        assert result == ["a.py", "b.ts"]

    def test_no_matching_files_returns_empty(self, manager: QAManager) -> None:
        """Returns empty list when no files match the gate's file_types."""
        gate = _make_gate([".py"])
        files = ["config.yaml", "schema.json", "README.md"]
        result = manager._files_for_gate(gate, files)
        assert result == []

    def test_all_files_match_returns_all(self, manager: QAManager) -> None:
        """Returns all files when every file matches the gate's file_types."""
        gate = _make_gate([".py"])
        files = ["a.py", "b.py", "c.py"]
        result = manager._files_for_gate(gate, files)
        assert result == ["a.py", "b.py", "c.py"]

    def test_empty_input_returns_empty(self, manager: QAManager) -> None:
        """Returns empty list when no files are provided."""
        gate = _make_gate([".py"])
        result = manager._files_for_gate(gate, [])
        assert result == []


# ---------------------------------------------------------------------------
# Tests: stable ordering
# ---------------------------------------------------------------------------


class TestFilesForGateOrdering:
    """_files_for_gate must preserve input order (stable, deterministic)."""

    def test_preserves_input_order(self, manager: QAManager) -> None:
        """Matching files are returned in their original input order."""
        gate = _make_gate([".py"])
        files = ["z.py", "a.py", "m.py", "b.ts", "k.py"]
        result = manager._files_for_gate(gate, files)
        assert result == ["z.py", "a.py", "m.py", "k.py"]

    def test_order_stable_across_calls(self, manager: QAManager) -> None:
        """Multiple calls with same input return identical ordered results."""
        gate = _make_gate([".py"])
        files = ["z.py", "a.py", "m.py"]
        assert manager._files_for_gate(gate, files) == manager._files_for_gate(gate, files)


# ---------------------------------------------------------------------------
# Tests: repo-scoped (pytest) gate
# ---------------------------------------------------------------------------


class TestFilesForGatePytestGate:
    """After C17: _files_for_gate is purely capability-driven; no tool-name special cases."""

    def test_gate_filters_by_file_types_regardless_of_command(self, manager: QAManager) -> None:
        """A gate with file_types=['.py'] receives .py files; tool command is irrelevant."""
        gate = _pytest_gate()
        files = ["tests/test_foo.py", "tests/test_bar.py"]
        result = manager._files_for_gate(gate, files)
        assert result == ["tests/test_foo.py", "tests/test_bar.py"]
