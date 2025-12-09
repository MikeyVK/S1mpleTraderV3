"""Test execution tools."""
import asyncio
import os
import subprocess
import sys
from typing import Any, Dict
from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.core.exceptions import ExecutionError
from mcp_server.config.settings import settings


def _run_pytest_sync(
    cmd: list[str],
    cwd: str,
    timeout: int
) -> tuple[str, str, int]:
    """Run pytest synchronously - to be called from thread pool."""
    # Build proper environment for venv
    env = os.environ.copy()
    venv_path = os.path.dirname(os.path.dirname(cmd[0]))  # Get venv from python path
    env["VIRTUAL_ENV"] = venv_path
    env["PATH"] = f"{os.path.dirname(cmd[0])};{env.get('PATH', '')}"
    env["PYTHONUNBUFFERED"] = "1"  # Disable output buffering

    # Use Popen for proper subprocess control
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,  # Prevents hanging on input
        text=True,
        cwd=cwd,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return stdout or "", stderr or "", proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise


class RunTestsTool(BaseTool):
    """Tool to run pytest."""

    name = "run_tests"
    description = "Run tests using pytest"

    # Default timeout in seconds (5 minutes for large test suites)
    DEFAULT_TIMEOUT = 300

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to test file or directory",
                    "default": "tests/"
                },
                "markers": {
                    "type": "string",
                    "description": "Pytest markers to filter by"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 300)",
                    "default": 300
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Verbose output (-v flag)",
                    "default": True
                }
            }
        }

    async def execute(
        self,
        path: str = "tests/",
        markers: str | None = None,
        timeout: int | None = None,
        verbose: bool = True,
        **kwargs: Any
    ) -> ToolResult:
        """Execute the tool."""
        cmd = [sys.executable, "-m", "pytest", path]

        if verbose:
            cmd.append("-v")

        cmd.append("--tb=short")  # Always use short traceback

        if markers:
            cmd.extend(["-m", markers])

        effective_timeout = timeout or self.DEFAULT_TIMEOUT

        try:
            # pylint: disable=no-member
            workspace_root = settings.server.workspace_root

            # Run subprocess in thread pool to avoid blocking event loop
            stdout, stderr, returncode = await asyncio.to_thread(
                _run_pytest_sync,
                cmd,
                workspace_root,
                effective_timeout
            )

            output = stdout or ""
            if stderr:
                output += "\nSTDERR:\n" + stderr

            # Add summary line
            if returncode == 0:
                output += "\n\n✅ Tests passed"
            else:
                output += f"\n\n❌ Tests failed (exit code: {returncode})"

            return ToolResult.text(output)

        except subprocess.TimeoutExpired:
            raise ExecutionError(
                f"Tests timed out after {effective_timeout}s. "
                "Consider running a smaller test subset or increasing timeout."
            ) from None
        except OSError as e:
            raise ExecutionError(f"Failed to run tests: {e}") from e
