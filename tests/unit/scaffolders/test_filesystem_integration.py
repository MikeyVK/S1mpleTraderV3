"""Tests for TemplateScaffolder filesystem integration.

Verifies that TemplateScaffolder correctly loads templates
from the filesystem via JinjaRenderer.

@layer: Tests (Unit)
@dependencies: [pytest, mock, mcp_server.scaffolders]
@responsibilities: [Filesystem integration validation]
"""
from unittest.mock import Mock

from jinja2.exceptions import TemplateNotFound
import pytest

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder


@pytest.fixture(name="registry")
def mock_registry_fixture():
    """Provide mock registry with test artifact configuration."""
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


@pytest.fixture(name="scaffolder_fixture")
def scaffolder_with_registry(registry):
    """Provide TemplateScaffolder with mock registry."""
    return TemplateScaffolder(registry=registry)


class TestTemplateReading:
    """Test template loading from filesystem."""

    def test_template_loads_via_open(self, scaffolder_fixture):
        """Template should load via JinjaRenderer and return ScaffoldResult."""
        # scaffold() returns ScaffoldResult, not str
        result = scaffolder_fixture.scaffold(
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

    def test_ioerror_becomes_config_error(self, scaffolder_fixture, registry):
        """Non-existent template should raise TemplateNotFound during introspection."""
        # Test with non-existent template
        artifact = Mock()
        artifact.type_id = 'test'
        artifact.required_fields = ['name']
        artifact.template_path = 'nonexistent/template.jinja2'
        artifact.fallback_template = None
        registry.get_artifact.return_value = artifact

        # TemplateNotFound raised during introspection
        with pytest.raises(TemplateNotFound):
            scaffolder_fixture.scaffold('test', name='Test')
