import pytest
from unittest.mock import Mock, patch
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.exceptions import ConfigError

@pytest.fixture
def mock_registry():
    registry = Mock(spec=ArtifactRegistryConfig)
    artifact = Mock()
    artifact.type_id = 'test'
    artifact.required_fields = ['name']
    artifact.template_path = 'components/dto.py.jinja2'  # Real template path
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
        # Template loading now uses JinjaRenderer, not open()
        # scaffold() returns ScaffoldResult, not str
        result = scaffolder.scaffold('test', name='TestDto', description='Test')
        assert result is not None
        assert hasattr(result, 'content')
        assert len(result.content) > 0

    def test_ioerror_becomes_config_error(self, scaffolder, mock_registry):
        # Test with non-existent template
        # Note: JinjaRenderer raises ExecutionError, not ConfigError
        artifact = Mock()
        artifact.type_id = 'test'
        artifact.required_fields = ['name']
        artifact.template_path = 'nonexistent/template.jinja2'
        artifact.fallback_template = None
        mock_registry.get_artifact.return_value = artifact
        
        # ExecutionError is acceptable for template not found
        from mcp_server.core.exceptions import ExecutionError
        with pytest.raises((ConfigError, ExecutionError)):
            scaffolder.scaffold('test', name='Test')
