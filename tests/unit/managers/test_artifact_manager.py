"""Unit tests for ArtifactManager."""
from pathlib import Path
from unittest.mock import Mock

import pytest

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.core.errors import ValidationError


class TestArtifactManagerCore:
    """Test ArtifactManager core functionality."""

    def test_constructor_accepts_workspace_root(self):
        """Test that constructor accepts workspace_root parameter."""
        from mcp_server.managers.artifact_manager import ArtifactManager
        manager = ArtifactManager(workspace_root=Path('/test'))
        assert manager.workspace_root == Path('/test')

    def test_constructor_accepts_optional_registry(self):
        """Test that constructor accepts optional registry parameter."""
        from mcp_server.managers.artifact_manager import ArtifactManager
        mock_registry = Mock(spec=ArtifactRegistryConfig)
        manager = ArtifactManager(registry=mock_registry)
        assert manager.registry is mock_registry

    def test_constructor_accepts_optional_scaffolder(self):
        """Test that constructor accepts optional scaffolder parameter."""
        from mcp_server.managers.artifact_manager import ArtifactManager
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        manager = ArtifactManager(scaffolder=mock_scaffolder)
        assert manager.scaffolder is mock_scaffolder

    def test_scaffold_artifact_delegates_to_scaffolder(self):
        """Test that scaffold_artifact delegates to scaffolder."""
        from mcp_server.managers.artifact_manager import ArtifactManager
        from unittest.mock import patch

        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.scaffold.return_value = Mock(content='test', file_name='test.py')

        # Mock get_artifact_path to avoid complex dependency chain
        with patch.object(ArtifactManager, 'get_artifact_path', return_value=Path('/test/test.py')):
            manager = ArtifactManager(scaffolder=mock_scaffolder)
            result = manager.scaffold_artifact('dto', name='Test', fields=[])

        # Verify scaffolder was called with correct arguments
        mock_scaffolder.scaffold.assert_called_once_with('dto', name='Test', fields=[])
        # Verify path was returned (normalize for cross-platform)
        assert result == str(Path('/test/test.py'))

    def test_validate_artifact_delegates_to_scaffolder(self):
        """Test that validate_artifact delegates to scaffolder."""
        from mcp_server.managers.artifact_manager import ArtifactManager
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.validate.return_value = True

        manager = ArtifactManager(scaffolder=mock_scaffolder)
        result = manager.validate_artifact('dto', name='Test')

        assert result is True
        mock_scaffolder.validate.assert_called_once_with('dto', name='Test')

    def test_validation_error_propagates(self):
        """Test that validation errors propagate correctly."""
        from mcp_server.managers.artifact_manager import ArtifactManager
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.validate.side_effect = ValidationError('Missing field')

        manager = ArtifactManager(scaffolder=mock_scaffolder)
        with pytest.raises(ValidationError):
            manager.validate_artifact('dto', name='Test')

    def test_not_singleton(self):
        """Test that ArtifactManager is NOT a singleton."""
        from mcp_server.managers.artifact_manager import ArtifactManager
        manager1 = ArtifactManager()
        manager2 = ArtifactManager()
        assert manager1 is not manager2
