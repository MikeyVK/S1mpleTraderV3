"""Test execution tools."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mcp_server.config.settings import Settings
from mcp_server.core.exceptions import ExecutionError
from mcp_server.core.interfaces import IPytestRunner
from mcp_server.core.interfaces.icore_tool import ICoreTool
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.schemas.tool_outputs import RunTestsOutput, TestFailureDTO
from mcp_server.utils.schema_utils import resolve_schema_refs

if TYPE_CHECKING:
    from mcp_server.managers.pytest_runner import PytestResult


class RunTestsInput(BaseModel):
    """Input for RunTestsTool."""

    model_config = ConfigDict(extra="forbid")

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
    collect_only: bool = Field(
        default=False,
        description="Only collect tests, do not run them (pytest --collect-only).",
    )
    verbose: bool = Field(
        default=False,
        description=(
            "Enable verbose mode to capture complete tracebacks and stdout/stderr output "
            "from failed tests. Only permitted in path-based execution mode targeting "
            "specific test files (directories or the full suite run are not supported)."
        ),
    )

    @model_validator(mode="after")
    def validate_path_or_scope(self) -> RunTestsInput:
        """Ensure exactly one of path or scope is provided and validate verbose constraints."""
        if self.path is None and self.scope is None:
            raise ValueError("Either 'path' or 'scope' must be provided")
        if self.path is not None and self.scope is not None:
            raise ValueError("'path' and 'scope' are mutually exclusive — provide one, not both")

        if self.verbose:
            if self.path is None:
                msg = (
                    "verbose mode requires a path-based execution mode "
                    "(directories or the full suite are not supported)"
                )
                raise ValueError(msg)
            for p in self.path.split():
                if os.path.isdir(p):
                    msg = (
                        "verbose mode is only permitted on specific files, "
                        f"but '{p}' is a directory"
                    )
                    raise ValueError(msg)
                # String check fallback for mock/non-existent paths in unit tests
                if not (p.endswith(".py") or ".py::" in p or "::" in p):
                    msg = (
                        "verbose mode is only permitted on specific test files, "
                        f"but '{p}' is not a valid python file path"
                    )
                    raise ValueError(msg)
        return self


def _emit_lf_cache_note(result: PytestResult, params: RunTestsInput, context: NoteContext) -> None:
    """Emit the LF-empty informational note only when the user requested --lf."""
    if params.last_failed_only and result.lf_cache_was_empty:
        context.produce(
            Note(
                key="pytest_lf_cache_empty_info",
                params={},
            )
        )


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


class RunTestsTool(ICoreTool[RunTestsInput, RunTestsOutput]):
    """Thin MCP adapter for pytest execution via an injected runner."""

    @property
    def name(self) -> str:
        return "run_tests"

    @property
    def description(self) -> str:
        return "Run tests using pytest"

    @property
    def args_model(self) -> type[RunTestsInput] | None:
        return RunTestsInput

    DEFAULT_TIMEOUT = 300

    def __init__(
        self,
        runner: IPytestRunner,
        workspace_root: str | os.PathLike[str] | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._runner = runner
        base_workspace = workspace_root or (
            settings.server.workspace_root if settings else Path.cwd()
        )
        self._workspace_root = str(base_workspace)

    @property
    def input_schema(self) -> dict[str, Any]:
        """Get the input schema for the tool."""
        if self.args_model:
            return resolve_schema_refs(self.args_model.model_json_schema())
        return {
            "type": "object",
            "properties": {},
        }

    def _build_cmd(self, params: RunTestsInput) -> list[str]:
        """Build the pytest command from input parameters."""
        tb_style = "--tb=long" if params.verbose else "--tb=short"
        cmd = [sys.executable, "-m", "pytest", tb_style]
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
        if params.collect_only:
            cmd.append("--collect-only")
        return cmd

    async def execute(self, params: RunTestsInput, context: NoteContext) -> RunTestsOutput:
        """Execute the tool."""
        cmd = self._build_cmd(params)
        effective_timeout = params.timeout or self.DEFAULT_TIMEOUT

        try:
            result = await asyncio.to_thread(
                self._runner.run,
                cmd,
                self._workspace_root,
                effective_timeout,
                verbose=params.verbose,
            )
        except Exception as exc:
            if _find_timeout_expired(exc) is not None:
                context.produce(
                    Note(
                        key="pytest_timeout_recovery",
                        params={"timeout": effective_timeout},
                    )
                )
                raise ExecutionError(f"Tests timed out after {effective_timeout}s") from None
            if isinstance(exc, OSError):
                context.produce(
                    Note(
                        key="pytest_interpreter_recovery",
                        params={},
                    )
                )
                raise ExecutionError(f"Failed to run tests: {exc}") from exc
            raise

        if result.note is not None:
            context.produce(result.note)
        _emit_lf_cache_note(result, params, context)

        if not params.verbose and result.failures:
            failing_files = sorted({f.location for f in result.failures if f.location})
            if failing_files:
                failing_files_str = " ".join(failing_files)
                context.produce(
                    Note(
                        key="pytest_failed_verbose_suggestion",
                        params={"failing_files": failing_files_str},
                    )
                )

        if result.should_raise:
            raise ExecutionError(f"pytest exited with returncode {result.exit_code}")

        failures_list = []
        for f in result.failures:
            failures_list.append(
                TestFailureDTO(
                    test_id=f.test_id,
                    location=f.location,
                    short_reason=f.short_reason,
                    traceback=f.traceback,
                    is_collection_error=f.is_collection_error,
                )
            )

        stderr_tail = "\n".join(result.stderr.splitlines()[-50:]) if result.stderr else ""

        return RunTestsOutput(
            success=not result.is_error,
            exit_code=result.exit_code,
            passed_count=result.passed,
            failed_count=result.failed,
            skipped_count=result.skipped,
            errors_count=result.errors,
            duration_seconds=result.duration_seconds,
            failures=failures_list,
            coverage_pct=result.coverage_pct,
            lf_cache_was_empty=result.lf_cache_was_empty,
            stderr=stderr_tail,
        )
