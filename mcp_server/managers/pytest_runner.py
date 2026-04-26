"""PytestRunner manager — command execution, output parsing, exit-code classification."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Literal

from mcp_server.core.operation_notes import RecoveryNote, SuggestionNote

if TYPE_CHECKING:
    from mcp_server.core.operation_notes import NoteEntry


class PytestExitCode(IntEnum):
    """Pytest exit codes per pytest CLI specification."""

    ALL_PASSED = 0
    TESTS_FAILED = 1
    INTERRUPTED = 2
    INTERNAL_ERROR = 3
    USAGE_ERROR = 4
    NO_TESTS_COLLECTED = 5


@dataclass(frozen=True)
class FailureDetail:
    """Detail record for a single failing test."""

    test_id: str
    location: str
    short_reason: str
    traceback: str


@dataclass(frozen=True)
class PytestResult:
    """Single source of truth for a completed pytest invocation."""

    exit_code: int
    summary_line: str
    passed: int
    failed: int
    skipped: int
    errors: int
    failures: tuple[FailureDetail, ...]
    coverage_pct: float | None
    lf_cache_was_empty: bool
    should_raise: bool
    note: NoteEntry | None


@dataclass(frozen=True)
class ExitCodePolicy:
    """Dispatch policy for a single pytest exit code."""

    outcome: Literal["return", "raise"]
    note_factory: Callable[[int], NoteEntry] | None
    summary_line_when_no_parse: str


@dataclass(frozen=True)
class _PytestExecution:
    """Private normalized subprocess result used inside PytestRunner only."""

    stdout: str
    stderr: str
    returncode: int


_EXIT_CODE_POLICY: dict[int, ExitCodePolicy] = {
    PytestExitCode.ALL_PASSED: ExitCodePolicy("return", None, ""),
    PytestExitCode.TESTS_FAILED: ExitCodePolicy("return", None, ""),
    PytestExitCode.INTERRUPTED: ExitCodePolicy(
        "raise",
        lambda _: RecoveryNote("Pytest was interrupted; check for hung tests or external SIGINT."),
        "pytest interrupted (exit 2)",
    ),
    PytestExitCode.INTERNAL_ERROR: ExitCodePolicy(
        "raise",
        lambda _: RecoveryNote(
            "Pytest reported an internal error; inspect stderr and pytest plugins."
        ),
        "pytest internal error (exit 3)",
    ),
    PytestExitCode.USAGE_ERROR: ExitCodePolicy(
        "raise",
        lambda _: RecoveryNote(
            "Pytest could not start. Verify the path exists and the CLI options are valid."
        ),
        "pytest usage error (exit 4)",
    ),
    PytestExitCode.NO_TESTS_COLLECTED: ExitCodePolicy(
        "return",
        lambda _: SuggestionNote("No tests matched the filter. Check markers and path."),
        "no tests collected",
    ),
}

_UNKNOWN_CODE_POLICY = ExitCodePolicy(
    "raise",
    lambda c: RecoveryNote(f"Pytest exited with unexpected code {c}; inspect stderr."),
    "pytest exited with unexpected code",
)

_FAILED_LINE_RE = re.compile(r"^FAILED (.+?) - (.+)$", re.MULTILINE)
_COVERAGE_RE = re.compile(r"^TOTAL\b(?:\s+\d+)+\s+(\d+(?:\.\d+)?)%$", re.MULTILINE)
_LF_EMPTY_RE = re.compile(r"no previously failed tests,\s*not deselecting", re.IGNORECASE)


class PytestRunner:
    """Domain manager: command execution, output parsing, exit-code classification."""

    def run(self, cmd: list[str], cwd: str, timeout: int) -> PytestResult:
        """Execute pytest, parse output, classify exit code, return typed result."""
        execution = self._execute(cmd, cwd, timeout)
        return self._parse_output(execution.stdout, execution.returncode)

    def _execute(self, cmd: list[str], cwd: str, timeout: int) -> _PytestExecution:
        """Run pytest with safe subprocess defaults for the MCP server environment."""
        env = os.environ.copy()
        python_dir = os.path.dirname(cmd[0])
        venv_path = os.path.dirname(python_dir)
        env["VIRTUAL_ENV"] = venv_path
        env["PATH"] = f"{python_dir};{env.get('PATH', '')}"
        env["PYTHONUNBUFFERED"] = "1"

        proc = subprocess.run(
            cmd,
            capture_output=True,
            check=False,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            ),
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        )
        return _PytestExecution(
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            returncode=proc.returncode,
        )

    def _parse_output(self, stdout: str, returncode: int) -> PytestResult:
        """Parse raw pytest stdout and return a fully typed PytestResult."""
        policy = _EXIT_CODE_POLICY.get(returncode, _UNKNOWN_CODE_POLICY)

        passed, failed, skipped, errors = self._parse_counts(stdout)
        failures = self._parse_failures(stdout)
        coverage_pct = self._parse_coverage(stdout)
        lf_cache_was_empty = bool(_LF_EMPTY_RE.search(stdout))
        summary_line = self._parse_summary_line(stdout, returncode, policy)

        return PytestResult(
            exit_code=returncode,
            summary_line=summary_line,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            failures=failures,
            coverage_pct=coverage_pct,
            lf_cache_was_empty=lf_cache_was_empty,
            should_raise=policy.outcome == "raise",
            note=policy.note_factory(returncode) if policy.note_factory else None,
        )

    def _parse_counts(self, stdout: str) -> tuple[int, int, int, int]:
        """Extract (passed, failed, skipped, errors) counts — order-independent."""

        def _count(keyword: str) -> int:
            match = re.search(rf"(\d+) {keyword}", stdout)
            return int(match.group(1)) if match else 0

        return _count("passed"), _count("failed"), _count("skipped"), _count("error")

    def _parse_failures(self, stdout: str) -> tuple[FailureDetail, ...]:
        """Extract FailureDetail entries from FAILED lines in short summary."""
        details: list[FailureDetail] = []
        for match in _FAILED_LINE_RE.finditer(stdout):
            test_id = match.group(1).strip()
            short_reason = match.group(2).strip()
            traceback = self._extract_traceback(stdout, test_id)
            location, _, _ = test_id.partition("::")
            details.append(
                FailureDetail(
                    test_id=test_id,
                    location=location,
                    short_reason=short_reason,
                    traceback=traceback,
                )
            )
        return tuple(details)

    def _extract_traceback(self, stdout: str, test_id: str) -> str:
        """Extract the traceback block for a given test_id from the FAILURES section."""
        _, _, test_name = test_id.rpartition("::")
        pattern = re.compile(
            r"_{3,}\s+" + re.escape(test_name) + r"\s+_{3,}\n(.*?)(?=\n_{3,}|\n={3,}|\Z)",
            re.DOTALL,
        )
        match = pattern.search(stdout)
        return match.group(1).strip() if match else ""

    def _parse_coverage(self, stdout: str) -> float | None:
        """Extract total coverage percentage from coverage report line."""
        match = _COVERAGE_RE.search(stdout)
        return float(match.group(1)) if match else None

    def _parse_summary_line(self, stdout: str, returncode: int, policy: ExitCodePolicy) -> str:
        """Return the human-readable summary line — never empty."""
        if policy.summary_line_when_no_parse:
            return policy.summary_line_when_no_parse

        candidates: list[str] = re.findall(r"={3,}\s+(.+?)\s+={3,}", stdout)
        for candidate in reversed(candidates):
            if "in " in candidate or "passed" in candidate or "failed" in candidate:
                return candidate
        return f"pytest exited with code {returncode}"
