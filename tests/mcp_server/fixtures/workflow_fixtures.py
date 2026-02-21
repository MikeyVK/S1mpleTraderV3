"""
@module: tests.fixtures.workflow_fixtures
@layer: Test Infrastructure
@dependencies: pytest, mcp_server.config.workflows
@responsibilities:
  - Provide workflow-phase fixtures for tests
  - Load phase lists from .st3/workflows.yaml
"""

import pytest

from mcp_server.config.workflows import WorkflowConfig


@pytest.fixture
def workflow_config():
    """Load workflow configuration from .st3/workflows.yaml."""
    return WorkflowConfig.load()


@pytest.fixture
def workflow_phases(workflow_config: WorkflowConfig) -> list[str]:
    """
    All unique phases across all workflows.

    Returns list like: ["research", "planning", "design", "tdd", "integration", "documentation", "coordination"]
    """
    all_phases = set()
    for workflow in workflow_config.workflows.values():
        all_phases.update(workflow.phases)
    return sorted(all_phases)


@pytest.fixture
def feature_phases(workflow_config: WorkflowConfig) -> list[str]:
    """
    Phases for feature workflow.

    Returns: ["research", "planning", "design", "tdd", "integration", "documentation"]
    """
    return workflow_config.workflows["feature"].phases


@pytest.fixture
def bug_phases(workflow_config: WorkflowConfig) -> list[str]:
    """
    Phases for bug workflow.

    Returns: ["research", "planning", "design", "tdd", "integration", "documentation"]
    """
    return workflow_config.workflows["bug"].phases


@pytest.fixture
def hotfix_phases(workflow_config: WorkflowConfig) -> list[str]:
    """
    Phases for hotfix workflow.

    Returns: ["tdd", "integration", "documentation"]
    """
    return workflow_config.workflows["hotfix"].phases
