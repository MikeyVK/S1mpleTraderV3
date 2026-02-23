# tests/mcp_server/unit/mcp_server/managers/test_summary_line_formatter.py
"""
C25: _format_summary_line produces a concise status line for pass/fail/skip outcomes.

Design contract (design.md §4.8):
  Pass:       "✅ Quality gates: N/N passed (0 violations)"
  Fail:       "❌ Quality gates: N/M passed — V violations in gate_id[, gate_id]"
  Skip+pass:  "⚠️ Quality gates: N/N active (S skipped)"
"""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from mcp_server.managers.qa_manager import QAManager


def _make_results(
    passed: int,
    failed: int,
    skipped: int,
    total_violations: int,
    failed_gate_names: list[str] | None = None,
) -> dict:
    """Build a minimal results dict matching the shape produced by run_quality_gates."""
    gates = []
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
    }


class TestFormatSummaryLinePass:
    """All gates pass — green emoji, N/N passed, 0 violations."""

    def test_all_pass_produces_green_line(self) -> None:
        """All gates pass, 0 violations → ✅ line."""
        manager = QAManager(workspace_root=None)
        results = _make_results(passed=5, failed=0, skipped=0, total_violations=0)

        line = manager._format_summary_line(results)

        assert line.startswith("✅"), f"Expected ✅ prefix, got: {line!r}"
        assert "5/5" in line, f"Expected '5/5' in: {line!r}"
        assert "0 violations" in line, f"Expected '0 violations' in: {line!r}"

    def test_all_pass_single_gate(self) -> None:
        """Single gate passes — N/N is 1/1."""
        manager = QAManager(workspace_root=None)
        results = _make_results(passed=1, failed=0, skipped=0, total_violations=0)

        line = manager._format_summary_line(results)

        assert "1/1" in line, f"Expected '1/1' in: {line!r}"
        assert "✅" in line


class TestFormatSummaryLineFail:
    """At least one gate fails — red emoji, N/M passed, violation count and gate names."""

    def test_one_failure_produces_red_line(self) -> None:
        """One gate fails — ❌ with violation count and gate name."""
        manager = QAManager(workspace_root=None)
        results = _make_results(
            passed=4,
            failed=1,
            skipped=0,
            total_violations=3,
            failed_gate_names=["Gate 0: Ruff Format"],
        )

        line = manager._format_summary_line(results)

        assert line.startswith("❌"), f"Expected ❌ prefix, got: {line!r}"
        assert "4/5" in line, f"Expected '4/5' passed ratio in: {line!r}"
        assert "3" in line, f"Expected violation count '3' in: {line!r}"
        assert "Gate 0: Ruff Format" in line, f"Expected gate name in: {line!r}"

    def test_multiple_failures_lists_all_gate_names(self) -> None:
        """Multiple failures — all failed gate names appear in the line."""
        manager = QAManager(workspace_root=None)
        results = _make_results(
            passed=3,
            failed=2,
            skipped=0,
            total_violations=5,
            failed_gate_names=["Gate 0: Ruff Format", "Gate 3: Line Length"],
        )

        line = manager._format_summary_line(results)

        assert "Gate 0: Ruff Format" in line
        assert "Gate 3: Line Length" in line
        assert "3/5" in line

    def test_fail_has_no_green_emoji(self) -> None:
        """Failed result must not contain ✅."""
        manager = QAManager(workspace_root=None)
        results = _make_results(
            passed=0, failed=1, skipped=0, total_violations=2,
            failed_gate_names=["Gate 1: Ruff Strict Lint"],
        )

        line = manager._format_summary_line(results)

        assert "✅" not in line, f"Green emoji must not appear in failure line: {line!r}"
        assert "❌" in line


class TestFormatSummaryLineSkip:
    """Some gates skipped, rest pass — warning emoji."""

    def test_skips_with_all_active_passing_produces_warning(self) -> None:
        """Passed=N active, skipped=S, failed=0 → ⚠️ line."""
        manager = QAManager(workspace_root=None)
        results = _make_results(passed=4, failed=0, skipped=1, total_violations=0)

        line = manager._format_summary_line(results)

        assert "⚠️" in line, f"Expected ⚠️ in skip+pass line, got: {line!r}"
        assert "1" in line, f"Expected skipped count '1' in: {line!r}"

    def test_skips_with_active_passing_no_red_emoji(self) -> None:
        """No failed gates — ❌ must not appear when only skipped."""
        manager = QAManager(workspace_root=None)
        results = _make_results(passed=3, failed=0, skipped=2, total_violations=0)

        line = manager._format_summary_line(results)

        assert "❌" not in line, f"Red emoji must not appear in skip-only line: {line!r}"

    def test_fail_takes_precedence_over_skip(self) -> None:
        """When both failed and skipped, ❌ takes precedence over ⚠️."""
        manager = QAManager(workspace_root=None)
        results = _make_results(
            passed=2,
            failed=1,
            skipped=1,
            total_violations=1,
            failed_gate_names=["Gate 4b: Pyright"],
        )

        line = manager._format_summary_line(results)

        assert "❌" in line, f"Expected ❌ when there are failures: {line!r}"
        assert "⚠️" not in line, f"⚠️ must not appear when failures exist: {line!r}"
