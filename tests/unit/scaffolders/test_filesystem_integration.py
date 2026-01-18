import pytest
from unittest.mock import Mock, patch
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.errors import ConfigError

@pytest.fixture
def mock_registry():
    registry = Mock(spec=ArtifactRegistryConfig)
    artifact = Mock()
    artifact.type_id = 'test'
    artifact.required_fields = ['name']
    artifact.template_path = '.st3/templates/test.j2'
    artifact.fallback_template = None
    artifact.name_suffix = ''
    artifact.file_extension = '.py'
    registry.get_artifact.return_value = artifact
    return registry

@pytest.fixture
def scaffolder(mock_registry):
    return TemplateScaffolder(registry=mock_registry)

class TestTemplateReading:
    def test_template_loads_via_open(self, scaffolder):
        with patch('builtins.open') as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = 'content'
            _result = scaffolder.scaffold('test', name='Test')
            mock_open.assert_called_once()

    def test_ioerror_becomes_config_error(self, scaffolder):
        with patch('builtins.open', side_effect=IOError('fail')):
            with pytest.raises(ConfigError):
                scaffolder.scaffold('test', name='Test')
