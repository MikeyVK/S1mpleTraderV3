"""Tests for TemplateScaffolder registry integration.

Verifies that TemplateScaffolder correctly loads and uses
artifact definitions from the registry configuration.
"""
from unittest.mock import Mock

import pytest

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder


@pytest.fixture
def mock_registry():
    """Provide mock artifact registry for testing."""
    return Mock(spec=ArtifactRegistryConfig)


@pytest.fixture
def scaffolder(mock_registry):
    """Provide TemplateScaffolder with mock registry."""
    return TemplateScaffolder(registry=mock_registry)


class TestTemplateRegistryLoading:
    """Tests for artifact registry integration."""

    def test_loads_artifact_from_registry(self, scaffolder, mock_registry):
        """Should load artifact definition from registry."""
        artifact = Mock()
        artifact.type_id = 'dto'
        artifact.required_fields = ['name', 'description']
        artifact.template_path = 'concrete/dto.py.jinja2'
        artifact.fallback_template = None
        artifact.name_suffix = ''
        artifact.file_extension = '.py'
        mock_registry.get_artifact.return_value = artifact

        # TemplateScaffolder now uses JinjaRenderer and returns ScaffoldResult
        result = scaffolder.scaffold(
            'dto',
            name='TestDto',
            description='Test DTO',
            frozen=True,
            examples=[{"test": "data"}],
            fields=[{"name": "test", "type": "str", "description": "Test"}],
            dependencies=["pydantic"],
            responsibilities=["Validation"]
        )

        assert result is not None
        assert hasattr(result, 'content')
        assert len(result.content) > 0
        # Called in validate() and scaffold()
        assert mock_registry.get_artifact.call_count == 2

    def test_uses_template_path_from_artifact(self, scaffolder, mock_registry):
        """Should use template_path from artifact definition."""
        artifact = Mock()
        artifact.type_id = 'worker'
        artifact.required_fields = ['name', 'description']
        artifact.template_path = 'concrete/worker.py.jinja2'
        artifact.fallback_template = None
        artifact.name_suffix = ''
        artifact.file_extension = '.py'
        mock_registry.get_artifact.return_value = artifact

        # Worker template needs all required fields from template introspection
        result = scaffolder.scaffold(
            'worker',
            name='TestWorker',
            description='Test worker',
            input_dto='TestInput',
            output_dto='TestOutput',
            dependencies=["SomeService"],
            responsibilities=["Process data"]
        )
        assert result is not None
        assert hasattr(result, 'content')
        assert 'TestWorker' in result.content

    def test_error_when_no_template_defined(self, scaffolder, mock_registry):
        """Should raise error when artifact has no template defined."""
        artifact = Mock()
        artifact.type_id = 'broken'
        artifact.required_fields = []
        artifact.template_path = None
        artifact.fallback_template = None
        mock_registry.get_artifact.return_value = artifact

        # ValidationError is raised, not ConfigError
        with pytest.raises((ConfigError, ValidationError)) as exc:
            scaffolder.scaffold('broken', name='Test')
        assert 'No template' in str(exc.value)
