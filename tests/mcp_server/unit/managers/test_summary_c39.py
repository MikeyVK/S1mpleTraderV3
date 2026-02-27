"""C39 RED — Summary-line clarity + message sanitation (F-1, F-18, F-19, duration_ms).

Four distinct failures targeted by this cycle:

F-1:  All-gates-skipped emits ⚠️ but should emit ✅ (clean empty-diff state).
F-19: Summary line lacks any scope-resolution context (scope name, file count).
      planning: include scope for all inputs (auto, branch, project, files).
duration_ms: Summary line missing; present in compact JSON root (should be reversed).
F-18: Gate 4b (Pyright) messages verbatim — contain \\n and \\u00a0 from pyright JSON.
"""

from __future__ import annotations

import pytest

from mcp_server.config.quality_config import JsonViolationsParsing
from mcp_server.managers.qa_manager import QAManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_summary_results(
    passed: int,
    failed: int,
    skipped: int,
    total_violations: int = 0,
    failed_gate_names: list[str] | None = None,
    duration_total_ms: int = 0,
) -> dict:
    """Minimal results dict compatible with _format_summary_line."""
    gates: list[dict] = []
    for name in failed_gate_names or []:
        gates.append({"name": name, "status": "failed", "issues": []})
    return {
        "summary": {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total_violations": total_violations,
        },
        "gates": gates,
        "overall_pass": failed == 0,
        "timings": {"total": duration_total_ms},
    }


def _make_compact_results(duration_total_ms: int = 145) -> dict:
    """Minimal full results dict for _build_compact_result."""
    return {
        "summary": {"passed": 1, "failed": 0, "skipped": 0, "total_violations": 0},
        "gates": [
            {
                "gate_number": 1,
                "name": "Gate 0: Ruff Format",
                "passed": True,
                "status": "passed",
                "issues": [],
            }
        ],
        "overall_pass": True,
        "timings": {"total": duration_total_ms},
    }


# ---------------------------------------------------------------------------
# F-1: all-skipped should emit ✅ not ⚠️
# ---------------------------------------------------------------------------


class TestAllSkippedSummarySignal:
    """F-1: all gates skipped (empty diff) → green checkmark, not warning."""

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager(workspace_root=None)

    def test_all_skipped_emits_green_checkmark(self, manager: QAManager) -> None:
        """When every gate is skipped, summary must start with ✅."""
        results = _make_summary_results(passed=0, failed=0, skipped=5)
        line = manager._format_summary_line(results)
        assert line.startswith("✅"), f"All-skipped state must emit ✅ (clean state), got: {line!r}"

    def test_all_skipped_does_not_emit_warning(self, manager: QAManager) -> None:
        """When every gate is skipped, ⚠️ must NOT appear."""
        results = _make_summary_results(passed=0, failed=0, skipped=5)
        line = manager._format_summary_line(results)
        assert "⚠️" not in line, f"⚠️ must not appear for all-skipped clean state, got: {line!r}"

    def test_partial_skip_still_emits_warning(self, manager: QAManager) -> None:
        """Some active gates passed + some skipped → still ⚠️ (not all-skipped)."""
        results = _make_summary_results(passed=3, failed=0, skipped=2)
        line = manager._format_summary_line(results)
        assert "⚠️" in line, f"Partial-skip state (some passed) must still emit ⚠️, got: {line!r}"


# ---------------------------------------------------------------------------
# F-19: scope context in summary line
# ---------------------------------------------------------------------------


class TestScopeSummaryContext:
    """F-19: summary line must include scope + file-count context when scope is given."""

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager(workspace_root=None)

    def test_summary_with_auto_scope_contains_scope_name(self, manager: QAManager) -> None:
        """scope='auto' → 'auto' appears in summary line."""
        results = _make_summary_results(passed=5, failed=0, skipped=0)
        line = manager._format_summary_line(results, scope="auto", file_count=3)
        assert "auto" in line, f"Expected 'auto' in summary when scope='auto', got: {line!r}"

    def test_summary_contains_file_count(self, manager: QAManager) -> None:
        """file_count=3 → '3 files' (or similar) appears in summary."""
        results = _make_summary_results(passed=5, failed=0, skipped=0)
        line = manager._format_summary_line(results, scope="branch", file_count=7)
        assert "7" in line, f"Expected file count '7' in summary, got: {line!r}"

    def test_summary_without_scope_omits_scope_context(self, manager: QAManager) -> None:
        """When scope is None (not passed), no scope annotation in summary."""
        results = _make_summary_results(passed=5, failed=0, skipped=0)
        line = manager._format_summary_line(results)
        # Should not crash AND should not include 'None' in the output
        assert "None" not in line, f"'None' must not appear in summary, got: {line!r}"


