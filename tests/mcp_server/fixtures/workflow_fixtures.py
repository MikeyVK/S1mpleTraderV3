"""
@module: tests.fixtures.workflow_fixtures
@layer: Test Infrastructure
@dependencies: pytest, mcp_server.config.loader
@responsibilities:
  - Provide workflow-phase fixtures for tests
  - Load phase lists from .pgmcp/config/contracts.yaml via ConfigLoader (SSOT)
  - workflows.yaml fixtures retained for backward compat with WorkflowConfig tests
"""

from pathlib import Path

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import WorkflowConfig
from mcp_server.config.schemas.contracts_config import ContractsConfig
from tests.mcp_server.test_support import get_default_server_root


def _make_loader() -> ConfigLoader:
    return ConfigLoader(Path(get_default_server_root()) / "config")


@pytest.fixture
def workflow_config() -> WorkflowConfig:
    """Load workflow configuration from .pgmcp/config/workflows.yaml."""
    return _make_loader().load_workflow_config()


@pytest.fixture
def contracts_config() -> ContractsConfig:
    """Load ContractsConfig from .pgmcp/config/contracts.yaml (SSOT)."""
    return _make_loader().load_contracts_config()


@pytest.fixture
def workflow_phases(workflow_config: WorkflowConfig) -> list[str]:
    """
    All unique phases across all workflows.

    Returns list like:
    ["research", "planning", "design", "implementation", "validation",
    "documentation", "coordination"]
    """
    all_phases = set()
    for workflow in workflow_config.workflows.values():
        all_phases.update(workflow.phases)
    return sorted(all_phases)


@pytest.fixture
def feature_phases(contracts_config: ContractsConfig) -> list[str]:
    """
    Phases for feature workflow from contracts.yaml (SSOT).

    Returns: ["research", "planning", "design", "implementation", "validation",
              "documentation", "ready"]
    """
    return contracts_config.get_phases("feature")


@pytest.fixture
def bug_phases(contracts_config: ContractsConfig) -> list[str]:
    """
    Phases for bug workflow from contracts.yaml (SSOT).
    """
    return contracts_config.get_phases("bug")


@pytest.fixture
def hotfix_phases(contracts_config: ContractsConfig) -> list[str]:
    """
    Phases for hotfix workflow from contracts.yaml (SSOT).
    """
    return contracts_config.get_phases("hotfix")
