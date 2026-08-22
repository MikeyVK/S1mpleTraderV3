# tests/mcp_server/unit/managers/test_pytest_runner.py
"""Unit tests for PytestRunner ÔÇö parser, exit-code classification, LF-cache detection.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.managers.pytest_runner]
"""

from __future__ import annotations

import subprocess

import pytest

import mcp_server.managers.pytest_runner as pytest_runner_module
from mcp_server.core.operation_notes import Note
from mcp_server.managers.pytest_runner import FailureDetail, PytestResult, PytestRunner

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
Name                                   Stmts   Miss Branch BrPart  Cover
TOTAL                                    250     10     40      4    96%

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
# Helper ÔÇö exercise public PytestRunner.run() with a controlled subprocess seam
# ---------------------------------------------------------------------------


def _run(
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    returncode: int,
    *,
    stderr: str = "",
    verbose: bool = False,
) -> PytestResult:
    """Helper to exercise PytestRunner.run() through a controlled subprocess seam."""
    completed: subprocess.CompletedProcess[str] = subprocess.CompletedProcess(
        args=["pytest"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )

    def fake_run(
        cmd: list[str],
        *,
        capture_output: bool,
        check: bool,
        creationflags: int,
        cwd: str,
        env: dict[str, str],
        stdin: int,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        assert cmd == ["pytest"]
        assert capture_output is True
        assert check is False
        assert creationflags >= 0
        assert cwd == "."
        assert env["PYTHONUNBUFFERED"] == "1"
        assert stdin == subprocess.DEVNULL
        assert text is True
        assert timeout == 30
        return completed

    monkeypatch.setattr(pytest_runner_module.subprocess, "run", fake_run)
    return PytestRunner().run(["pytest"], cwd=".", timeout=30, verbose=verbose)


# ---------------------------------------------------------------------------
# Test cases (8 scenarios per design.md ┬º3.10)
# ---------------------------------------------------------------------------


class TestPytestRunnerRun:
    """Runner unit tests ÔÇö exercise the public run() surface only."""

    def test_all_passed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Scenario 1: all-passed stdout exposes counts and numeric duration."""
        result = _run(monkeypatch, _PASSED_STDOUT, returncode=0)

        assert result.passed == 3
        assert result.failed == 0
        assert result.errors == 0
        assert result.failures == ()
        assert result.duration_seconds == pytest.approx(0.12)
        assert result.exit_code == 0
        assert result.should_raise is False
        assert result.note is None

    def test_failing_tests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Scenario 2: failing tests stdout ÔåÆ failures tuple populated with FailureDetail."""
        result = _run(monkeypatch, _FAILED_STDOUT, returncode=1)

        assert result.failed == 1
        assert result.passed == 1
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert isinstance(failure, FailureDetail)
        assert "test_bad" in failure.test_id
        assert result.should_raise is False
        assert result.note is None

    def test_skipped_tests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Scenario 3: skipped tests stdout ÔåÆ skipped=N."""
        result = _run(monkeypatch, _SKIPPED_STDOUT, returncode=0)

        assert result.skipped == 1
        assert result.passed == 1
        assert result.failed == 0

    def test_errors_during_collection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Scenario 4: errors-during-collection stdout ÔåÆ errors=N."""
        result = _run(monkeypatch, _ERRORS_STDOUT, returncode=2, verbose=True)

        assert result.errors >= 1
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert failure.test_id == "tests/test_bad_import.py"
        assert failure.location == "tests/test_bad_import.py"
        assert failure.short_reason == "ImportError: cannot import name 'missing'"
        assert "cannot import name 'missing'" in failure.traceback
        assert failure.is_collection_error is True

    def test_errors_during_collection_non_verbose(self, monkeypatch: pytest.MonkeyPatch) -> None:
        result = _run(monkeypatch, _ERRORS_STDOUT, returncode=2, verbose=False)

        assert result.errors >= 1
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert failure.test_id == "tests/test_bad_import.py"
        assert failure.location == "tests/test_bad_import.py"
        assert failure.short_reason == "ImportError: cannot import name 'missing'"
        assert failure.traceback == ""
        assert failure.is_collection_error is True

    def test_coverage_pct_parsed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Scenario 5: coverage report line present ÔåÆ coverage_pct parsed as float."""
        result = _run(monkeypatch, _COVERAGE_STDOUT, returncode=0)

        assert result.coverage_pct is not None
        assert isinstance(result.coverage_pct, float)
        assert result.coverage_pct == pytest.approx(96.0)

    def test_lf_cache_was_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Scenario 6: LF empty fallback message in stdout ÔåÆ lf_cache_was_empty=True."""
        result = _run(monkeypatch, _LF_EMPTY_STDOUT, returncode=0)

        assert result.lf_cache_was_empty is True

    def test_empty_stdout_has_no_duration(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Scenario 7: empty stdout has no synthesized presentation data."""
        result = _run(monkeypatch, _EMPTY_STDOUT, returncode=2)

        assert result.duration_seconds is None
        assert result.should_raise is False
        assert result.is_error is True

    def test_exit_code_5_no_tests_collected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Scenario 8: exit code 5 retains parsed duration and recovery note."""
        result = _run(monkeypatch, _NO_TESTS_STDOUT, returncode=5)

        assert result.duration_seconds == pytest.approx(0.01)
        assert result.should_raise is False
        assert isinstance(result.note, Note)

    def test_c1_pytest_runner_run_accepts_verbose_kwarg(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """PytestRunner.run accepts verbose keyword-only argument."""
        completed = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=0,
            stdout=_PASSED_STDOUT,
            stderr="",
        )
        monkeypatch.setattr(
            pytest_runner_module.subprocess,
            "run",
            lambda *_args, **_kwargs: completed,
        )
        result_verbose = PytestRunner().run(["pytest"], cwd=".", timeout=30, verbose=True)
        assert result_verbose.exit_code == 0
        result_non_verbose = PytestRunner().run(["pytest"], cwd=".", timeout=30, verbose=False)
        assert result_non_verbose.exit_code == 0


# ---------------------------------------------------------------------------
# C1 ÔÇö ExitCodePolicy + PytestResult contract
# ---------------------------------------------------------------------------


class TestC1ExitCodePolicyAndPytestResultContract:
    """C1: three-value Literal in ExitCodePolicy + PytestResult.is_error + PytestResult.stderr."""

    def test_c1_parse_output_exit2_sets_is_error_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exit 2 (INTERRUPTED) ÔåÆ result.is_error=True, result.should_raise=False."""
        result = _run(monkeypatch, _EMPTY_STDOUT, returncode=2)

        assert result.is_error is True
        assert result.should_raise is False

    def test_c1_parse_output_exit3_sets_is_error_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exit 3 (INTERNAL_ERROR) ÔåÆ result.is_error=True."""
        result = _run(monkeypatch, _EMPTY_STDOUT, returncode=3)

        assert result.is_error is True
        assert result.should_raise is False

    def test_c1_parse_output_exit4_sets_is_error_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exit 4 (USAGE_ERROR) ÔåÆ result.is_error=True."""
        result = _run(monkeypatch, _EMPTY_STDOUT, returncode=4)

        assert result.is_error is True
        assert result.should_raise is False

    def test_c1_parse_output_exit0_sets_is_error_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exit 0 (ALL_PASSED) ÔåÆ result.is_error=False."""
        result = _run(monkeypatch, _PASSED_STDOUT, returncode=0)

        assert result.is_error is False
        assert result.should_raise is False

    def test_c1_parse_output_exit99_should_raise_unchanged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exit 99 (unknown) ÔåÆ result.should_raise=True, result.is_error=False ÔÇö RNF-5 gate."""
        result = _run(monkeypatch, _EMPTY_STDOUT, returncode=99)

        assert result.should_raise is True
        assert result.is_error is False

    def test_c1_pytest_result_default_stderr_is_empty_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PytestResult constructed without explicit stderr kwarg ÔåÆ result.stderr == ''."""
        result = _run(monkeypatch, _PASSED_STDOUT, returncode=0)

        assert result.stderr == ""


# ---------------------------------------------------------------------------
# C2 ÔÇö stderr pipeline: run() ÔåÆ _parse_output() ÔåÆ PytestResult.stderr
# ---------------------------------------------------------------------------


class TestC2StderrPipeline:
    """C2: execution.stderr is wired through run() ÔåÆ _parse_output() ÔåÆ PytestResult.stderr."""

    def test_c2_run_populates_result_stderr(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-empty stderr from subprocess ÔåÆ result.stderr carries the value."""
        result = _run(monkeypatch, _PASSED_STDOUT, returncode=0, stderr="some error text")

        assert result.stderr == "some error text"

    def test_c2_run_empty_stderr_gives_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty stderr from subprocess ÔåÆ result.stderr == ''."""
        result = _run(monkeypatch, _PASSED_STDOUT, returncode=0, stderr="")

        assert result.stderr == ""

    def test_c2_stderr_multiline_preserved_in_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Multi-line stderr ÔåÆ result.stderr contains all lines joined by newlines."""
        multiline = "line one\nline two\nline three"
        result = _run(monkeypatch, _EMPTY_STDOUT, returncode=2, stderr=multiline)

        assert result.stderr == multiline


# ---------------------------------------------------------------------------
# C4 xdist fixtures ÔÇö FAILURES header has [gwN] prefix before underscores
# ---------------------------------------------------------------------------

_XDIST_FAILED_STDOUT_GW0 = """\
============================= test session starts ==============================
collected 2 items

tests/test_foo.py::test_ok PASSED
tests/test_foo.py::test_bad FAILED

================================= FAILURES =================================
[gw0] _________________________ test_bad __________________________

    def test_bad():
>       assert 1 == 2
E       AssertionError: assert 1 == 2

tests/test_foo.py:10: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_foo.py::test_bad - AssertionError: assert 1 == 2
========================= 1 failed, 1 passed in 0.23s =========================
"""

_XDIST_FAILED_STDOUT_GW12 = """\
============================= test session starts ==============================
collected 2 items

tests/test_foo.py::test_ok PASSED
tests/test_foo.py::test_bad FAILED

================================= FAILURES =================================
[gw12] _________________________ test_bad __________________________

    def test_bad():
>       assert 1 == 2
E       AssertionError: assert 1 == 2

tests/test_foo.py:10: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_foo.py::test_bad - AssertionError: assert 1 == 2
========================= 1 failed, 1 passed in 0.23s =========================
"""


# ---------------------------------------------------------------------------
# C4 ÔÇö xdist _extract_traceback() regex fix: optional [gwN] prefix
# ---------------------------------------------------------------------------


class TestC4XdistTracebackExtraction:
    """C4: _extract_traceback handles optional [gwN] worker prefix in FAILURES header."""

    def test_c4_extract_traceback_with_xdist_prefix_gw0(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """xdist stdout with [gw0] prefix on FAILURES header ÔåÆ traceback non-empty."""
        result = _run(monkeypatch, _XDIST_FAILED_STDOUT_GW0, returncode=1, verbose=True)

        assert len(result.failures) == 1
        assert result.failures[0].traceback != ""

    def test_c4_extract_traceback_with_xdist_prefix_gw12(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """xdist stdout with double-digit [gw12] prefix ÔåÆ traceback non-empty."""
        result = _run(monkeypatch, _XDIST_FAILED_STDOUT_GW12, returncode=1, verbose=True)

        assert len(result.failures) == 1
        assert result.failures[0].traceback != ""

    def test_c4_extract_traceback_without_prefix_unchanged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Standard (non-xdist) FAILURES header ÔåÆ traceback still extracted (regression guard)."""
        result = _run(monkeypatch, _FAILED_STDOUT, returncode=1, verbose=True)

        assert len(result.failures) == 1
        assert result.failures[0].traceback != ""

    def test_extract_traceback_windows_crlf_and_dots(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify traceback extraction on Windows with CRLF and class-method dot separator."""
        crlf_stdout = (
            "============================= FAILURES =============================\r\n"
            "________________ TestClass.test_method ________________\r\n"
            "\r\n"
            "    def test_method():\r\n"
            ">       assert False\r\n"
            "E       AssertionError: assert False\r\n"
            "\r\n"
            "tests/test_foo.py:10: AssertionError\r\n"
            "=========================== short test summary info ===========================\r\n"
            "FAILED tests/test_foo.py::TestClass::test_method - AssertionError: assert False\r\n"
        )
        result = _run(monkeypatch, crlf_stdout, returncode=1, verbose=True)
        assert len(result.failures) == 1
        failure = result.failures[0]
        assert failure.test_id == "tests/test_foo.py::TestClass::test_method"
        assert "AssertionError: assert False" in failure.traceback
        assert failure.short_reason == "AssertionError: assert False"


# ---------------------------------------------------------------------------
# Pytest 9 format: short summary has NO "- reason" suffix
# ---------------------------------------------------------------------------

_PYTEST9_FAILED_STDOUT = """\
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
FAILED tests/test_foo.py::test_bad
========================= 1 failed, 1 passed in 0.23s =========================
"""

_PYTEST9_XDIST_FAILED_STDOUT = """\
============================= test session starts ==============================
collected 2 items

tests/test_foo.py::test_ok PASSED
tests/test_foo.py::test_bad FAILED

================================= FAILURES =================================
[gw0] _________________________ test_bad __________________________

    def test_bad():
>       assert 1 == 2
E       AssertionError: assert 1 == 2

tests/test_foo.py:10: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_foo.py::test_bad
========================= 1 failed, 1 passed in 0.23s =========================
"""


class TestPytest9FailedLineFormat:
    """Regression tests for pytest 9 short-summary format (no '- reason' suffix).

    In pytest 9, 'FAILED test_id - reason' became 'FAILED test_id'.
    _parse_failures() must still return a populated FailureDetail with
    a non-empty short_reason derived from the traceback.
    """

    def test_failures_populated_without_reason_suffix(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """pytest 9 stdout: 'FAILED test_id' (no '- reason') -> failures non-empty."""
        result = _run(monkeypatch, _PYTEST9_FAILED_STDOUT, returncode=1)

        assert len(result.failures) == 1, (
            "failures must be populated even when short summary has no '- reason'"
        )

    def test_short_reason_non_empty_without_reason_suffix(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """short_reason must be non-empty when extracted from traceback E-lines."""
        result = _run(monkeypatch, _PYTEST9_FAILED_STDOUT, returncode=1)

        assert len(result.failures) == 1
        assert result.failures[0].short_reason != "", (
            "short_reason must not be empty - must be extracted from traceback"
        )

    def test_short_reason_contains_assertion_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """short_reason must contain the assertion text from traceback E-lines."""
        result = _run(monkeypatch, _PYTEST9_FAILED_STDOUT, returncode=1)

        assert len(result.failures) == 1
        reason = result.failures[0].short_reason
        assert "AssertionError" in reason or "assert 1 == 2" in reason, (
            f"short_reason must contain assertion text, got: {reason!r}"
        )

    def test_xdist_failures_populated_without_reason_suffix(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """xdist + pytest 9 stdout (no '- reason') -> failures non-empty."""
        result = _run(monkeypatch, _PYTEST9_XDIST_FAILED_STDOUT, returncode=1)

        assert len(result.failures) == 1, "xdist failures must also be populated in pytest 9 format"

    def test_xdist_short_reason_non_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """xdist + pytest 9: short_reason extracted from traceback."""
        result = _run(monkeypatch, _PYTEST9_XDIST_FAILED_STDOUT, returncode=1)

        assert len(result.failures) == 1
        assert result.failures[0].short_reason != ""

    def test_test_id_correct_without_reason_suffix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """test_id must be correctly parsed without the '- reason' suffix."""
        result = _run(monkeypatch, _PYTEST9_FAILED_STDOUT, returncode=1)

        assert len(result.failures) == 1
        assert result.failures[0].test_id == "tests/test_foo.py::test_bad"


# ---------------------------------------------------------------------------
# C5 — _extract_short_reason collects all contiguous E-lines (issue #324)
# ---------------------------------------------------------------------------

_MULTILINE_E_BLOCK_STDOUT = """\
============================= test session starts ==============================
collected 1 item

tests/test_foo.py::test_dict_diff FAILED

================================= FAILURES =================================
________________________________ test_dict_diff ____________________________

    def test_dict_diff():
>       assert {"status": "ok"} == {"status": "error"}
E       AssertionError: assert {"status": "ok"} == {"status": "error"}
E         Differing items:
E         Left: {'status': 'ok'}
E         Right: {'status': 'error'}

tests/test_foo.py:5: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_foo.py::test_dict_diff
========================= 1 failed in 0.12s =========================
"""

_XDIST_MULTILINE_E_BLOCK_STDOUT = """\
============================= test session starts ==============================
collected 1 item

tests/test_foo.py::test_dict_diff FAILED

================================= FAILURES =================================
[gw0] _________________________ test_dict_diff __________________________

    def test_dict_diff():
>       assert {"status": "ok"} == {"status": "error"}
E       AssertionError: assert {"status": "ok"} == {"status": "error"}
E         Differing items:
E         Left: {'status': 'ok'}
E         Right: {'status': 'error'}

tests/test_foo.py:5: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_foo.py::test_dict_diff
========================= 1 failed in 0.12s =========================
"""

_LONG_E_BLOCK_STDOUT = """\
============================= test session starts ==============================
collected 1 item

tests/test_foo.py::test_long FAILED

================================= FAILURES =================================
________________________________ test_long _________________________________

    def test_long():
>       assert long_value == other
E       AssertionError: assert 'aaa' == 'bbb'
E         line2 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
E         line3 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
E         line4 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
E         line5 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
E         line6 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

tests/test_foo.py:5: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_foo.py::test_long
========================= 1 failed in 0.12s =========================
"""


class TestC5MultilineEBlock:
    """C5: _extract_short_reason collects all contiguous E-lines (issue #324)."""

    def test_c5_multiline_diff_lines_included_in_short_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Multi-line E-block: short_reason must contain diff lines, not just first E-line."""
        result = _run(monkeypatch, _MULTILINE_E_BLOCK_STDOUT, returncode=1)

        assert len(result.failures) == 1
        reason = result.failures[0].short_reason
        assert "Differing items" in reason or "Left" in reason or "Right" in reason, (
            f"short_reason must contain diff lines, got: {reason!r}"
        )

    def test_c5_short_reason_is_multiline_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Multi-line E-block: short_reason contains newlines between E-lines."""
        result = _run(monkeypatch, _MULTILINE_E_BLOCK_STDOUT, returncode=1)

        assert len(result.failures) == 1
        reason = result.failures[0].short_reason
        assert "\n" in reason, f"short_reason must be multi-line, got single-line: {reason!r}"

    def test_c5_xdist_multiline_diff_lines_included(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """xdist + multi-line E-block: diff lines must be present in short_reason."""
        result = _run(monkeypatch, _XDIST_MULTILINE_E_BLOCK_STDOUT, returncode=1)

        assert len(result.failures) == 1
        reason = result.failures[0].short_reason
        assert "Differing items" in reason or "Left" in reason or "Right" in reason, (
            f"xdist short_reason must contain diff lines, got: {reason!r}"
        )

    def test_c5_short_reason_capped_at_300_chars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Long E-block: short_reason must be capped at 300 characters."""
        result = _run(monkeypatch, _LONG_E_BLOCK_STDOUT, returncode=1)

        assert len(result.failures) == 1
        reason = result.failures[0].short_reason
        assert len(reason) <= 300, (
            f"short_reason must be capped at 300 chars, got {len(reason)}: {reason!r}"
        )

    def test_c5_single_e_line_still_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Regression guard: single E-line traceback still produces non-empty short_reason."""
        result = _run(monkeypatch, _FAILED_STDOUT, returncode=1)

        assert len(result.failures) == 1
        assert result.failures[0].short_reason != ""


_FIVE_FAILURES_STDOUT = """\\
============================= test session starts ==============================
collected 5 items

tests/test_foo.py::test_1 FAILED
tests/test_foo.py::test_2 FAILED
tests/test_foo.py::test_3 FAILED
tests/test_foo.py::test_4 FAILED
tests/test_foo.py::test_5 FAILED

================================= FAILURES =================================
________________________________ test_1 __________________________________
    def test_1():
>       assert 1 == 0
E       AssertionError: 1
________________________________ test_2 __________________________________
    def test_2():
>       assert 2 == 0
E       AssertionError: 2
________________________________ test_3 __________________________________
    def test_3():
>       assert 3 == 0
E       AssertionError: 3
________________________________ test_4 __________________________________
    def test_4():
>       assert 4 == 0
E       AssertionError: 4
________________________________ test_5 __________________________________
    def test_5():
>       assert 5 == 0
E       AssertionError: 5
=========================== short test summary info ===========================
FAILED tests/test_foo.py::test_1
FAILED tests/test_foo.py::test_2
FAILED tests/test_foo.py::test_3
FAILED tests/test_foo.py::test_4
FAILED tests/test_foo.py::test_5
========================= 5 failed in 0.23s =========================
"""


class TestC3VerboseTracebackAndCapping:
    """C3: tests for verbose traceback extraction and capping to MAX_FAILURES_DETAILED."""

    def test_verbose_false_tracebacks_are_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When verbose=False, all traceback strings must be empty."""
        result = _run(monkeypatch, _FAILED_STDOUT, returncode=1)
        assert len(result.failures) == 1
        assert result.failures[0].traceback == ""

    def test_verbose_true_tracebacks_are_extracted_and_capped(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When verbose=True, extract tracebacks but cap at MAX_FAILURES_DETAILED = 3."""
        completed = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=1,
            stdout=_FIVE_FAILURES_STDOUT,
            stderr="",
        )
        monkeypatch.setattr(
            pytest_runner_module.subprocess,
            "run",
            lambda *_args, **_kwargs: completed,
        )

        result = PytestRunner().run(["pytest"], cwd=".", timeout=30, verbose=True)

        assert len(result.failures) == 5
        assert "AssertionError: 1" in result.failures[0].traceback
        assert "AssertionError: 2" in result.failures[1].traceback
        assert "AssertionError: 3" in result.failures[2].traceback
        assert result.failures[3].traceback == ""
        assert result.failures[4].traceback == ""
