# c:\temp\pgmcp\mcp_server\core\interfaces\ipytest_runner.py
# template=interface version=3fb28c28 created=2026-06-20T18:30:14Z updated=
"""IPytestRunner module.

Run a pytest invocation and return a structured PytestResult.

@layer: Backend (Contracts)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from mcp_server.managers.pytest_runner import PytestResult


@runtime_checkable
class IPytestRunner(Protocol):
    """Run a pytest invocation and return a structured PytestResult."""

    def run(self, cmd: list[str], cwd: str, timeout: int, *, verbose: bool = False) -> PytestResult:
        raise NotImplementedError
