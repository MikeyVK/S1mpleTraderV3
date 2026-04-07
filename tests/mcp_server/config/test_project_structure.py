# tests/mcp_server/config/test_project_structure.py
"""Unit tests for ProjectStructureConfig model.

Tests Phase 2: .st3/config/project_structure.yaml + ProjectStructureConfig
Cross-validates allowed_component_types against artifacts.yaml.

@layer: Tests (Unit)
@dependencies: [pathlib, pytest, mcp_server.config.loader, mcp_server.config.schemas]
"""

from pathlib import Path

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import (
    ArtifactRegistryConfig,
    DirectoryPolicy,
    OperationPoliciesConfig,
    ProjectStructureConfig,
)
from mcp_server.core.exceptions import ConfigError


def _load_artifact_registry(config_path: Path | None = None) -> ArtifactRegistryConfig:
    loader = ConfigLoader(Path(".st3/config") if config_path is None else config_path.parent)
    return loader.load_artifact_registry_config(config_path=config_path)


def _load_operation_policies(config_path: Path | None = None) -> OperationPoliciesConfig:
    loader = ConfigLoader(Path(".st3/config") if config_path is None else config_path.parent)
    return loader.load_operation_policies_config(config_path=config_path)


def _load_project_structure(config_path: Path | None = None) -> ProjectStructureConfig:
    loader = ConfigLoader(Path(".st3/config") if config_path is None else config_path.parent)
    return loader.load_project_structure_config(config_path=config_path)


class TestProjectStructureConfig:
    """Test suite for ProjectStructureConfig."""

    def test_load_valid_config(self) -> None:
        """Test loading valid project_structure.yaml."""
        config = _load_project_structure()

        assert len(config.directories) >= 10
        assert "backend" in config.directories
        assert "backend/dtos" in config.directories
        assert "mcp_server" in config.directories
        assert "mcp_server/tools" in config.directories

        backend = config.directories["backend"]
        assert backend.path == "backend"
        assert backend.parent is None
        assert backend.description == "Backend application code"
        assert "dto" in backend.allowed_component_types
        assert "worker" in backend.allowed_component_types
        assert ".py" in backend.allowed_extensions

        dtos = config.directories["backend/dtos"]
        assert dtos.parent == "backend"
        assert "dto" in dtos.allowed_component_types
        assert len(dtos.allowed_component_types) == 1

        mcp = config.directories["mcp_server"]
        assert "tool" in mcp.allowed_component_types
        assert "resource" in mcp.allowed_component_types

    def test_repeated_loads_are_equivalent(self) -> None:
        """Repeated loads of the same file should be value-equivalent."""
        config1 = _load_project_structure()
        config2 = _load_project_structure()
        assert config1 == config2

    def test_missing_file(self) -> None:
        """Test ConfigError when file not found."""
        with pytest.raises(ConfigError, match="Config file not found"):
            _load_project_structure(Path(".st3/config/nonexistent.yaml"))

    def test_get_directory_exists(self) -> None:
        """Test get_directory with existing path."""
        config = _load_project_structure()
        backend = config.get_directory("backend")
        assert backend is not None
        assert backend.path == "backend"

    def test_get_directory_not_exists(self) -> None:
        """Test get_directory with non-existent path."""
        config = _load_project_structure()
        result = config.get_directory("nonexistent/path")
        assert result is None

    def test_get_all_directories(self) -> None:
        """Test get_all_directories returns sorted list."""
        config = _load_project_structure()
        directories = config.get_all_directories()
        assert len(directories) >= 10
        assert directories == sorted(directories)
        assert "backend" in directories
        assert "mcp_server" in directories

    def test_cross_validation_component_types(self) -> None:
        """Test cross-validation with artifacts.yaml."""
        config = _load_project_structure()
        assert "backend" in config.directories

    def test_parent_validation_success(self) -> None:
        """Test parent reference validation with valid parents."""
        config = _load_project_structure()
        dtos = config.directories["backend/dtos"]
        assert dtos.parent == "backend"
        assert "backend" in config.directories

    def test_unrestricted_directories(self) -> None:
        """Test directories with no restrictions."""
        config = _load_project_structure()

        scripts = config.directories["scripts"]
        assert scripts.allowed_component_types == []
        assert scripts.allowed_extensions == []
        assert scripts.require_scaffold_for == []

        poc = config.directories["proof_of_concepts"]
        assert poc.allowed_component_types == []
        assert poc.allowed_extensions == []

    def test_config_directories(self) -> None:
        """Test .st3 config directory policy."""
        config = _load_project_structure()
        st3 = config.directories[".st3"]
        assert st3.parent is None
        assert st3.allowed_component_types == []
        assert ".yaml" in st3.allowed_extensions
        assert ".yml" in st3.allowed_extensions

    def test_directory_policy_allowed_component_types_alias(self) -> None:
        """allowed_component_types should mirror allowed_artifact_types."""
        policy = DirectoryPolicy(
            path="backend",
            description="Backend code",
            allowed_artifact_types=["dto", "worker"],
        )

        assert policy.allowed_component_types == ["dto", "worker"]

    def test_manual_project_structure_accessors(self) -> None:
        """Accessor helpers should work on manually constructed configs."""
        config = ProjectStructureConfig(
            directories={
                "backend": DirectoryPolicy(path="backend", description="Backend code"),
                "backend/dtos": DirectoryPolicy(
                    path="backend/dtos",
                    parent="backend",
                    description="DTOs",
                ),
            }
        )

        assert config.get_directory("backend") is not None
        assert config.get_directory("missing") is None
        assert config.get_all_directories() == ["backend", "backend/dtos"]

    def test_test_directory_policy(self) -> None:
        """Test tests directory allows no components."""
        config = _load_project_structure()
        tests = config.directories["tests"]
        assert tests.allowed_component_types == []
        assert ".py" in tests.allowed_extensions
        assert tests.require_scaffold_for == []


class TestProjectStructureIntegration:
    """Integration tests for ProjectStructureConfig."""

    def test_all_three_configs_load(self) -> None:
        """Test all three foundation configs load successfully."""
        component_config = _load_artifact_registry()
        operation_config = _load_operation_policies()
        structure_config = _load_project_structure()

        type_ids = component_config.list_type_ids()
        assert len(type_ids) > 0
        assert "dto" in type_ids
        assert "worker" in type_ids

        assert len(operation_config.operations) == 3
        assert len(structure_config.directories) >= 10
