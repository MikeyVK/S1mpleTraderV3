# tests/mcp_server/unit/managers/test_pytest_runner.py
"""Unit tests for PytestRunner — parser, exit-code classification, LF-cache detection.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.managers.pytest_runner]
"""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import pytest

from mcp_server.managers.pytest_runner import (
    FailureDetail,
    PytestResult,
    PytestRunner,
)

# ---------------------------------------------------------------------------
# Stdout fixtures
# ---------------------------------------------------------------------------

_PASSED_STDOUT = """\
============================= test session starts ==============================
collected 3 items

tests/test_foo.py::test_a PASSED
tests/test_foo.py::test_b PASSED
tests/test_foo.py::test_c PASSED

============================== 3 passed in 0.12s ==============================
"""

_FAILED_STDOUT = """\
============================= test session starts ==============================
collected 2 items

tests/test_foo.py::test_ok PASSED
tests/test_foo.py::test_bad FAILED

================================= FAILURES =================================
________________________________ test_bad __________________________________

    def test_bad():
>       assert 1 == 2
E       AssertionError: assert 1 == 2

tests/test_foo.py:10: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_foo.py::test_bad - AssertionError: assert 1 == 2
========================= 1 failed, 1 passed in 0.23s =========================
"""

_SKIPPED_STDOUT = """\
============================= test session starts ==============================
collected 2 items

tests/test_foo.py::test_a PASSED
tests/test_foo.py::test_skip SKIPPED (reason)

========================= 1 passed, 1 skipped in 0.10s =========================
"""

_ERRORS_STDOUT = """\
============================= test session starts ==============================
collected 0 items / 1 error

==================================== ERRORS ====================================
__________________ ERROR collecting tests/test_bad_import.py ___________________
ImportError: cannot import name 'missing'
========================= 1 error in 0.05s =========================
"""

_COVERAGE_STDOUT = """\
============================= test session starts ==============================
collected 1 items

tests/test_foo.py::test_a PASSED

---------- coverage: platform linux, python 3.12 ----------
TOTAL                                   250    10    96%

============================== 1 passed in 0.45s ==============================
"""

_LF_EMPTY_STDOUT = """\
============================= test session starts ==============================
run-last-failure: no previously failed tests, not deselecting.
collected 3 items

tests/test_foo.py::test_a PASSED

============================== 1 passed in 0.12s ==============================
"""

_EMPTY_STDOUT = ""

_NO_TESTS_STDOUT = """\
============================= test session starts ==============================
collected 0 items

============================ no tests ran in 0.01s ============================
"""


# ---------------------------------------------------------------------------
# Helper — construct PytestRunner and call _parse_output directly
# ---------------------------------------------------------------------------


def _parse(stdout: str, returncode: int) -> PytestResult:
    """Helper to exercise PytestRunner._parse_output for parser unit tests."""
    runner = PytestRunner()
    return runner._parse_output(stdout, returncode)  # noqa: SLF001


# ---------------------------------------------------------------------------
# Test cases (8 scenarios per design.md §3.10)
# ---------------------------------------------------------------------------


class TestPytestRunnerParser:
    """Parser unit tests — exercise _parse_output with raw stdout fixtures."""

    def test_all_passed(self) -> None:
        """Scenario 1: all-passed stdout → passed=N, failed=0, summary_line non-empty."""
        result = _parse(_PASSED_STDOUT, returncode=0)

        assert result.passed == 3
        assert result.failed == 0
        assert result.errors == 0
        assert result.failures == ()
        assert result.summary_line != ""
        assert result.exit_code == 0
        assert result.should_raise is False
        assert result.note is None

    def test_failing_tests(self) -> None:
        """Scenario 2: failing tests stdout → failures tuple populated with FailureDetail."""
        result = _parse(_FAILED_STDOUT, returncode=1)

        assert result.failed == 1
        assert result.passed == 1
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert isinstance(failure, FailureDetail)
        assert "test_bad" in failure.test_id
        assert result.should_raise is False
        assert result.note is None

    def test_skipped_tests(self) -> None:
        """Scenario 3: skipped tests stdout → skipped=N."""
        result = _parse(_SKIPPED_STDOUT, returncode=0)

        assert result.skipped == 1
        assert result.passed == 1
        assert result.failed == 0

    def test_errors_during_collection(self) -> None:
        """Scenario 4: errors-during-collection stdout → errors=N."""
        result = _parse(_ERRORS_STDOUT, returncode=2)

        assert result.errors >= 1

    def test_coverage_pct_parsed(self) -> None:
        """Scenario 5: coverage report line present → coverage_pct parsed as float."""
        result = _parse(_COVERAGE_STDOUT, returncode=0)

        assert result.coverage_pct is not None
        assert isinstance(result.coverage_pct, float)
        assert result.coverage_pct == pytest.approx(96.0)

    def test_lf_cache_was_empty(self) -> None:
        """Scenario 6: LF empty fallback message in stdout → lf_cache_was_empty=True."""
        result = _parse(_LF_EMPTY_STDOUT, returncode=0)

        assert result.lf_cache_was_empty is True

    def test_empty_stdout_summary_line_fallback(self) -> None:
        """Scenario 7: empty/unparseable stdout → summary_line falls back to policy; never empty."""
        result = _parse(_EMPTY_STDOUT, returncode=2)

        assert result.summary_line != ""
        assert result.should_raise is True

    def test_exit_code_5_no_tests_collected(self) -> None:
        """Scenario 8: exit code 5 path → summary_line == 'no tests collected'."""
        result = _parse(_NO_TESTS_STDOUT, returncode=5)

        assert result.summary_line == "no tests collected"
        assert result.should_raise is False
