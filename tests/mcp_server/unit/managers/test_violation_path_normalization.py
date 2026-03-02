# tests/mcp_server/unit/managers/test_violation_path_normalization.py
"""
C36 REFACTOR: Violation file path normalization (F-15).

Planning C36 / state cycle 37:
  Normalize all violation `file` fields to workspace-relative POSIX in
  _normalize_file_path so that all gates expose the same canonical format.

Exit criteria:
  - All violation file fields in a compact payload use the same POSIX-relative format.
  - Integration test: Gate 0 (text_violations) + Gate 1 (json_violations) for the
    same file produce identical file field values after normalization.
  - No absolute paths in compact payload.
"""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from pathlib import Path

from mcp_server.managers.qa_manager import QAManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WORKSPACE = Path("D:/dev/SimpleTraderV3")
_REL_FILE = "mcp_server/utils/path_resolver.py"
# Same file, different representations:
_ABS_WIN = r"D:\dev\SimpleTraderV3\mcp_server\utils\path_resolver.py"
_ABS_POSIX = "D:/dev/SimpleTraderV3/mcp_server/utils/path_resolver.py"
_REL_BACKSLASH = r"mcp_server\utils\path_resolver.py"


def _make_manager(workspace_root: Path = _WORKSPACE) -> QAManager:
    return QAManager(workspace_root=workspace_root)


def _make_gate_result(name: str, issues: list[dict]) -> dict:
    return {
        "gate_number": 1,
        "id": 1,
        "name": name,
        "passed": len(issues) == 0,
        "status": "failed" if issues else "passed",
        "issues": issues,
        "score": "Pass" if not issues else f"Fail ({len(issues)})",
        "duration_ms": 42,
    }


def _make_results(gates: list[dict]) -> dict:
    failed = sum(1 for g in gates if g.get("status") == "failed")
    return {
        "summary": {"passed": 0, "failed": failed, "skipped": 0, "total_violations": 0},
        "gates": gates,
        "overall_pass": failed == 0,
        "timings": {"total": 99},
    }


# ---------------------------------------------------------------------------
# Unit tests for _normalize_file_path
# ---------------------------------------------------------------------------


class TestNormalizeFilePath:
    """_normalize_file_path converts any path form to workspace-relative POSIX."""

    def test_absolute_windows_path_becomes_relative_posix(self) -> None:
        """Absolute Windows path is made relative to workspace_root and POSIX formatted."""
        manager = _make_manager()

        result = manager._normalize_file_path(_ABS_WIN)

        assert result == _REL_FILE, f"Expected '{_REL_FILE}', got '{result}'"

    def test_absolute_posix_path_becomes_relative_posix(self) -> None:
        """Absolute POSIX-form path is made relative to workspace_root."""
        manager = _make_manager()

        result = manager._normalize_file_path(_ABS_POSIX)

        assert result == _REL_FILE

    def test_relative_backslash_path_becomes_posix(self) -> None:
        """Relative Windows backslash path is converted to forward-slash POSIX form."""
        manager = _make_manager()

        result = manager._normalize_file_path(_REL_BACKSLASH)

        assert result == _REL_FILE

    def test_already_relative_posix_is_unchanged(self) -> None:
        """A path that is already workspace-relative POSIX is returned as-is."""
        manager = _make_manager()

        result = manager._normalize_file_path(_REL_FILE)

        assert result == _REL_FILE

    def test_none_returns_none(self) -> None:
        """None file path is passed through as None."""
        manager = _make_manager()

        result = manager._normalize_file_path(None)

        assert result is None

    def test_no_workspace_root_returns_posix_separators_only(self) -> None:
        """When workspace_root is absent, absolute path cannot be made relative.

        The method must still convert OS separators to POSIX and leave the path
        unchanged in terms of relativity (best-effort).
        """
        manager = QAManager(workspace_root=None)

        result = manager._normalize_file_path(_REL_BACKSLASH)

        assert result is not None
        assert "\\" not in result, f"Backslashes remain in result: {result!r}"


# ---------------------------------------------------------------------------
# Integration tests: compact payload path normalization
# ---------------------------------------------------------------------------


