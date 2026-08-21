"""Unit tests for ArtifactManager.

@layer: Tests (Unit)
@dependencies: pytest, tests.mcp_server.test_support, mcp_server.managers.artifact_manager
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest

import mcp_server.managers.artifact_manager as artifact_manager_module
from mcp_server.config.schemas.artifact_registry_config import (
    ArtifactDefinition,
    ArtifactRegistryConfig,
    SchemaFieldDef,
)
from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.validation.base import ValidationIssue
from tests.mcp_server.test_support import make_artifact_manager


class TestArtifactManagerCore:
    """Test ArtifactManager core functionality."""

    def test_constructor_accepts_optional_registry(self) -> None:
        """Test that constructor accepts optional registry parameter."""
        mock_registry = Mock(spec=ArtifactRegistryConfig)
        manager = ArtifactManager(registry=mock_registry, server_root=Path("."))
        assert manager.registry is mock_registry

    def test_constructor_accepts_optional_scaffolder(self) -> None:
        """Test that constructor accepts optional scaffolder parameter."""
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.registry = Mock(spec=ArtifactRegistryConfig)
        manager = ArtifactManager(scaffolder=mock_scaffolder, server_root=Path("."))
        assert manager.scaffolder is mock_scaffolder

    @pytest.mark.asyncio
    async def test_scaffold_artifact_delegates_to_scaffolder(self) -> None:
        """Test that scaffold_artifact delegates to scaffolder."""
        # Valid Python content for validation
        valid_python_content = (
            '"""Test DTO."""\n\nclass TestDTO:\n    """Test DTO class."""\n    pass\n'
        )

        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.scaffold.return_value = Mock(
            content=valid_python_content, file_name="test.py"
        )

        mock_fs_adapter = Mock()
        # Mock resolve_path to return the absolute path
        mock_fs_adapter.resolve_path.return_value = Path("/test/test.py")

        mock_validation_service = Mock()
        # Make validate return an async coroutine
        mock_validation_service.validate = AsyncMock(return_value=(True, ()))

        # Mock get_artifact_path to avoid complex dependency chain
        mock_artifact = Mock()
        mock_artifact.template_path = "concrete/dto.py.jinja2"
        type(mock_artifact).output_type = PropertyMock(return_value="file")
        mock_artifact.type = "code"
        mock_artifact.file_extension = ".py"
        mock_artifact.name_suffix = "DTO"
        mock_artifact.context_schema = {
            "name": SchemaFieldDef(
                type="string", title="Name", description="DTO Name", required=True
            ),
            "fields": SchemaFieldDef(
                type="array", title="Fields", description="Fields list", required=False
            ),
        }
        mock_registry = Mock(spec=ArtifactRegistryConfig)
        mock_registry.get_artifact.return_value = mock_artifact

        with patch.object(ArtifactManager, "get_artifact_path", return_value=Path("/test/test.py")):
            manager = ArtifactManager(
                scaffolder=mock_scaffolder,
                registry=mock_registry,
                fs_adapter=mock_fs_adapter,
                validation_service=mock_validation_service,
                server_root=Path("."),
            )
            result = await manager.scaffold_artifact(
                "dto",
                output_path="test_scaffold_output.py",
                name="Test",
                dto_name="Test",
                fields=[],
            )

        # Verify scaffolder was called with metadata fields
        call_args = mock_scaffolder.scaffold.call_args
        assert call_args[0] == ("dto",)
        assert call_args[1]["name"] == "Test"
        assert call_args[1]["fields"] == []
        assert "template_id" in call_args[1]
        assert "version_hash" in call_args[1]  # Task 1.1c
        assert "scaffold_created" in call_args[1]
        assert "output_path" in call_args[1]

        # Verify validation was called
        mock_validation_service.validate.assert_called_once()

        # Verify file was written
        mock_fs_adapter.write_file.assert_called_once_with(
            "test_scaffold_output.py",
            valid_python_content,
        )

        # Verify path was returned (normalize for cross-platform)
        assert result == str(Path("/test/test.py"))

    @pytest.mark.asyncio
    async def test_strict_validation_forwards_canonical_issue_tuple(self) -> None:
        """Strict rejection preserves the validation service record tuple."""
        issue = ValidationIssue(message="Invalid syntax", line=3, code="E001")
        issues = (issue,)
        registry = Mock(spec=ArtifactRegistryConfig)
        registry.get_artifact.return_value = Mock(
            strict_validation=True,
            output_type="file",
            type="code",
        )
        validation_service = Mock()
        validation_service.validate = AsyncMock(return_value=(False, issues))
        manager = ArtifactManager(
            registry=registry,
            validation_service=validation_service,
            fs_adapter=Mock(),
            server_root=Path("."),
        )

        with pytest.raises(ValidationError) as exc_info:
            await manager._validate_and_write(  # pyright: ignore[reportPrivateUsage]
                "dto", "test.py", "invalid"
            )

        forwarded = exc_info.value.params["issues"]
        assert forwarded is issues
        assert forwarded[0] is issue

    def test_validate_artifact_delegates_to_scaffolder(self) -> None:
        """Test that validate_artifact delegates to scaffolder."""
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.registry = Mock(spec=ArtifactRegistryConfig)
        mock_scaffolder.validate.return_value = True

        manager = ArtifactManager(scaffolder=mock_scaffolder, server_root=Path("."))
        result = manager.validate_artifact("dto", name="Test")

        assert result is True
        mock_scaffolder.validate.assert_called_once_with("dto", name="Test")

    def test_validation_error_propagates(self) -> None:
        """Test that validation errors propagate correctly."""
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.registry = Mock(spec=ArtifactRegistryConfig)
        mock_scaffolder.validate.side_effect = ValidationError("Missing field")

        manager = ArtifactManager(scaffolder=mock_scaffolder, server_root=Path("."))
        with pytest.raises(ValidationError):
            manager.validate_artifact("dto", name="Test")

    def test_not_singleton(self, tmp_path: Path) -> None:
        """Test that ArtifactManager is NOT a singleton."""
        manager1 = make_artifact_manager(tmp_path)
        manager2 = make_artifact_manager(tmp_path)
        assert manager1 is not manager2


class TestGetContextSchema:
    """Tests for ArtifactManager.get_context_schema() — C1.D7."""

    def _make_manager(self) -> ArtifactManager:
        mock_registry = Mock(spec=ArtifactRegistryConfig)

        def get_mock_artifact(artifact_type: str) -> Mock:
            mock_art = Mock()
            mock_art.template_path = "concrete/dto.py.jinja2"
            type(mock_art).output_type = PropertyMock(return_value="file")
            mock_art.type = "code"
            mock_art.file_extension = ".py"
            mock_art.name_suffix = "DTO"
            mock_art.required_fields = []
            mock_art.optional_fields = []

            if artifact_type == "research":
                mock_art.context_schema = {
                    "title": SchemaFieldDef(
                        type="string", title="Title", description="The title", required=True
                    )
                }
            elif artifact_type == "generic_doc":
                mock_art.context_schema = {
                    "title": SchemaFieldDef(
                        type="string", title="Title", description="The title", required=True
                    ),
                    "purpose": SchemaFieldDef(
                        type="string", title="Purpose", description="The purpose", required=True
                    ),
                    "summary": SchemaFieldDef(
                        type="string", title="Summary", description="The summary", required=True
                    ),
                }
            else:
                mock_art.context_schema = None
            return mock_art

        mock_registry.get_artifact.side_effect = get_mock_artifact
        return ArtifactManager(registry=mock_registry, server_root=Path("."))

    def test_returns_json_schema_dict_for_type(self) -> None:
        """get_context_schema returns JSON Schema dict for a registered artifact type."""
        manager = self._make_manager()
        schema = manager.get_context_schema("research")
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"
        assert "properties" in schema
        assert isinstance(schema["properties"], dict)

    def test_required_fields_present_in_schema(self) -> None:
        """get_context_schema includes 'required' list for type with required fields."""
        manager = self._make_manager()
        schema = manager.get_context_schema("research")
        assert "required" in schema
        assert isinstance(schema["required"], list)
        assert len(schema["required"]) > 0

    def test_returns_json_schema_dict_for_generic_doc(self) -> None:
        """get_context_schema returns JSON Schema dict for generic_doc."""
        manager = self._make_manager()
        schema = manager.get_context_schema("generic_doc")
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"
        schema = manager.get_context_schema("generic_doc")
        assert {"title", "purpose", "summary"}.issubset(schema["properties"])


class TestArtifactManagerDynamicContext:
    """Tests for dynamic context class resolution in ArtifactManager."""

    def test_artifact_definition_has_context_class(self) -> None:
        """Verify context_class field is present on ArtifactDefinition."""
        assert "context_schema" in ArtifactDefinition.model_fields
        assert "context_class" in ArtifactDefinition.model_fields

    def test_v2_context_registry_removed(self) -> None:
        """Verify _v2_context_registry has been removed from artifact_manager.py."""
        assert not hasattr(artifact_manager_module, "_v2_context_registry")

    def test_get_context_schema_raises_config_error_if_no_yaml_schema(self) -> None:
        """Test that get_context_schema raises ConfigError if YAML context_schema is missing."""
        mock_registry = Mock(spec=ArtifactRegistryConfig)
        mock_art = Mock()
        mock_art.context_schema = None
        mock_art.context_class = None
        mock_registry.get_artifact.return_value = mock_art

        manager = ArtifactManager(registry=mock_registry, server_root=Path("."))
        with pytest.raises(ConfigError) as exc_info:
            manager.get_context_schema("dummy")
        assert "No Context schema defined for" in str(exc_info.value)
