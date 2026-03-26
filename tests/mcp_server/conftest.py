"""
@module: tests.mcp_server.conftest
@layer: Test Infrastructure
@dependencies: pytest, mcp_server.config.*
@responsibilities:
  - Import shared fixtures for MCP server tests
  - Reset config singletons between tests to prevent cross-test contamination
"""

from collections.abc import Generator

import pytest

from mcp_server.tools.git_tools import CreateBranchInput
from mcp_server.tools.pr_tools import CreatePRInput

pytest_plugins = [
    "tests.mcp_server.fixtures.artifact_test_harness",
    "tests.mcp_server.fixtures.workflow_fixtures",
]


@pytest.fixture(autouse=True)
def reset_config_singletons() -> Generator[None, None, None]:
    """Reset all config singletons before/after each test."""

    def _reset_all() -> None:
        CreateBranchInput._git_config = None
        CreatePRInput._git_config = None

    _reset_all()
    yield
    _reset_all()
