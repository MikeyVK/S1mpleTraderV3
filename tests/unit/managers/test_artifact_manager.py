"""Unit tests for ArtifactManager."""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.core.exceptions import ValidationError


class TestArtifactManagerCore:
    """Test ArtifactManager core functionality."""

    def test_constructor_accepts_optional_registry(self):
        """Test that constructor accepts optional registry parameter."""
        mock_registry = Mock(spec=ArtifactRegistryConfig)
        manager = ArtifactManager(registry=mock_registry)
        assert manager.registry is mock_registry

    def test_constructor_accepts_optional_scaffolder(self):
        """Test that constructor accepts optional scaffolder parameter."""
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        manager = ArtifactManager(scaffolder=mock_scaffolder)
        assert manager.scaffolder is mock_scaffolder

    def test_scaffold_artifact_delegates_to_scaffolder(self):
        """Test that scaffold_artifact delegates to scaffolder."""
        # Valid Python content for validation
        valid_python_content = (
            '"""Test DTO."""\n\nclass TestDTO:\n    """Test DTO class."""\n    pass\n'
        )

        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.scaffold.return_value = Mock(
            content=valid_python_content,
            file_name='test.py'
        )

        mock_fs_adapter = Mock()
        # Mock resolve_path to return the absolute path
        mock_fs_adapter.resolve_path.return_value = Path('/test/test.py')

        mock_validation_service = Mock()
        mock_validation_service.validate_content.return_value = (True, "")

        # Mock get_artifact_path to avoid complex dependency chain
        with patch.object(
            ArtifactManager, 'get_artifact_path', return_value=Path('/test/test.py')
        ):
            manager = ArtifactManager(
                scaffolder=mock_scaffolder,
                fs_adapter=mock_fs_adapter,
                validation_service=mock_validation_service
            )
            result = manager.scaffold_artifact('dto', name='Test', fields=[])

        # Verify scaffolder was called with correct arguments
        mock_scaffolder.scaffold.assert_called_once_with('dto', name='Test', fields=[])

        # Verify validation was called
        mock_validation_service.validate_content.assert_called_once_with(
            valid_python_content,
            'dto'
        )

        # Verify file was written
        mock_fs_adapter.write_file.assert_called_once_with(
            str(Path('/test/test.py')),
            valid_python_content
        )

        # Verify path was returned (normalize for cross-platform)
        assert result == str(Path('/test/test.py'))

    def test_validate_artifact_delegates_to_scaffolder(self):
        """Test that validate_artifact delegates to scaffolder."""
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.validate.return_value = True

        manager = ArtifactManager(scaffolder=mock_scaffolder)
        result = manager.validate_artifact('dto', name='Test')

        assert result is True
        mock_scaffolder.validate.assert_called_once_with('dto', name='Test')

    def test_validation_error_propagates(self):
        """Test that validation errors propagate correctly."""
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.validate.side_effect = ValidationError('Missing field')

        manager = ArtifactManager(scaffolder=mock_scaffolder)
        with pytest.raises(ValidationError):
            manager.validate_artifact('dto', name='Test')

    def test_not_singleton(self):
        """Test that ArtifactManager is NOT a singleton."""
        manager1 = ArtifactManager()
        manager2 = ArtifactManager()
        assert manager1 is not manager2
