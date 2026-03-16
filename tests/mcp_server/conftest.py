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
from mcp_server.tools.issue_tools import CreateIssueInput
from mcp_server.tools.pr_tools import CreatePRInput

pytest_plugins = [
    "tests.mcp_server.fixtures.artifact_test_harness",
    "tests.mcp_server.fixtures.workflow_fixtures",
]


@pytest.fixture(autouse=True)
def reset_config_singletons() -> Generator[None, None, None]:
    """Reset all config singletons before/after each test.

    Prevents cross-test contamination when config tests load custom YAML paths
    and set the module-level singleton, which would otherwise be reused by
    subsequent tests that call ``from_file()`` without arguments.

    Covers both the *singleton_instance* pattern (IssueConfig, ScopeConfig,
    WorkflowConfig, MilestoneConfig, ContributorConfig) and the *_instance*
    pattern used by LabelConfig.
    """

    def _reset_all() -> None:
        CreateIssueInput._issue_config = None
        CreateIssueInput._git_config = None
        CreateIssueInput._label_config = None
        CreateIssueInput._scope_config = None
        CreateIssueInput._milestone_config = None
        CreateIssueInput._contributor_config = None
        CreateBranchInput._git_config = None
        CreatePRInput._git_config = None

    _reset_all()
    yield
    _reset_all()
