"""
@module: tests.conftest
@layer: Test Infrastructure
@dependencies: pytest
@responsibilities:
  - Import shared fixtures for pytest discovery
  - Reset config singletons between tests to prevent cross-test contamination
"""

import pytest

# Import fixtures from fixture modules
pytest_plugins = [
    "tests.fixtures.artifact_test_harness",
    "tests.fixtures.workflow_fixtures",
]


@pytest.fixture(autouse=True)
def reset_config_singletons() -> object:
    """Reset all config singletons before/after each test.

    Prevents cross-test contamination when config tests load custom YAML paths
    and set the module-level singleton, which would otherwise be reused by
    subsequent tests that call ``from_file()`` without arguments.

    Covers both the *singleton_instance* pattern (IssueConfig, ScopeConfig,
    WorkflowConfig, MilestoneConfig, ContributorConfig) and the *_instance*
    pattern used by LabelConfig.
    """
    from mcp_server.config.issue_config import IssueConfig
    from mcp_server.config.scope_config import ScopeConfig
    from mcp_server.config.workflow_config import WorkflowConfig
    from mcp_server.config.milestone_config import MilestoneConfig
    from mcp_server.config.contributor_config import ContributorConfig
    from mcp_server.config.label_config import LabelConfig

    def _reset_all() -> None:
        IssueConfig.singleton_instance = None
        ScopeConfig.singleton_instance = None
        WorkflowConfig.singleton_instance = None
        MilestoneConfig.singleton_instance = None
        ContributorConfig.singleton_instance = None
        LabelConfig.reset()

    _reset_all()
    yield
    _reset_all()
