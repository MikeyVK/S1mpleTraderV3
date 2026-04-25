"""Test execution tools."""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, model_validator

from mcp_server.config.settings import Settings
from mcp_server.core.exceptions import ExecutionError
from mcp_server.core.interfaces import IPytestRunner
from mcp_server.core.operation_notes import InfoNote, NoteContext, RecoveryNote
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult

if TYPE_CHECKING:
    from mcp_server.managers.pytest_runner import PytestResult


def _run_pytest_sync(cmd: list[str], cwd: str, timeout: int) -> tuple[str, str, int]:
    """Run pytest synchronously - to be called from thread pool."""
    env = os.environ.copy()
    venv_path = os.path.dirname(os.path.dirname(cmd[0]))
    env["VIRTUAL_ENV"] = venv_path
    env["PATH"] = f"{os.path.dirname(cmd[0])};{env.get('PATH', '')}"
    env["PYTHONUNBUFFERED"] = "1"

    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        cwd=cwd,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    ) as proc:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return stdout or "", stderr or "", proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise


def _parse_pytest_output(stdout: str) -> dict[str, Any]:
    """Parse pytest stdout into a structured dict.

    Returns a dict with:
    - summary: {"passed": int, "failed": int}
    - summary_line: human-readable one-liner (e.g. "2 passed in 0.45s")
    - failures: list of {"test_id", "location", "short_reason", "traceback"}
    """
    tb_by_test_id: dict[str, str] = {}
    in_failures = False
    current_id = ""
    current_tb: list[str] = []
    for line in stdout.splitlines():
        if re.match(r"^=+ FAILURES =+", line):
            in_failures = True
            continue
        if not in_failures:
            continue
        header = re.match(r"^_+\s+(.+?)\s+_+$", line)
        if header:
            if current_id and current_tb:
                tb_by_test_id[current_id] = "\n".join(current_tb).strip()
            current_id = header.group(1).strip()
            current_tb = []
        elif re.match(r"^=+", line):
            if current_id and current_tb:
                tb_by_test_id[current_id] = "\n".join(current_tb).strip()
            in_failures = False
        else:
            current_tb.append(line)

    failures: list[dict[str, str]] = []
    for line in stdout.splitlines():
        match = re.match(r"^FAILED (.+?) - (.+)$", line.strip())
        if match:
            location = match.group(1).strip()
            short_reason = match.group(2).strip()
            test_id = location.split("::")[-1] if "::" in location else location
            failures.append(
                {
                    "test_id": test_id,
                    "location": location,
                    "short_reason": short_reason,
                    "traceback": tb_by_test_id.get(test_id, ""),
                }
            )

    passed = 0
    failed = 0
    summary_line = ""
    for line in stdout.splitlines():
        match_fail = re.search(r"(\d+) failed", line)
        if match_fail:
            failed = int(match_fail.group(1))
        match_pass = re.search(r"(\d+) passed", line)
        if match_pass:
            passed = int(match_pass.group(1))
        if re.search(r"\d+ (passed|failed)", line):
            cleaned = re.sub(r"^=+\s*", "", line.strip())
            cleaned = re.sub(r"\s*=+$", "", cleaned).strip()
            if cleaned:
                summary_line = cleaned

    result: dict[str, Any] = {
        "summary": {"passed": passed, "failed": failed},
        "summary_line": summary_line,
    }
    if failures:
        result["failures"] = failures
    return result


class RunTestsInput(BaseModel):
    """Input for RunTestsTool."""

    path: str | None = Field(
        default=None,
        description=(
            "Path to test file or directory. "
            "Multiple paths can be space-separated, e.g. 'tests/unit tests/integration'."
        ),
    )
    scope: Literal["full"] | None = Field(
        default=None,
        description="Set to 'full' to run the entire test suite. Mutually exclusive with path.",
    )
    markers: str | None = Field(default=None, description="Pytest markers to filter by")
    timeout: int = Field(default=300, description="Timeout in seconds (default: 300)")
    last_failed_only: bool = Field(
        default=False,
        description="Re-run only previously failed tests (pytest --lf)",
    )
    coverage: bool = Field(
        default=False,
        description="Enable branch coverage and enforce the 90% threshold.",
    )

    @model_validator(mode="after")
    def validate_path_or_scope(self) -> RunTestsInput:
        """Ensure exactly one of path or scope is provided."""
        if self.path is None and self.scope is None:
            raise ValueError("Either 'path' or 'scope' must be provided")
        if self.path is not None and self.scope is not None:
            raise ValueError("'path' and 'scope' are mutually exclusive — provide one, not both")
        return self


