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
from mcp_server.core.errors import ConfigError


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
