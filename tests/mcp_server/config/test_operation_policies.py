# tests/mcp_server/config/test_operation_policies.py
"""Unit tests for OperationPoliciesConfig model.

Tests Phase 1B: .st3/config/policies.yaml + OperationPoliciesConfig
Cross-validates allowed_phases against workflows.yaml.

@layer: Tests (Unit)
@dependencies: [pathlib, pytest, mcp_server.config.loader, mcp_server.config.schemas]
"""

from pathlib import Path

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import OperationPoliciesConfig, OperationPolicy
from mcp_server.core.exceptions import ConfigError


def _load_operation_policies(config_path: Path | None = None) -> OperationPoliciesConfig:
    loader = ConfigLoader(Path(".st3/config") if config_path is None else config_path.parent)
    return loader.load_operation_policies_config(config_path=config_path)


class TestOperationPoliciesConfig:
    """Test suite for OperationPoliciesConfig."""

    def test_load_valid_config(self) -> None:
        """Test loading valid policies.yaml."""
        config = _load_operation_policies()

        assert len(config.operations) == 3
        assert "scaffold" in config.operations
        assert "create_file" in config.operations
        assert "commit" in config.operations

        scaffold = config.operations["scaffold"]
        assert scaffold.operation_id == "scaffold"
        assert scaffold.description == "Create new component from template"
        assert "design" in scaffold.allowed_phases
        assert "implementation" in scaffold.allowed_phases

        create_file = config.operations["create_file"]
        assert create_file.allowed_phases == []
        assert "backend/**" in create_file.blocked_patterns
        assert ".md" in create_file.allowed_extensions

        commit = config.operations["commit"]
        assert commit.require_tdd_prefix is True
        assert commit.allowed_prefixes == []  # dead field removed from policies.yaml (issue #270)

    def test_repeated_loads_are_equivalent(self) -> None:
        """Repeated loads of the same file should be value-equivalent."""
        config1 = _load_operation_policies()
        config2 = _load_operation_policies()
        assert config1 == config2

    def test_missing_file(self) -> None:
        """Test ConfigError when file not found."""
        with pytest.raises(ConfigError, match="Config file not found"):
            _load_operation_policies(Path(".st3/config/nonexistent.yaml"))

    def test_get_operation_policy_valid(self) -> None:
        """Test get_operation_policy with valid operation."""
        config = _load_operation_policies()
        scaffold = config.get_operation_policy("scaffold")
        assert scaffold.operation_id == "scaffold"
        assert "design" in scaffold.allowed_phases

    def test_get_operation_policy_invalid(self) -> None:
        """Test get_operation_policy with unknown operation."""
        config = _load_operation_policies()
        with pytest.raises(ValueError, match="Unknown operation"):
            config.get_operation_policy("invalid_op")

    def test_get_available_operations(self) -> None:
        """Test get_available_operations returns sorted list."""
        config = _load_operation_policies()
        operations = config.get_available_operations()
        assert operations == ["commit", "create_file", "scaffold"]

    def test_is_allowed_in_phase_explicit(self) -> None:
        """Test phase check with explicit allowed_phases."""
        config = _load_operation_policies()
        scaffold = config.get_operation_policy("scaffold")
        assert scaffold.is_allowed_in_phase("design") is True
        assert scaffold.is_allowed_in_phase("implementation") is True
        assert scaffold.is_allowed_in_phase("refactor") is False

    def test_is_allowed_in_phase_empty(self) -> None:
        """Test phase check with empty allowed_phases (all allowed)."""
        config = _load_operation_policies()
        create = config.get_operation_policy("create_file")
        assert create.is_allowed_in_phase("design") is True
        assert create.is_allowed_in_phase("refactor") is True
        assert create.is_allowed_in_phase("any_phase") is True

    def test_is_path_blocked(self) -> None:
        """Test glob pattern matching for blocked paths."""
        config = _load_operation_policies()
        create = config.get_operation_policy("create_file")
        assert create.is_path_blocked("backend/foo.py") is True
        assert create.is_path_blocked("backend/services/user.py") is True
        assert create.is_path_blocked("mcp_server/tools/my_tool.py") is True
        assert create.is_path_blocked("scripts/bar.sh") is False
        assert create.is_path_blocked("docs/readme.md") is False

    def test_is_extension_allowed(self) -> None:
        """Test extension validation."""
        config = _load_operation_policies()
        create = config.get_operation_policy("create_file")
        assert create.is_extension_allowed("docs/foo.md") is True
        assert create.is_extension_allowed("config.yaml") is True
        assert create.is_extension_allowed("backend/foo.py") is False
        assert create.is_extension_allowed("test.exe") is False

    def test_is_extension_allowed_without_restrictions(self) -> None:
        """Policies with no extension restrictions should allow any suffix."""
        policy = OperationPolicy(
            operation_id="create_file",
            description="Create file",
        )

        assert policy.is_extension_allowed("backend/service.py") is True

    def test_validate_extension_format_rejects_missing_dot(self) -> None:
        """Extensions without a leading dot must be rejected."""
        with pytest.raises(ValueError, match="must start with dot"):
            OperationPolicy(
                operation_id="create_file",
                description="Create file",
                allowed_extensions=["py"],
            )

    def test_validate_commit_message_required(self) -> None:
        """Test TDD prefix validation when required."""
        config = _load_operation_policies()
        commit = config.get_operation_policy("commit")
        assert commit.validate_commit_message("red: add failing test") is True
        assert commit.validate_commit_message("green: implement feature") is True
        assert commit.validate_commit_message("refactor: cleanup") is True
        assert commit.validate_commit_message("docs: update readme") is True
        assert commit.validate_commit_message("invalid: bad prefix") is False
        assert commit.validate_commit_message("no prefix message") is False

    def test_validate_commit_message_not_required(self) -> None:
        """Test commit message validation when not required."""
        config = _load_operation_policies()
        scaffold = config.get_operation_policy("scaffold")
        assert scaffold.validate_commit_message("any message") is True


class TestOperationPoliciesIntegration:
    """Integration tests for OperationPoliciesConfig."""

    def test_cross_validation_success(self) -> None:
        """Test cross-validation with valid phases."""
        config = _load_operation_policies()
        assert "scaffold" in config.operations
