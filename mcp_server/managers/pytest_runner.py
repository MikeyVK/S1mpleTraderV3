"""PytestRunner manager — command execution, output parsing, exit-code classification."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Literal

from mcp_server.core.operation_notes import Note

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
    is_collection_error: bool = False


@dataclass(frozen=True)
class PytestResult:
    """Single source of truth for a completed pytest invocation."""

    exit_code: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration_seconds: float | None
    failures: tuple[FailureDetail, ...]
    coverage_pct: float | None
    lf_cache_was_empty: bool
    should_raise: bool
    note: NoteEntry | None
    is_error: bool
    stderr: str = ""


@dataclass(frozen=True)
class ExitCodePolicy:
    """Dispatch policy for a single pytest exit code."""

    outcome: Literal["ok", "error", "raise"]
    note_factory: Callable[[int], NoteEntry] | None


@dataclass(frozen=True)
class _PytestExecution:
    """Private normalized subprocess result used inside PytestRunner only."""

    stdout: str
    stderr: str
    returncode: int


_EXIT_CODE_POLICY: dict[int, ExitCodePolicy] = {
    PytestExitCode.ALL_PASSED: ExitCodePolicy("ok", None),
    PytestExitCode.TESTS_FAILED: ExitCodePolicy("ok", None),
    PytestExitCode.INTERRUPTED: ExitCodePolicy(
        "error",
        lambda _: Note(key="pytest_interrupted_recovery", params={}),
    ),
    PytestExitCode.INTERNAL_ERROR: ExitCodePolicy(
        "error",
        lambda _: Note(key="pytest_internal_error_recovery", params={}),
    ),
    PytestExitCode.USAGE_ERROR: ExitCodePolicy(
        "error",
        lambda _: Note(key="pytest_usage_error_recovery", params={}),
    ),
    PytestExitCode.NO_TESTS_COLLECTED: ExitCodePolicy(
        "ok",
        lambda _: Note(key="pytest_no_tests_collected_suggestion", params={}),
    ),
}

_UNKNOWN_CODE_POLICY = ExitCodePolicy(
    "raise",
    lambda c: Note(key="pytest_unexpected_code_recovery", params={"exit_code": c}),
)

_FAILED_LINE_RE = re.compile(r"^FAILED (.+?)(?:\s+-\s+(.+))?$", re.MULTILINE)
_TRACEBACK_ERROR_RE = re.compile(r"^E\s+(.+)$", re.MULTILINE)
_COVERAGE_RE = re.compile(r"^TOTAL\b(?:\s+\d+)+\s+(\d+(?:\.\d+)?)%$", re.MULTILINE)
_DURATION_RE = re.compile(r"\bin\s+(\d+(?:\.\d+)?)s(?:\s|=|$)")
_LF_EMPTY_RE = re.compile(r"no previously failed tests,\s*not deselecting", re.IGNORECASE)


MAX_FAILURES_DETAILED: int = 3


class PytestRunner:
    """Domain manager: command execution, output parsing, exit-code classification."""

    def run(self, cmd: list[str], cwd: str, timeout: int, *, verbose: bool = False) -> PytestResult:
        """Execute pytest, parse output, classify exit code, return typed result."""
        execution = self._execute(cmd, cwd, timeout)
        return self._parse_output(
            execution.stdout,
            execution.stderr,
            execution.returncode,
            verbose=verbose,
        )

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

    def _parse_output(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
        *,
        verbose: bool = False,
    ) -> PytestResult:
        """Parse raw pytest stdout and return a fully typed PytestResult."""
        policy = _EXIT_CODE_POLICY.get(returncode, _UNKNOWN_CODE_POLICY)

        passed, failed, skipped, errors = self._parse_counts(stdout)
        failures = self._parse_failures(stdout, verbose=verbose)
        coverage_pct = self._parse_coverage(stdout)
        duration_seconds = self._parse_duration_seconds(stdout)
        lf_cache_was_empty = bool(_LF_EMPTY_RE.search(stdout))

        return PytestResult(
            exit_code=returncode,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration_seconds=duration_seconds,
            failures=failures,
            coverage_pct=coverage_pct,
            lf_cache_was_empty=lf_cache_was_empty,
            should_raise=policy.outcome == "raise",
            note=policy.note_factory(returncode) if policy.note_factory else None,
            is_error=policy.outcome == "error",
            stderr=stderr,
        )

    def _parse_counts(self, stdout: str) -> tuple[int, int, int, int]:
        """Extract (passed, failed, skipped, errors) counts — order-independent."""

        def _count(keyword: str) -> int:
            match = re.search(rf"(\d+) {keyword}", stdout)
            return int(match.group(1)) if match else 0

        return _count("passed"), _count("failed"), _count("skipped"), _count("error")

    def _parse_failures(self, stdout: str, *, verbose: bool = False) -> tuple[FailureDetail, ...]:
        """Extract FailureDetail entries from FAILED lines and ERROR collecting lines."""
        details: list[FailureDetail] = []
        for i, match in enumerate(_FAILED_LINE_RE.finditer(stdout)):
            test_id = match.group(1).strip()
            raw_traceback = self._extract_traceback(stdout, test_id)
            inline_reason = match.group(2)
            if inline_reason:
                short_reason = inline_reason.strip()
            else:
                short_reason = self._extract_short_reason(raw_traceback)
            location, _, _ = test_id.partition("::")

            traceback = ""
            if verbose and i < MAX_FAILURES_DETAILED:
                traceback = raw_traceback

            details.append(
                FailureDetail(
                    test_id=test_id,
                    location=location,
                    short_reason=short_reason,
                    traceback=traceback,
                    is_collection_error=False,
                )
            )

        collect_matches = list(
            re.finditer(
                r"_+\s*ERROR collecting\s+(.+?)(?:\s+_+)?$",
                stdout,
                re.MULTILINE,
            )
        )
        for j, match in enumerate(collect_matches):
            target_name = match.group(1).strip()
            raw_traceback = self._extract_traceback(stdout, target_name)
            short_reason = self._extract_short_reason(raw_traceback)

            traceback = ""
            if verbose and (len(details) + j) < MAX_FAILURES_DETAILED:
                traceback = raw_traceback

            details.append(
                FailureDetail(
                    test_id=target_name,
                    location=target_name,
                    short_reason=short_reason,
                    traceback=traceback,
                    is_collection_error=True,
                )
            )

        return tuple(details)

    def _extract_short_reason(self, traceback: str) -> str:
        """Extract all contiguous 'E  ...' assertion lines from a traceback block.

        Collects every E-line, joins them with newlines, and caps the result at
        300 characters so the response stays compact while preserving diff context.
        """
        lines = _TRACEBACK_ERROR_RE.findall(traceback)
        if not lines:
            tb_lines = [ln.strip() for ln in traceback.splitlines() if ln.strip()]
            if tb_lines:
                return tb_lines[-1][:300]
            return "Collection Error"
        reason = "\n".join(line.strip() for line in lines)
        return reason[:300]

    def _extract_traceback(self, stdout: str, test_id: str) -> str:
        """Extract the traceback block for a given test_id from the FAILURES or ERRORS section."""
        parts = test_id.split("::")
        target_name = ".".join(parts[1:]) if len(parts) > 1 else parts[0]
        pattern = re.compile(
            r"(?:\[gw\d+\]\s+)?_*\s*"
            + re.escape(target_name)
            + r"\s*_*\r?\n(.*?)(?=\r?\n(?:\[gw\d+\]\s+)?_+|\r?\n=+|\Z)",
            re.DOTALL,
        )
        match = pattern.search(stdout)
        if match:
            return match.group(1).strip()

        collect_pattern = re.compile(
            r"_*\s*ERROR collecting\s+"
            + re.escape(target_name)
            + r"(?:\s+_*)?\r?\n(.*?)(?=\r?\n(?:\[gw\d+\]\s+)?_+|\r?\n=+|\Z)",
            re.DOTALL,
        )
        match = collect_pattern.search(stdout)
        return match.group(1).strip() if match else ""

    def _parse_coverage(self, stdout: str) -> float | None:
        """Extract total coverage percentage from coverage report line."""
        match = _COVERAGE_RE.search(stdout)
        return float(match.group(1)) if match else None

    def _parse_duration_seconds(self, stdout: str) -> float | None:
        """Extract the numeric duration from the final pytest summary, when present."""
        matches = _DURATION_RE.findall(stdout)
        return float(matches[-1]) if matches else None
