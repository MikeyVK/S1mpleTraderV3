import pytest
from pathlib import Path
from unittest.mock import Mock
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.core.errors import ValidationError

class TestArtifactManagerCore:
    def test_constructor_accepts_workspace_root(self):
        from mcp_server.managers.artifact_manager import ArtifactManager
        manager = ArtifactManager(workspace_root=Path('/test'))
        assert manager.workspace_root == Path('/test')
    
    def test_constructor_accepts_optional_registry(self):
        from mcp_server.managers.artifact_manager import ArtifactManager
        mock_registry = Mock(spec=ArtifactRegistryConfig)
        manager = ArtifactManager(registry=mock_registry)
        assert manager.registry is mock_registry
    
    def test_constructor_accepts_optional_scaffolder(self):
        from mcp_server.managers.artifact_manager import ArtifactManager
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        manager = ArtifactManager(scaffolder=mock_scaffolder)
        assert manager.scaffolder is mock_scaffolder
    
    def test_scaffold_artifact_delegates_to_scaffolder(self):
        from mcp_server.managers.artifact_manager import ArtifactManager
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.scaffold.return_value = Mock(content='test', file_name='test.py')
        
        manager = ArtifactManager(scaffolder=mock_scaffolder)
        manager.scaffold_artifact('dto', name='Test', fields=[])
        
        mock_scaffolder.scaffold.assert_called_once_with('dto', name='Test', fields=[])
    
    def test_validate_artifact_delegates_to_scaffolder(self):
        from mcp_server.managers.artifact_manager import ArtifactManager
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.validate.return_value = True
        
        manager = ArtifactManager(scaffolder=mock_scaffolder)
        result = manager.validate_artifact('dto', name='Test')
        
        assert result is True
        mock_scaffolder.validate.assert_called_once_with('dto', name='Test')
    
    def test_validation_error_propagates(self):
        from mcp_server.managers.artifact_manager import ArtifactManager
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.validate.side_effect = ValidationError('Missing field')
        
        manager = ArtifactManager(scaffolder=mock_scaffolder)
        with pytest.raises(ValidationError):
            manager.validate_artifact('dto', name='Test')
    
    def test_not_singleton(self):
        from mcp_server.managers.artifact_manager import ArtifactManager
        manager1 = ArtifactManager()
        manager2 = ArtifactManager()
        assert manager1 is not manager2
