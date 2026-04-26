"""Test execution tools."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, model_validator

from mcp_server.config.settings import Settings
from mcp_server.core.exceptions import ExecutionError
from mcp_server.core.interfaces import IPytestRunner
from mcp_server.core.operation_notes import InfoNote, NoteContext, RecoveryNote
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult

if TYPE_CHECKING:
    from mcp_server.managers.pytest_runner import PytestResult


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
