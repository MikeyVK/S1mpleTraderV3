"""Reusable FakePytestRunner fixture for thin-adapter unit tests.

@layer: Tests (Fixtures)
@dependencies: [mcp_server.managers.pytest_runner]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server.managers.pytest_runner import PytestResult


@dataclass
class FakePytestRunner:
    """Synchronous test double for IPytestRunner."""

    result: PytestResult
    captured_cmd: list[str] | None = None

    def run(self, cmd: list[str], cwd: str, timeout: int) -> PytestResult:
        """Capture the built pytest command and return the pre-baked result."""
        del cwd, timeout
        self.captured_cmd = cmd
        return self.result