# ---------------------------------------------------------------------------
# duration_ms: in summary line, absent from compact JSON root
# ---------------------------------------------------------------------------


class TestDurationMs:
    """duration_ms must appear in the summary line and NOT in the compact JSON root."""

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager(workspace_root=None)

    def test_summary_line_contains_duration_ms(self, manager: QAManager) -> None:
        """Summary line must include duration_ms (e.g. '— 1234ms')."""
        results = _make_summary_results(passed=5, failed=0, skipped=0, duration_total_ms=1234)
        line = manager._format_summary_line(results)
        assert "1234ms" in line, f"Expected '1234ms' in summary line, got: {line!r}"

    def test_compact_root_has_no_duration_ms(self, manager: QAManager) -> None:
        """Compact JSON payload root must NOT contain 'duration_ms' key."""
        results = _make_compact_results(duration_total_ms=145)
        compact = manager._build_compact_result(results)
        assert "duration_ms" not in compact, (
            f"'duration_ms' must be removed from compact JSON root, keys: {set(compact.keys())}"
        )

    def test_compact_root_has_only_overall_pass_and_gates(self, manager: QAManager) -> None:
        """Compact root must have exactly: 'overall_pass' and 'gates'."""
        results = _make_compact_results()
        compact = manager._build_compact_result(results)
        assert set(compact.keys()) == {"overall_pass", "gates"}, (
            f"Unexpected compact root keys: {set(compact.keys())}"
        )


# ---------------------------------------------------------------------------
# F-18: Pyright message sanitation
# ---------------------------------------------------------------------------


_PYRIGHT_MSG_WITH_NOISE = (
    'Type "str" is not assignable to declared type "int"\n'
    "\u00a0\u00a0\u00a0\u00a0"
    '"str" is not assignable to "int"'
)

_PYRIGHT_PARSING_STRICT = JsonViolationsParsing(
    field_map={
        "file": "file",
        "line": "range/start/line",
        "col": "range/start/character",
        "message": "message",
        "rule": "rule",
        "severity": "severity",
    },
    line_offset=1,
)


class TestPyrightMessageSanitation:
    """F-18: Pyright multi-line messages must be normalized to a single clean line."""

    @pytest.fixture
    def manager(self) -> QAManager:
        return QAManager(workspace_root=None)

    def test_newline_not_in_sanitized_message(self, manager: QAManager) -> None:
        """After parsing, ViolationDTO.message must not contain \\n."""
        payload = [
            {
                "file": "backend/dtos/x.py",
                "severity": "error",
                "message": _PYRIGHT_MSG_WITH_NOISE,
                "range": {"start": {"line": 5, "character": 4}, "end": {"line": 5, "character": 8}},
                "rule": "reportAssignmentType",
            }
        ]
        result = manager._parse_json_violations(payload, _PYRIGHT_PARSING_STRICT)
        assert "\n" not in result[0].message, (
            f"\\n must be sanitized from message, got: {result[0].message!r}"
        )

    def test_nbsp_not_in_sanitized_message(self, manager: QAManager) -> None:
        """After parsing, ViolationDTO.message must not contain \\u00a0 (non-breaking space)."""
        payload = [
            {
                "file": "backend/dtos/x.py",
                "severity": "error",
                "message": _PYRIGHT_MSG_WITH_NOISE,
                "range": {"start": {"line": 5, "character": 4}, "end": {"line": 5, "character": 8}},
                "rule": "reportAssignmentType",
            }
        ]
        result = manager._parse_json_violations(payload, _PYRIGHT_PARSING_STRICT)
        assert "\u00a0" not in result[0].message, (
            f"\\u00a0 must be sanitized from message, got: {result[0].message!r}"
        )

    def test_message_is_single_line_with_em_dash_separator(self, manager: QAManager) -> None:
        """The secondary type annotation line is preserved as ' — secondary' suffix."""
        payload = [
            {
                "file": "backend/dtos/x.py",
                "severity": "error",
                "message": _PYRIGHT_MSG_WITH_NOISE,
                "range": {"start": {"line": 5, "character": 4}, "end": {"line": 5, "character": 8}},
                "rule": "reportAssignmentType",
            }
        ]
        result = manager._parse_json_violations(payload, _PYRIGHT_PARSING_STRICT)
        msg = result[0].message
        # Must be a single line (no newlines) and secondary part preserved via ' — '
        assert "\n" not in msg
        assert " — " in msg, f"Expected em-dash separator in sanitized message, got: {msg!r}"
