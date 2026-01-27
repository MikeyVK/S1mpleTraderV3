from unittest.mock import Mock

import pytest

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder


@pytest.fixture
def mock_registry():
    registry = Mock(spec=ArtifactRegistryConfig)
    artifact = Mock()
    artifact.type_id = 'test'
    artifact.required_fields = ['name']
    artifact.template_path = 'concrete/dto.py.jinja2'  # Updated template path (Task 1.6)
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
        result = scaffolder.scaffold(
            'test',
            name='TestDto',
            description='Test',
            frozen=True,
            examples=[{"test": "data"}],
            fields=[{"name": "test", "type": "str", "description": "Test"}],
            dependencies=["pydantic"],
            responsibilities=["Test validation"]
        )
        assert result is not None
        assert hasattr(result, 'content')
        assert len(result.content) > 0

    def test_ioerror_becomes_config_error(self, scaffolder, mock_registry):
        # Test with non-existent template
        # Template introspection now raises Jinja2 TemplateNotFound during validation
        from jinja2.exceptions import TemplateNotFound
        artifact = Mock()
        artifact.type_id = 'test'
        artifact.required_fields = ['name']
        artifact.template_path = 'nonexistent/template.jinja2'
        artifact.fallback_template = None
        mock_registry.get_artifact.return_value = artifact

        # TemplateNotFound raised during introspection
        with pytest.raises(TemplateNotFound):
            scaffolder.scaffold('test', name='Test')