def _emit_lf_cache_note(result: PytestResult, params: RunTestsInput, context: NoteContext) -> None:
    """Emit the LF-empty informational note only when the user requested --lf."""
    if params.last_failed_only and result.lf_cache_was_empty:
        context.produce(InfoNote("Last-failed cache was empty; ran full selection instead."))


def _find_timeout_expired(exc: BaseException) -> subprocess.TimeoutExpired | None:
    """Unwrap direct or grouped timeout exceptions from thread execution."""
    if isinstance(exc, subprocess.TimeoutExpired):
        return exc

    nested = getattr(exc, "exceptions", None)
    if nested is None:
        return None

    for child in nested:
        timeout_exc = _find_timeout_expired(child)
        if timeout_exc is not None:
            return timeout_exc
    return None


def _to_tool_result(result: PytestResult) -> ToolResult:
    """Convert the typed runner result into the MCP ToolResult payload."""
    payload = {
        "exit_code": result.exit_code,
        "summary": {
            "passed": result.passed,
            "failed": result.failed,
            "skipped": result.skipped,
            "errors": result.errors,
        },
        "summary_line": result.summary_line,
        "failures": [asdict(failure) for failure in result.failures],
        "coverage_pct": result.coverage_pct,
        "lf_cache_was_empty": result.lf_cache_was_empty,
    }
    return ToolResult(
        content=[
            {"type": "text", "text": result.summary_line},
            {"type": "json", "json": payload},
        ]
    )


class RunTestsTool(BaseTool):
    """Thin MCP adapter for pytest execution via an injected runner."""

    name = "run_tests"
    description = "Run tests using pytest"
    args_model = RunTestsInput

    DEFAULT_TIMEOUT = 300

    def __init__(
        self,
        runner: IPytestRunner,
        workspace_root: str | os.PathLike[str] | None = None,
        settings: Settings | None = None,
    ) -> None:
        super().__init__()
        self._runner = runner
        base_workspace = workspace_root or (
            settings.server.workspace_root if settings else Path.cwd()
        )
        self._workspace_root = str(base_workspace)

    def _build_cmd(self, params: RunTestsInput) -> list[str]:
        """Build the pytest command from input parameters."""
        cmd = [sys.executable, "-m", "pytest", "--tb=short"]
        if params.path is not None:
            cmd.extend(params.path.split())
        if params.last_failed_only:
            cmd.append("--lf")
        if params.markers:
            cmd.extend(["-m", params.markers])
        if params.coverage:
            cmd.extend(
                [
                    "--cov=backend",
                    "--cov=mcp_server",
                    "--cov-branch",
                    "--cov-fail-under=90",
                ]
            )
        return cmd

    async def execute(self, params: RunTestsInput, context: NoteContext) -> ToolResult:
        """Execute the tool."""
        cmd = self._build_cmd(params)
        effective_timeout = params.timeout or self.DEFAULT_TIMEOUT

        try:
            result = await asyncio.to_thread(
                self._runner.run,
                cmd,
                self._workspace_root,
                effective_timeout,
            )
        except Exception as exc:
            if _find_timeout_expired(exc) is not None:
                context.produce(
                    RecoveryNote(
                        f"Tests timed out after {effective_timeout}s. "
                        "Run a smaller subset or raise the timeout."
                    )
                )
                raise ExecutionError(f"Tests timed out after {effective_timeout}s") from None
            if isinstance(exc, OSError):
                context.produce(
                    RecoveryNote("Verify the Python interpreter and venv are reachable.")
                )
                raise ExecutionError(f"Failed to run tests: {exc}") from exc
            raise

        if result.note is not None:
            context.produce(result.note)
        _emit_lf_cache_note(result, params, context)

        if result.should_raise:
            raise ExecutionError(f"pytest exited with returncode {result.exit_code}")

        return _to_tool_result(result)
