# tests/mcp_server/unit/mcp_server/managers/test_compact_payload_builder.py
"""
C26 + C35: _build_compact_result returns compact gate payload with violations only.

C26 design contract (design.md §4.9 / planning.md Cycle 26):
  Schema: {"overall_pass": bool, "duration_ms": int,
           "gates": [{"id": str, "passed": bool, "skipped": bool,
                      "status": str, "violations": list}]}

C35 additions (F-2, F-3):
  - Top-level `overall_pass` and `duration_ms` (F-2)
  - Per-gate `status` enum ("passed"|"failed"|"skipped") (F-3)
  No debug fields: stdout, stderr, raw_output, command, hints, skip_reason, score
"""
# pyright: reportPrivateUsage=false

from __future__ import annotations

from mcp_server.managers.qa_manager import QAManager


def _make_gate(
    name: str = "Gate 0: Ruff Format",
    passed: bool = True,
    status: str = "passed",
    issues: list | None = None,
    include_debug: bool = True,
) -> dict:
    """Build a gate dict as produced by _execute_gate (with debug fields)."""
    gate: dict = {
        "gate_number": 1,
        "id": 1,
        "name": name,
        "passed": passed,
        "status": status,
        "skip_reason": None,
        "score": "Pass" if passed else "Fail",
        "issues": issues or [],
    }
    if include_debug:
        gate["duration_ms"] = 145
        gate["command"] = {
            "executable": "python",
            "args": ["-m", "ruff"],
            "cwd": None,
            "exit_code": 0,
            "environment": {},
        }
    return gate


def _make_results(gates: list[dict]) -> dict:
    """Build a results dict with the given gates."""
    passed = sum(1 for g in gates if g.get("status") == "passed")
    failed = sum(1 for g in gates if g.get("status") == "failed")
    skipped = sum(1 for g in gates if g.get("status") == "skipped")
    return {
        "summary": {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total_violations": sum(len(g.get("issues", [])) for g in gates),
        },
        "gates": gates,
        "overall_pass": failed == 0,
        "timings": {"total": 145},
    }


class TestBuildCompactResultSchema:
    """Compact payload gate dicts have exactly: id, passed, skipped, violations."""

    def test_passed_gate_has_only_required_keys(self) -> None:
        """Compact gate dict must have exactly: id, passed, skipped, status, violations."""
        manager = QAManager(workspace_root=None)
        results = _make_results([_make_gate()])

        compact = manager._build_compact_result(results)

        assert "gates" in compact, "Compact payload must have 'gates' key"
        gate = compact["gates"][0]
        assert set(gate.keys()) == {"id", "passed", "skipped", "status", "violations"}

    def test_passed_gate_values(self) -> None:
        """Passed gate: passed=True, skipped=False, violations=[]."""
        manager = QAManager(workspace_root=None)
        results = _make_results([_make_gate(passed=True, status="passed")])

        compact = manager._build_compact_result(results)
        gate = compact["gates"][0]

        assert gate["passed"] is True
        assert gate["skipped"] is False
        assert gate["violations"] == []

    def test_skipped_gate_has_skipped_true(self) -> None:
        """Skipped gate: passed=True, skipped=True."""
        manager = QAManager(workspace_root=None)
        raw_gate = _make_gate(status="skipped")
        raw_gate["passed"] = True
        results = _make_results([raw_gate])

        compact = manager._build_compact_result(results)
        gate = compact["gates"][0]

        assert gate["skipped"] is True
        assert gate["passed"] is True

    def test_failed_gate_carries_violations(self) -> None:
        """Failed gate in compact output contains the violations list."""
        violations = [{"message": "E501 line too long", "file": "x.py", "line": 5}]
        manager = QAManager(workspace_root=None)
        raw_gate = _make_gate(passed=False, status="failed", issues=violations)
        results = _make_results([raw_gate])

        compact = manager._build_compact_result(results)
        gate = compact["gates"][0]

        assert gate["passed"] is False
        assert gate["violations"] == violations

    def test_id_is_string(self) -> None:
        """The id field in compact gate must be a string."""
        manager = QAManager(workspace_root=None)
        results = _make_results([_make_gate(name="Gate 0: Ruff Format")])

        compact = manager._build_compact_result(results)

        assert isinstance(compact["gates"][0]["id"], str), "id must be a string"


class TestBuildCompactResultNoDebugFields:
    """Debug fields must not appear in compact payload."""

    _FORBIDDEN: frozenset[str] = frozenset(
        {
            "stdout",
            "stderr",
            "raw_output",
            "command",
            "duration_ms",
            "hints",
            "skip_reason",
            "score",
        }
    )

    def test_gate_has_no_debug_fields(self) -> None:
        """command, duration_ms, score, skip_reason absent from compact gate."""
        manager = QAManager(workspace_root=None)
        results = _make_results([_make_gate(include_debug=True)])

        compact = manager._build_compact_result(results)
        gate_keys = set(compact["gates"][0].keys())

        for key in self._FORBIDDEN:
            assert key not in gate_keys, f"Forbidden key '{key}' found in compact gate"

    def test_compact_root_has_only_gates_key(self) -> None:
        """Compact payload root must contain exactly: 'gates' and 'overall_pass'.

        C39: 'duration_ms' was removed from compact root and moved to the summary line.
        """
        manager = QAManager(workspace_root=None)
        results = _make_results([_make_gate()])

        compact = manager._build_compact_result(results)

        assert set(compact.keys()) == {"gates", "overall_pass"}, (
            f"Unexpected root keys: {set(compact.keys())}"
        )


