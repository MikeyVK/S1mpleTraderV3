"""PytestRunner manager — command execution, output parsing, exit-code classification."""

from __future__ import annotations

import re
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

    exit_code: int  # raw int — may be unknown (not in PytestExitCode)
    summary_line: str  # ALWAYS non-empty — canonical display string
    passed: int
    failed: int
    skipped: int
    errors: int
    failures: tuple[FailureDetail, ...]  # tuple for hashability + immutability
    coverage_pct: float | None  # None when coverage flag was not requested
    lf_cache_was_empty: bool  # True iff pytest --lf fell back to full run
    should_raise: bool  # True for exit codes 2, 3, 4, unknown — stamped by runner policy
    note: "NoteEntry | None"  # RecoveryNote/SuggestionNote from policy; None for codes 0, 1


@dataclass(frozen=True)
class ExitCodePolicy:
    """Dispatch policy for a single pytest exit code."""

    outcome: Literal["return", "raise"]
    note_factory: Callable[[int], "NoteEntry"] | None  # None for codes that produce no note
    summary_line_when_no_parse: str  # used when parser found no summary


_EXIT_CODE_POLICY: dict[int, ExitCodePolicy] = {
    PytestExitCode.ALL_PASSED: ExitCodePolicy("return", None, ""),
    PytestExitCode.TESTS_FAILED: ExitCodePolicy("return", None, ""),
    PytestExitCode.INTERRUPTED: ExitCodePolicy(
        "raise",
        lambda c: RecoveryNote("Pytest was interrupted; check for hung tests or external SIGINT."),
        "pytest interrupted (exit 2)",
    ),
    PytestExitCode.INTERNAL_ERROR: ExitCodePolicy(
        "raise",
        lambda c: RecoveryNote(
            "Pytest reported an internal error; inspect stderr and pytest plugins."
        ),
        "pytest internal error (exit 3)",
    ),
    PytestExitCode.USAGE_ERROR: ExitCodePolicy(
        "raise",
        lambda c: RecoveryNote(
            "Pytest could not start. Verify the path exists and the CLI options are valid."
        ),
        "pytest usage error (exit 4)",
    ),
    PytestExitCode.NO_TESTS_COLLECTED: ExitCodePolicy(
        "return",
        lambda c: SuggestionNote("No tests matched the filter. Check markers and path."),
        "no tests collected",
    ),
}

_UNKNOWN_CODE_POLICY = ExitCodePolicy(
    "raise",
    lambda c: RecoveryNote(f"Pytest exited with unexpected code {c}; inspect stderr."),
    "pytest exited with unexpected code",
)
