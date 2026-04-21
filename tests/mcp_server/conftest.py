"""
@module: tests.mcp_server.conftest
@layer: Test Infrastructure
@dependencies: pytest, mcp_server.config.*
@responsibilities:
  - Reset config singletons between tests to prevent cross-test contamination
"""

from collections.abc import Generator

import pytest

from mcp_server.tools.git_tools import CreateBranchInput


@pytest.fixture(autouse=True)
def reset_config_singletons() -> Generator[None, None, None]:
    """Reset all config singletons before/after each test."""

    def _reset_all() -> None:
        CreateBranchInput._git_config = None

    _reset_all()
    yield
    _reset_all()
