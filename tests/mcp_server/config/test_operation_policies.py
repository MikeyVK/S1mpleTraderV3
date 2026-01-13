"""Unit tests for OperationPoliciesConfig model.

Tests Phase 1B: .st3/policies.yaml + OperationPoliciesConfig
Cross-validates allowed_phases against workflows.yaml
"""

import pytest

from mcp_server.config.operation_policies import (
    OperationPoliciesConfig,
    OperationPolicy,
)
from mcp_server.core.errors import ConfigError


class TestOperationPoliciesConfig:
    """Test suite for OperationPoliciesConfig."""

    def setup_method(self):
        """Reset singleton before each test."""
        OperationPoliciesConfig.reset_instance()

    def test_load_valid_config(self):
        """Test loading valid policies.yaml."""
        config = OperationPoliciesConfig.from_file(".st3/policies.yaml")

        # Verify 3 operations loaded
        assert len(config.operations) == 3
        assert "scaffold" in config.operations
        assert "create_file" in config.operations
        assert "commit" in config.operations

        # Verify scaffold policy
        scaffold = config.operations["scaffold"]
        assert scaffold.operation_id == "scaffold"
        assert scaffold.description == "Create new component from template"
        assert "design" in scaffold.allowed_phases
        assert "tdd" in scaffold.allowed_phases

        # Verify create_file policy
        create_file = config.operations["create_file"]
        assert create_file.allowed_phases == []  # All phases allowed
        assert "backend/**/*.py" in create_file.blocked_patterns
        assert ".md" in create_file.allowed_extensions

        # Verify commit policy
        commit = config.operations["commit"]
        assert commit.require_tdd_prefix is True
        assert "red:" in commit.allowed_prefixes
        assert "green:" in commit.allowed_prefixes
