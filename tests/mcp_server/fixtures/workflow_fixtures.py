"""
@module: tests.fixtures.workflow_fixtures
@layer: Test Infrastructure
@dependencies: pytest, mcp_server.config.loader
@responsibilities:
  - Provide workflow-phase fixtures for tests
  - Load phase lists from .st3/config/workflows.yaml via ConfigLoader
"""

from pathlib import Path

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import WorkflowConfig


def _make_loader() -> ConfigLoader:
    return ConfigLoader(Path(".st3/config"))


@pytest.fixture
def workflow_config() -> WorkflowConfig:
    """Load workflow configuration from .st3/config/workflows.yaml."""
    return _make_loader().load_workflow_config()


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
