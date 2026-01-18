"""Unit tests for ProjectStructureConfig model.

Tests Phase 2: .st3/project_structure.yaml + ProjectStructureConfig
Cross-validates allowed_component_types against components.yaml
"""

import pytest

from mcp_server.config.component_registry import ComponentRegistryConfig
from mcp_server.config.project_structure import (
    ProjectStructureConfig,
    DirectoryPolicy,
)
from mcp_server.core.exceptions import ConfigError


class TestProjectStructureConfig:
    """Test suite for ProjectStructureConfig."""

    def setup_method(self):
        """Reset singletons before each test."""
        ComponentRegistryConfig.reset_instance()
        ProjectStructureConfig.reset_instance()

    def test_load_valid_config(self):
        """Test loading valid project_structure.yaml."""
        config = ProjectStructureConfig.from_file(".st3/project_structure.yaml")

        # Verify 15 directories loaded
        assert len(config.directories) >= 10
        assert "backend" in config.directories
        assert "backend/dtos" in config.directories
        assert "mcp_server" in config.directories
        assert "mcp_server/tools" in config.directories

        # Verify backend policy
        backend = config.directories["backend"]
        assert backend.path == "backend"
        assert backend.parent is None
        assert backend.description == "Backend application code"
        assert "dto" in backend.allowed_component_types
        assert "worker" in backend.allowed_component_types
        assert ".py" in backend.allowed_extensions

        # Verify backend/dtos policy (inherits from backend)
        dtos = config.directories["backend/dtos"]
        assert dtos.parent == "backend"
        assert "dto" in dtos.allowed_component_types
        assert len(dtos.allowed_component_types) == 1  # Only dto

        # Verify mcp_server policy
        mcp = config.directories["mcp_server"]
        assert "tool" in mcp.allowed_component_types
        assert "resource" in mcp.allowed_component_types

    def test_singleton_pattern(self):
        """Test singleton returns same instance."""
        config1 = ProjectStructureConfig.from_file()
        config2 = ProjectStructureConfig.from_file()
        assert config1 is config2

    def test_missing_file(self):
        """Test ConfigError when file not found."""
        with pytest.raises(ConfigError, match="Config file not found"):
            ProjectStructureConfig.from_file(".st3/nonexistent.yaml")

    def test_get_directory_exists(self):
        """Test get_directory with existing path."""
        config = ProjectStructureConfig.from_file()
        backend = config.get_directory("backend")
        assert backend is not None
        assert backend.path == "backend"

    def test_get_directory_not_exists(self):
        """Test get_directory with non-existent path."""
        config = ProjectStructureConfig.from_file()
        result = config.get_directory("nonexistent/path")
        assert result is None

    def test_get_all_directories(self):
        """Test get_all_directories returns sorted list."""
        config = ProjectStructureConfig.from_file()
        directories = config.get_all_directories()
        assert len(directories) >= 10
        assert directories == sorted(directories)
        assert "backend" in directories
        assert "mcp_server" in directories

    def test_cross_validation_component_types(self):
        """Test cross-validation with components.yaml."""
        # All component types in project_structure.yaml
        # must exist in components.yaml
        config = ProjectStructureConfig.from_file()
        assert "backend" in config.directories
        # No ConfigError raised = validation passed

    def test_parent_validation_success(self):
        """Test parent reference validation with valid parents."""
        config = ProjectStructureConfig.from_file()
        dtos = config.directories["backend/dtos"]
        assert dtos.parent == "backend"
        assert "backend" in config.directories

    def test_unrestricted_directories(self):
        """Test directories with no restrictions."""
        config = ProjectStructureConfig.from_file()

        # scripts - no restrictions
        scripts = config.directories["scripts"]
        assert scripts.allowed_component_types == []
        assert scripts.allowed_extensions == []
        assert scripts.require_scaffold_for == []

        # proof_of_concepts - no restrictions
        poc = config.directories["proof_of_concepts"]
        assert poc.allowed_component_types == []
        assert poc.allowed_extensions == []

    def test_config_directories(self):
        """Test .st3 config directory policy."""
        config = ProjectStructureConfig.from_file()
        st3 = config.directories[".st3"]
        assert st3.parent is None
        assert st3.allowed_component_types == []
        assert ".yaml" in st3.allowed_extensions
        assert ".yml" in st3.allowed_extensions

    def test_test_directory_policy(self):
        """Test tests directory allows no components."""
        config = ProjectStructureConfig.from_file()
        tests = config.directories["tests"]
        assert tests.allowed_component_types == []
        assert ".py" in tests.allowed_extensions
        assert tests.require_scaffold_for == []


class TestProjectStructureIntegration:
    """Integration tests for ProjectStructureConfig."""

    def setup_method(self):
        """Reset singletons before each test."""
        ComponentRegistryConfig.reset_instance()
        ProjectStructureConfig.reset_instance()

    def test_all_three_configs_load(self):
        """Test all three foundation configs load successfully."""
        from mcp_server.config.operation_policies import OperationPoliciesConfig

        OperationPoliciesConfig.reset_instance()

        component_config = ComponentRegistryConfig.from_file()
        operation_config = OperationPoliciesConfig.from_file()
        structure_config = ProjectStructureConfig.from_file()

        assert len(component_config.components) == 9
        assert len(operation_config.operations) == 3
        assert len(structure_config.directories) >= 10
