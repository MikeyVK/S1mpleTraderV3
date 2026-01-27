"""Unit tests for OperationPoliciesConfig model.

Tests Phase 1B: .st3/policies.yaml + OperationPoliciesConfig
Cross-validates allowed_phases against workflows.yaml
"""

import pytest

from mcp_server.config.operation_policies import (
    OperationPoliciesConfig,
)
from mcp_server.core.exceptions import ConfigError


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
        assert "backend/**" in create_file.blocked_patterns
        assert ".md" in create_file.allowed_extensions

        # Verify commit policy
        commit = config.operations["commit"]
        assert commit.require_tdd_prefix is True
        assert "red:" in commit.allowed_prefixes
        assert "green:" in commit.allowed_prefixes

    def test_singleton_pattern(self):
        """Test singleton returns same instance."""
        config1 = OperationPoliciesConfig.from_file(".st3/policies.yaml")
        config2 = OperationPoliciesConfig.from_file(".st3/policies.yaml")
        assert config1 is config2

    def test_missing_file(self):
        """Test ConfigError when file not found."""
        with pytest.raises(ConfigError, match="Config file not found"):
            OperationPoliciesConfig.from_file(".st3/nonexistent.yaml")

    def test_get_operation_policy_valid(self):
        """Test get_operation_policy with valid operation."""
        config = OperationPoliciesConfig.from_file()
        scaffold = config.get_operation_policy("scaffold")
        assert scaffold.operation_id == "scaffold"
        assert "design" in scaffold.allowed_phases

    def test_get_operation_policy_invalid(self):
        """Test get_operation_policy with unknown operation."""
        config = OperationPoliciesConfig.from_file()
        with pytest.raises(ValueError, match="Unknown operation"):
            config.get_operation_policy("invalid_op")

    def test_get_available_operations(self):
        """Test get_available_operations returns sorted list."""
        config = OperationPoliciesConfig.from_file()
        operations = config.get_available_operations()
        assert operations == ["commit", "create_file", "scaffold"]

    def test_is_allowed_in_phase_explicit(self):
        """Test phase check with explicit allowed_phases."""
        config = OperationPoliciesConfig.from_file()
        scaffold = config.get_operation_policy("scaffold")
        assert scaffold.is_allowed_in_phase("design") is True
        assert scaffold.is_allowed_in_phase("tdd") is True
        assert scaffold.is_allowed_in_phase("refactor") is False

    def test_is_allowed_in_phase_empty(self):
        """Test phase check with empty allowed_phases (all allowed)."""
        config = OperationPoliciesConfig.from_file()
        create = config.get_operation_policy("create_file")
        assert create.is_allowed_in_phase("design") is True
        assert create.is_allowed_in_phase("refactor") is True
        assert create.is_allowed_in_phase("any_phase") is True

    def test_is_path_blocked(self):
        """Test glob pattern matching for blocked paths."""
        config = OperationPoliciesConfig.from_file()
        create = config.get_operation_policy("create_file")
        assert create.is_path_blocked("backend/foo.py") is True
        assert create.is_path_blocked("backend/services/user.py") is True
        assert create.is_path_blocked("mcp_server/tools/my_tool.py") is True
        assert create.is_path_blocked("scripts/bar.sh") is False
        assert create.is_path_blocked("docs/readme.md") is False

    def test_is_extension_allowed(self):
        """Test extension validation."""
        config = OperationPoliciesConfig.from_file()
        create = config.get_operation_policy("create_file")
        assert create.is_extension_allowed("docs/foo.md") is True
        assert create.is_extension_allowed("config.yaml") is True
        assert create.is_extension_allowed("backend/foo.py") is False
        assert create.is_extension_allowed("test.exe") is False

    def test_validate_commit_message_required(self):
        """Test TDD prefix validation when required."""
        config = OperationPoliciesConfig.from_file()
        commit = config.get_operation_policy("commit")
        assert commit.validate_commit_message("red: add failing test") is True
        assert commit.validate_commit_message("green: implement feature") is True
        assert commit.validate_commit_message("refactor: cleanup") is True
        assert commit.validate_commit_message("docs: update readme") is True
        assert commit.validate_commit_message("invalid: bad prefix") is False
        assert commit.validate_commit_message("no prefix message") is False

    def test_validate_commit_message_not_required(self):
        """Test commit message validation when not required."""
        # Scaffold operation doesn't require TDD prefix
        config = OperationPoliciesConfig.from_file()
        scaffold = config.get_operation_policy("scaffold")
        assert scaffold.validate_commit_message("any message") is True


class TestOperationPoliciesIntegration:
    """Integration tests for OperationPoliciesConfig."""

    def setup_method(self):
        """Reset singleton before each test."""
        OperationPoliciesConfig.reset_instance()

    def test_cross_validation_success(self):
        """Test cross-validation with valid phases."""
        # All phases in policies.yaml exist in workflows.yaml
        config = OperationPoliciesConfig.from_file()
        assert "scaffold" in config.operations
        # No ConfigError should be raised
