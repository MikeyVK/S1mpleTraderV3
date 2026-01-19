"""Unit tests for DirectoryPolicyResolver.

Tests Phase 3: Directory policy resolution with inheritance
"""

import pytest

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.config.project_structure import ProjectStructureConfig
from mcp_server.core.directory_policy_resolver import (
    DirectoryPolicyResolver,
    ResolvedDirectoryPolicy,
)


class TestDirectoryPolicyResolver:
    """Test suite for DirectoryPolicyResolver."""

    def setup_method(self):
        """Reset singletons before each test."""
        ArtifactRegistryConfig.reset_instance()
        ProjectStructureConfig.reset_instance()

    def test_exact_path_match(self):
        """Test exact directory match."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("backend")
        assert policy.path == "backend"
        assert "dto" in policy.allowed_component_types
        assert "worker" in policy.allowed_component_types

    def test_parent_directory_match(self):
        """Test walking up parent chain."""
        resolver = DirectoryPolicyResolver()
        # backend/foo doesn't exist in config, should resolve to backend
        policy = resolver.resolve("backend/foo")
        assert "dto" in policy.allowed_component_types
        assert "worker" in policy.allowed_component_types

    def test_inheritance_extensions(self):
        """Test allowed_extensions inheritance."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("backend/dtos")
        # backend/dtos doesn't specify extensions, should inherit from backend
        assert ".py" in policy.allowed_extensions

    def test_inheritance_component_types_override(self):
        """Test allowed_component_types override (no merge)."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("backend/dtos")
        # backend/dtos overrides with [dto], should NOT include worker from backend
        assert policy.allowed_component_types == ["dto"]

    def test_inheritance_scaffold_cumulative(self):
        """Test require_scaffold_for cumulative inheritance."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("backend/dtos")
        # Should include patterns from both backend/dtos and backend (cumulative)
        assert "**/*.py" in policy.require_scaffold_for

    def test_fallback_permissive(self):
        """Test fallback to permissive default for unknown paths."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("unknown/path")
        # Should return permissive default (all allowed)
        assert not policy.allowed_component_types  # Empty = all allowed
        assert not policy.allowed_extensions

    def test_allows_component_type(self):
        """Test component type validation."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("backend/dtos")
        assert policy.allows_component_type("dto") is True
        assert policy.allows_component_type("worker") is False

    def test_allows_extension(self):
        """Test extension validation."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("backend")
        assert policy.allows_extension("backend/foo.py") is True
        assert policy.allows_extension("backend/foo.js") is False

    def test_requires_scaffold(self):
        """Test scaffold requirement pattern matching."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("backend")
        assert policy.requires_scaffold("backend/foo.py") is True
        assert policy.requires_scaffold("backend/README.md") is False

    def test_file_path_resolves_to_directory(self):
        """Test file path resolves to parent directory."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("backend/dtos/user.py")
        # Should resolve to backend/dtos directory
        assert policy.path == "backend/dtos"
        assert "dto" in policy.allowed_component_types


class TestDocumentArtifactDirectories:
    """Test document artifact directory configuration (Cycle 3)."""

    def setup_method(self):
        """Reset singletons before each test."""
        ArtifactRegistryConfig.reset_instance()
        ProjectStructureConfig.reset_instance()

    def test_docs_root_allows_document_types(self):
        """docs/ directory allows document artifact types."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("docs")

        # Should allow document types (after allowed_artifact_types rename)
        # NOTE: Will pass after component→artifact rename
        assert "research" in policy.allowed_artifact_types
        assert "planning" in policy.allowed_artifact_types
        assert "design" in policy.allowed_artifact_types
        assert "architecture" in policy.allowed_artifact_types
        assert "tracking" in policy.allowed_artifact_types
        assert "reference" in policy.allowed_artifact_types

    def test_docs_development_subdirectory(self):
        """docs/development allows phase documents."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("docs/development")

        assert "research" in policy.allowed_artifact_types
        assert "planning" in policy.allowed_artifact_types
        assert "design" in policy.allowed_artifact_types
        assert "tracking" in policy.allowed_artifact_types

    def test_docs_architecture_subdirectory(self):
        """docs/architecture allows architecture docs."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("docs/architecture")

        assert "architecture" in policy.allowed_artifact_types
        assert "reference" in policy.allowed_artifact_types

    def test_markdown_extension_allowed_in_docs(self):
        """Markdown files allowed in docs directories."""
        resolver = DirectoryPolicyResolver()
        policy = resolver.resolve("docs")

        assert policy.allows_extension("test.md")
        assert policy.allows_extension("test.rst")
