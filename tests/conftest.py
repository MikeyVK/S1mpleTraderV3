"""
Pytest configuration and shared fixtures for S1mpleTrader V3 tests.

This module provides shared test fixtures and pytest configuration
following the TDD principles outlined in the architecture documentation.

@layer: Tests
@dependencies: [pytest]
"""

import pytest

from backend.dtos.shared.disposition_envelope import DispositionEnvelope
from mcp_server.config.workflows import WorkflowConfig


@pytest.fixture
def sample_continue_envelope():
    """Fixture providing a sample CONTINUE disposition envelope."""
    return DispositionEnvelope(disposition="CONTINUE")


@pytest.fixture
def sample_stop_envelope():
    """Fixture providing a sample STOP disposition envelope."""
    return DispositionEnvelope(disposition="STOP")


@pytest.fixture(scope="session")
def workflow_config():
    """Load workflow config once per test session."""
    return WorkflowConfig.load()


@pytest.fixture
def workflow_phases(workflow_config):  # pylint: disable=redefined-outer-name
    """
    Access to all workflow phases from configuration.
    
    Returns dict mapping workflow name to list of phases:
    {
        "feature": ["research", "planning", "design", "tdd", "integration", "documentation"],
        "bug": ["research", "planning", "tdd", "integration", "documentation"],
        ...
    }
    """
    return {name: wf.phases for name, wf in workflow_config.workflows.items()}


@pytest.fixture
def feature_phases(workflow_phases):  # pylint: disable=redefined-outer-name
    """Shortcut to feature workflow phases."""
    return workflow_phases["feature"]


@pytest.fixture
def bug_phases(workflow_phases):  # pylint: disable=redefined-outer-name
    """Shortcut to bug workflow phases."""
    return workflow_phases["bug"]


@pytest.fixture
def hotfix_phases(workflow_phases):  # pylint: disable=redefined-outer-name
    """Shortcut to hotfix workflow phases."""
    return workflow_phases["hotfix"]


@pytest.fixture
def refactor_phases(workflow_phases):  # pylint: disable=redefined-outer-name
    """Shortcut to refactor workflow phases."""
    return workflow_phases["refactor"]


@pytest.fixture
def docs_phases(workflow_phases):  # pylint: disable=redefined-outer-name
    """Shortcut to docs workflow phases."""
    return workflow_phases["docs"]