class TestCompactPayloadPathNormalization:
    """Compact payload violation file fields are normalized before output."""

    def test_absolute_violation_path_normalized_in_compact(self) -> None:
        """Gate violation with absolute Windows path produces relative POSIX in compact."""
        manager = _make_manager()
        gates = [
            _make_gate_result(
                "Gate 0: Ruff Format",
                [
                    {
                        "file": _ABS_WIN,
                        "message": "E501 line too long",
                        "line": 1,
                        "col": 1,
                        "rule": "E501",
                        "severity": "error",
                        "fixable": False,
                    }
                ],
            )
        ]
        results = _make_results(gates)

        compact = manager._build_compact_result(results)

        file_val = compact["gates"][0]["violations"][0]["file"]
        assert file_val == _REL_FILE, (
            f"Expected normalized POSIX path '{_REL_FILE}', got '{file_val}'"
        )

    def test_gate0_and_gate1_same_file_identical_path_in_compact(self) -> None:
        """Gate 0 (Windows abs path) and Gate 1 (POSIX abs path) for same file
        both produce the same canonical relative POSIX value in compact payload.

        This is the primary integration scenario for F-15.
        """
        manager = _make_manager()
        # Gate 0 (text_violations style) produces Windows absolute path
        gate0 = _make_gate_result(
            "Gate 0: Ruff Format",
            [
                {
                    "file": _ABS_WIN,
                    "message": "W291 trailing whitespace",
                    "line": 5,
                    "col": 20,
                    "rule": "W291",
                    "severity": "warning",
                    "fixable": True,
                }
            ],
        )
        # Gate 1 (json_violations style) produces POSIX absolute path
        gate1 = _make_gate_result(
            "Gate 1: Ruff Lint",
            [
                {
                    "file": _ABS_POSIX,
                    "message": "F401 unused import",
                    "line": 3,
                    "col": 1,
                    "rule": "F401",
                    "severity": "error",
                    "fixable": False,
                }
            ],
        )
        results = _make_results([gate0, gate1])

        compact = manager._build_compact_result(results)

        file_gate0 = compact["gates"][0]["violations"][0]["file"]
        file_gate1 = compact["gates"][1]["violations"][0]["file"]
        assert file_gate0 == file_gate1, (
            f"Paths diverge: gate0={file_gate0!r}, gate1={file_gate1!r}. "
            "Both should be normalized to the same workspace-relative POSIX form."
        )
        assert file_gate0 == _REL_FILE

    def test_no_absolute_paths_in_compact_payload(self) -> None:
        """No violation file field in compact payload starts with a drive letter or /."""
        manager = _make_manager()
        gates = [
            _make_gate_result(
                "Gate 0: Ruff Format",
                [
                    {
                        "file": _ABS_WIN,
                        "message": "E501",
                        "line": 1,
                        "col": 1,
                        "rule": "E501",
                        "severity": "error",
                        "fixable": False,
                    },
                    {
                        "file": _ABS_POSIX,
                        "message": "W291",
                        "line": 2,
                        "col": 1,
                        "rule": "W291",
                        "severity": "warning",
                        "fixable": True,
                    },
                ],
            ),
        ]
        results = _make_results(gates)

        compact = manager._build_compact_result(results)

        for gate in compact["gates"]:
            for violation in gate["violations"]:
                f = violation.get("file", "")
                if f is None:
                    continue
                assert not Path(f).is_absolute(), f"Absolute path found in compact payload: {f!r}"

    def test_relative_backslash_violation_normalized_in_compact(self) -> None:
        """Windows-relative backslash path in violation becomes POSIX in compact."""
        manager = _make_manager()
        gates = [
            _make_gate_result(
                "Gate 1: Ruff Lint",
                [
                    {
                        "file": _REL_BACKSLASH,
                        "message": "F401",
                        "line": 1,
                        "col": 1,
                        "rule": "F401",
                        "severity": "error",
                        "fixable": False,
                    }
                ],
            )
        ]
        results = _make_results(gates)

        compact = manager._build_compact_result(results)

        file_val = compact["gates"][0]["violations"][0]["file"]
        assert "\\" not in (file_val or ""), (
            f"Backslash still present after normalization: {file_val!r}"
        )
        assert file_val == _REL_FILE
