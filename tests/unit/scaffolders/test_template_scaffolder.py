"""Tests for TemplateScaffolder (Cycle 4).

Basic scaffolder functionality without filesystem operations.
Filesystem integration tested separately in test_filesystem_integration.py.
"""

import pytest
from unittest.mock import Mock, patch

from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolders.base_scaffolder import BaseScaffolder
from mcp_server.scaffolders.scaffold_result import ScaffoldResult
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.exceptions import ValidationError


@pytest.fixture
def mock_registry():
    """Mock registry with test artifact definitions."""
    registry = Mock(spec=ArtifactRegistryConfig)
    
    # Mock DTO artifact
    dto_artifact = Mock()
    dto_artifact.type_id = "dto"
    dto_artifact.required_fields = ["name", "fields"]
    dto_artifact.template_path = "dto.py.jinja2"
    dto_artifact.fallback_template = None
    dto_artifact.name_suffix = "DTO"
    dto_artifact.file_extension = ".py"
    
    registry.get_artifact.return_value = dto_artifact
    return registry


@pytest.fixture
def scaffolder(mock_registry):
    """TemplateScaffolder instance with mocked registry."""
    return TemplateScaffolder(registry=mock_registry)


class TestInheritance:
    """Test that TemplateScaffolder follows architecture."""
    
    def test_extends_base_scaffolder(self):
        """TemplateScaffolder must extend BaseScaffolder."""
        assert issubclass(TemplateScaffolder, BaseScaffolder)


class TestValidation:
    """Test validation logic."""
    
    def test_validate_checks_required_fields(self, scaffolder):
        """Missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            scaffolder.validate("dto", name="Test")  # Missing 'fields'
        
        assert "fields" in str(exc_info.value)
    
    def test_validate_passes_with_all_fields(self, scaffolder):
        """All required fields present returns True."""
        result = scaffolder.validate("dto", name="Test", fields=[])
        assert result is True


class TestScaffolding:
    """Test scaffolding operations with mocked filesystem."""
    
    def test_scaffold_returns_result(self, scaffolder):
        """scaffold() returns ScaffoldResult instance."""
        # Mock filesystem read (Cycle 5 integration)
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "content"
            
            result = scaffolder.scaffold(
                "dto",
                name="User",
                fields=[{"name": "id", "type": "int"}]
            )
            
            assert isinstance(result, ScaffoldResult)
            assert result.content == "content"
    
    def test_scaffold_constructs_filename(self, scaffolder):
        """scaffold() constructs correct filename from artifact definition."""
        # Mock filesystem read
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "content"
            
            result = scaffolder.scaffold(
                "dto",
                name="User",
                fields=[]
            )
            
            # DTO has name_suffix="DTO" and file_extension=".py"
            assert result.file_name == "UserDTO.py"