class TestBuildCompactResultMultiGate:
    """Multi-gate and edge-case scenarios."""

    def test_two_gates_produce_two_compact_gates(self) -> None:
        """Two gates in input → two gates in compact output."""
        manager = QAManager(workspace_root=None)
        gates = [
            _make_gate(name="Gate 0: Ruff Format"),
            _make_gate(name="Gate 1: Ruff Strict Lint"),
        ]
        results = _make_results(gates)

        compact = manager._build_compact_result(results)

        assert len(compact["gates"]) == 2

    def test_empty_gates_list_returns_empty(self) -> None:
        """Empty gates list in input → empty 'gates' list in compact output."""
        manager = QAManager(workspace_root=None)
        results = _make_results([])

        compact = manager._build_compact_result(results)

        assert compact["gates"] == []
        assert compact["overall_pass"] is True


class TestCompactPayloadF2TopLevelFields:
    """F-2: overall_pass must be present at the compact payload root.

    C39: duration_ms has been moved from 'compact JSON root' to the summary line text.
    These tests verify overall_pass and the absence of duration_ms from the root.
    """

    def test_overall_pass_true_when_no_failures(self) -> None:
        """overall_pass is True when all gates passed."""
        manager = QAManager(workspace_root=None)
        results = _make_results([_make_gate(passed=True, status="passed")])

        compact = manager._build_compact_result(results)

        assert "overall_pass" in compact, "overall_pass must be present in compact root"
        assert compact["overall_pass"] is True

    def test_overall_pass_false_when_gate_failed(self) -> None:
        """overall_pass is False when at least one gate failed."""
        manager = QAManager(workspace_root=None)
        results = _make_results([_make_gate(passed=False, status="failed")])

        compact = manager._build_compact_result(results)

        assert compact["overall_pass"] is False

    def test_overall_pass_true_when_all_skipped(self) -> None:
        """overall_pass is True when all gates are skipped (no failures)."""
        manager = QAManager(workspace_root=None)
        skipped_gate = _make_gate(status="skipped")
        skipped_gate["passed"] = True
        results = _make_results([skipped_gate])

        compact = manager._build_compact_result(results)

        assert compact["overall_pass"] is True

    def test_duration_ms_absent_from_compact_root(self) -> None:
        """C39: duration_ms must NOT be present in compact root (moved to summary line)."""
        manager = QAManager(workspace_root=None)
        results = _make_results([_make_gate()])

        compact = manager._build_compact_result(results)

        assert "duration_ms" not in compact, (
            "duration_ms must not be in compact root (C39: moved to summary line)"
        )

    def test_timings_total_not_leaked_to_compact_root(self) -> None:
        """timings.total must not appear as duration_ms in compact root regardless of value."""
        manager = QAManager(workspace_root=None)
        results = _make_results([_make_gate()])
        results["timings"] = {"total": 299}

        compact = manager._build_compact_result(results)

        assert "duration_ms" not in compact


class TestCompactPayloadF3GateStatusEnum:
    """F-3: Each gate entry in compact payload must have a 'status' enum field."""

    def test_passed_gate_has_status_passed(self) -> None:
        """A passing gate has status='passed'."""
        manager = QAManager(workspace_root=None)
        results = _make_results([_make_gate(passed=True, status="passed")])

        compact = manager._build_compact_result(results)

        assert compact["gates"][0]["status"] == "passed"

    def test_failed_gate_has_status_failed(self) -> None:
        """A failing gate has status='failed'."""
        manager = QAManager(workspace_root=None)
        results = _make_results([_make_gate(passed=False, status="failed")])

        compact = manager._build_compact_result(results)

        assert compact["gates"][0]["status"] == "failed"

    def test_skipped_gate_has_status_skipped(self) -> None:
        """A skipped gate has status='skipped'."""
        manager = QAManager(workspace_root=None)
        skipped = _make_gate(status="skipped")
        skipped["passed"] = True
        results = _make_results([skipped])

        compact = manager._build_compact_result(results)

        assert compact["gates"][0]["status"] == "skipped"

    def test_status_values_are_valid_enum(self) -> None:
        """All status values in a multi-gate result are within the valid enum."""
        valid = {"passed", "failed", "skipped"}
        manager = QAManager(workspace_root=None)
        skipped = _make_gate(name="Gate 2: Imports", status="skipped")
        skipped["passed"] = True
        gates = [
            _make_gate(name="Gate 0: Ruff Format", passed=True, status="passed"),
            _make_gate(name="Gate 1: Ruff Lint", passed=False, status="failed"),
            skipped,
        ]
        results = _make_results(gates)

        compact = manager._build_compact_result(results)

        for gate in compact["gates"]:
            assert gate["status"] in valid, f"Invalid status: {gate['status']!r}"
