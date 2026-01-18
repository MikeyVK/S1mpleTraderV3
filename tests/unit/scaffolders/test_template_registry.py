import pytest
from unittest.mock import Mock, patch, call
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.exceptions import ConfigError

@pytest.fixture
def mock_registry():
    registry = Mock(spec=ArtifactRegistryConfig)
    return registry

@pytest.fixture
def scaffolder(mock_registry):
    return TemplateScaffolder(registry=mock_registry)

class TestTemplateRegistryLoading:
    def test_loads_artifact_from_registry(self, scaffolder, mock_registry):
        artifact = Mock()
        artifact.type_id = 'dto'
        artifact.required_fields = ['name']
        artifact.template_path = 'templates/dto.j2'
        artifact.fallback_template = None
        artifact.name_suffix = ''
        artifact.file_extension = '.py'
        mock_registry.get_artifact.return_value = artifact
        
        with patch('builtins.open') as m:
            m.return_value.__enter__.return_value.read.return_value = 'test'
            scaffolder.scaffold('dto', name='Test')
        
        # Called in validate() and scaffold()
        assert mock_registry.get_artifact.call_count == 2
        assert all(c == call('dto') for c in mock_registry.get_artifact.call_args_list)
    
    def test_uses_template_path_from_artifact(self, scaffolder, mock_registry):
        artifact = Mock()
        artifact.type_id = 'worker'
        artifact.required_fields = []
        artifact.template_path = 'custom/worker.j2'
        artifact.fallback_template = None
        artifact.name_suffix = ''
        artifact.file_extension = '.py'
        mock_registry.get_artifact.return_value = artifact
        
        with patch('builtins.open') as m:
            m.return_value.__enter__.return_value.read.return_value = 'content'
            scaffolder.scaffold('worker', name='Test')
            m.assert_called_with('custom/worker.j2', 'r', encoding='utf-8')
    
    def test_uses_fallback_when_primary_none(self, scaffolder, mock_registry):
        artifact = Mock()
        artifact.type_id = 'test'
        artifact.required_fields = []
        artifact.template_path = None
        artifact.fallback_template = 'fallback.j2'
        artifact.name_suffix = ''
        artifact.file_extension = '.py'
        mock_registry.get_artifact.return_value = artifact
        
        with patch('builtins.open') as m:
            m.return_value.__enter__.return_value.read.return_value = 'fb'
            scaffolder.scaffold('test', name='Test')
            m.assert_called_with('fallback.j2', 'r', encoding='utf-8')
    
    def test_error_when_no_template_defined(self, scaffolder, mock_registry):
        artifact = Mock()
        artifact.type_id = 'broken'
        artifact.required_fields = []
        artifact.template_path = None
        artifact.fallback_template = None
        mock_registry.get_artifact.return_value = artifact
        
        with pytest.raises(ConfigError) as exc:
            scaffolder.scaffold('broken', name='Test')
        assert 'No template defined' in str(exc.value)
