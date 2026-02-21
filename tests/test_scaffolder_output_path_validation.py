# tests\test_scaffolder_output_path_validation.py
# template=unit_test version=3d15d309 created=2026-02-21T15:35Z updated=
"""
Unit tests for mcp_server.scaffolders.template_scaffolder.

Tests for template_scaffolder.validate() file artifact gate (Issue #239 C2).

RED phase: file artifact + empty/None output_path → ValidationError with hint.
           ephemeral artifact + output_path=None → no error.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.scaffolders.template_scaffolder, unittest.mock]
@responsibilities:
    - Test TestScaffolderOutputPathValidation functionality
    - Verify output_path validation gate in validate() for file vs ephemeral artifacts
    - Confirm ephemeral artifacts are unaffected by the gate
"""

# Standard library
from unittest.mock import MagicMock, patch

# Third-party
import pytest

# Project modules
from mcp_server.core.exceptions import ValidationError
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder

_INTROSPECT = "mcp_server.scaffolders.template_scaffolder.introspect_template_with_inheritance"


@pytest.fixture
def mock_schema() -> MagicMock:
    """Schema with no required fields — isolates output_path gate from field-presence gate."""
    schema = MagicMock()
    schema.required = []
    schema.optional = []
    return schema


@pytest.fixture
def file_scaffolder(mock_schema: MagicMock) -> TemplateScaffolder:
    """TemplateScaffolder backed by a mocked file artifact (output_type='file')."""
    artifact = MagicMock()
    artifact.output_type = "file"
    artifact.template_path = "concrete/dto.py.jinja2"
    artifact.fallback_template = None

    registry = MagicMock()
    registry.get_artifact.return_value = artifact

    renderer = MagicMock()
    renderer.env.loader.searchpath = ["/fake/templates"]

    with patch(_INTROSPECT, return_value=mock_schema):
        scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)
        scaffolder._mock_schema = mock_schema  # keep reference for re-patching in tests
        scaffolder._mock_registry = registry
        scaffolder._mock_renderer = renderer
    return scaffolder


@pytest.fixture
def ephemeral_scaffolder(mock_schema: MagicMock) -> TemplateScaffolder:
    """TemplateScaffolder backed by a mocked ephemeral artifact (output_type='ephemeral')."""
    artifact = MagicMock()
    artifact.output_type = "ephemeral"
    artifact.template_path = "concrete/commit.txt.jinja2"
    artifact.fallback_template = None

    registry = MagicMock()
    registry.get_artifact.return_value = artifact

    renderer = MagicMock()
    renderer.env.loader.searchpath = ["/fake/templates"]

    with patch(_INTROSPECT, return_value=mock_schema):
        scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)
        scaffolder._mock_schema = mock_schema
        scaffolder._mock_registry = registry
        scaffolder._mock_renderer = renderer
    return scaffolder


class TestScaffolderOutputPathValidation:
    """Test suite for validate() output_path gate (Issue #239 C2)."""

    def test_file_artifact_empty_output_path_raises(
        self, file_scaffolder: TemplateScaffolder, mock_schema: MagicMock
    ) -> None:
        """validate() with file artifact + output_path='' raises ValidationError."""
        # Arrange
        # Act / Assert
        with patch(_INTROSPECT, return_value=mock_schema):
            with pytest.raises(ValidationError):
                file_scaffolder.validate("dto", name="MyDto", output_path="")

    def test_file_artifact_none_output_path_raises(
        self, file_scaffolder: TemplateScaffolder, mock_schema: MagicMock
    ) -> None:
        """validate() with file artifact + output_path=None raises ValidationError."""
        # Arrange
        # Act / Assert
        with patch(_INTROSPECT, return_value=mock_schema):
            with pytest.raises(ValidationError):
                file_scaffolder.validate("dto", name="MyDto", output_path=None)

    def test_file_artifact_error_hint_message(
        self, file_scaffolder: TemplateScaffolder, mock_schema: MagicMock
    ) -> None:
        """ValidationError hints contain 'output_path is required for file artifacts'."""
        # Arrange
        # Act
        with patch(_INTROSPECT, return_value=mock_schema):
            with pytest.raises(ValidationError) as exc_info:
                file_scaffolder.validate("dto", name="MyDto", output_path="")

        # Assert
        hints = exc_info.value.hints or []
        assert any("output_path is required for file artifacts" in h for h in hints), (
            f"Expected hint about output_path, got: {hints}"
        )

    def test_file_artifact_valid_output_path_passes(
        self, file_scaffolder: TemplateScaffolder, mock_schema: MagicMock
    ) -> None:
        """validate() with file artifact + valid output_path passes without error."""
        # Arrange
        # Act / Assert — no exception expected
        with patch(_INTROSPECT, return_value=mock_schema):
            result = file_scaffolder.validate("dto", name="MyDto", output_path="src/dtos/my_dto.py")

        assert result is True

    def test_ephemeral_artifact_none_output_path_passes(
        self, ephemeral_scaffolder: TemplateScaffolder, mock_schema: MagicMock
    ) -> None:
        """validate() with ephemeral artifact + output_path=None raises no error."""
        # Arrange
        # Act / Assert — no exception expected
        with patch(_INTROSPECT, return_value=mock_schema):
            result = ephemeral_scaffolder.validate("commit", name="my-commit", output_path=None)

        assert result is True
