"""Test execution tools."""

import asyncio
import os
import re
import subprocess
import sys
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.config.settings import settings
from mcp_server.core.exceptions import ExecutionError
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


def _run_pytest_sync(cmd: list[str], cwd: str, timeout: int) -> tuple[str, str, int]:
    """Run pytest synchronously - to be called from thread pool."""
    # Build proper environment for venv
    env = os.environ.copy()
    venv_path = os.path.dirname(os.path.dirname(cmd[0]))  # Get venv from python path
    env["VIRTUAL_ENV"] = venv_path
    env["PATH"] = f"{os.path.dirname(cmd[0])};{env.get('PATH', '')}"
    env["PYTHONUNBUFFERED"] = "1"  # Disable output buffering

    # Use Popen for proper subprocess control
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,  # Prevents hanging on input
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
    - failures: list of {"test_id", "location", "short_reason"}  — only present when failed > 0
    """
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
                }
            )

    passed = 0
    failed = 0
    for line in stdout.splitlines():
        m_fail = re.search(r"(\d+) failed", line)
        if m_fail:
            failed = int(m_fail.group(1))
        m_pass = re.search(r"(\d+) passed", line)
        if m_pass:
            passed = int(m_pass.group(1))

    result: dict[str, Any] = {"summary": {"passed": passed, "failed": failed}}
    if failures:
        result["failures"] = failures
    return result


class RunTestsInput(BaseModel):
    """Input for RunTestsTool."""

    path: str = Field(default="tests/", description="Path to test file or directory")
    markers: str | None = Field(default=None, description="Pytest markers to filter by")
    timeout: int = Field(default=300, description="Timeout in seconds (default: 300)")


class RunTestsTool(BaseTool):
    """Tool to run pytest."""

    name = "run_tests"
    description = "Run tests using pytest"
    args_model = RunTestsInput

    # Default timeout in seconds (5 minutes for large test suites)
    DEFAULT_TIMEOUT = 300

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()  # type: ignore[union-attr]

    async def execute(self, params: RunTestsInput) -> ToolResult:
        """Execute the tool."""
        cmd = [sys.executable, "-m", "pytest", params.path]

        cmd.append("--tb=short")  # Always use short traceback

        if params.markers:
            cmd.extend(["-m", params.markers])

        effective_timeout = params.timeout or self.DEFAULT_TIMEOUT

        try:
            # pylint: disable=no-member
            workspace_root = settings.server.workspace_root

            # Run subprocess in thread pool to avoid blocking event loop
            stdout, stderr, _ = await asyncio.to_thread(
                _run_pytest_sync,
                cmd,
                workspace_root,
                effective_timeout,
            )

            output = stdout or ""
            if stderr:
                output += "\nSTDERR:\n" + stderr

            parsed = _parse_pytest_output(output)
            return ToolResult.json_data(parsed)

        except subprocess.TimeoutExpired:
            raise ExecutionError(
                f"Tests timed out after {effective_timeout}s. "
                "Consider running a smaller test subset or increasing timeout."
            ) from None
        except OSError as e:
            raise ExecutionError(f"Failed to run tests: {e}") from e
