"""Unit tests for TemplateScaffolder (Cycle 4)."""

from unittest.mock import MagicMock
import pytest

from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolders.scaffold_result import ScaffoldResult
from mcp_server.config.artifact_registry_config import (
    ArtifactRegistryConfig,
    ConfigError,
)
from mcp_server.core.errors import ValidationError


@pytest.fixture
def mock_registry() -> MagicMock:
    """Mock artifact registry."""
    registry = MagicMock(spec=ArtifactRegistryConfig)
    dto_artifact = MagicMock()
    dto_artifact.required_fields = ["name", "description"]
    dto_artifact.template_path = "dto.py.jinja2"
    dto_artifact.fallback_template = None
    dto_artifact.name_suffix = None
    dto_artifact.file_extension = ".py"
    registry.get_artifact.return_value = dto_artifact
    return registry


@pytest.fixture
def scaffolder(mock_registry: MagicMock) -> TemplateScaffolder:
    """TemplateScaffolder with mock registry."""
    return TemplateScaffolder(registry=mock_registry)


class TestInheritance:
    """Test BaseScaffolder extension."""

    def test_extends_base_scaffolder(
        self, scaffolder: TemplateScaffolder
    ) -> None:
        """Extends BaseScaffolder."""
        from mcp_server.scaffolders.base_scaffolder import BaseScaffolder

        assert isinstance(scaffolder, BaseScaffolder)


class TestValidation:
    """Test validation."""

    def test_validate_checks_required_fields(
        self, scaffolder: TemplateScaffolder
    ) -> None:
        """Checks required fields."""
        with pytest.raises(ValidationError):
            scaffolder.validate("dto", name="UserDTO")

    def test_validate_passes_with_all_fields(
        self, scaffolder: TemplateScaffolder
    ) -> None:
        """Passes with all required fields."""
        result = scaffolder.validate(
            "dto", name="UserDTO", description="User data"
        )
        assert result is True


class TestScaffolding:
    """Test scaffold() method."""

    def test_scaffold_returns_result(
        self, scaffolder: TemplateScaffolder
    ) -> None:
        """Returns ScaffoldResult."""
        scaffolder._render_template = MagicMock(return_value="content")

        result = scaffolder.scaffold(
            "dto", name="UserDTO", description="User data"
        )

        assert isinstance(result, ScaffoldResult)

    def test_scaffold_constructs_filename(
        self, scaffolder: TemplateScaffolder
    ) -> None:
        """Constructs filename."""
        scaffolder._render_template = MagicMock(return_value="content")

        result = scaffolder.scaffold(
            "dto", name="UserDTO", description="User data"
        )

        assert result.file_name == "UserDTO.py"
