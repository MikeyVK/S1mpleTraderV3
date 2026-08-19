"""Unit tests for ScaffoldArtifactTool (Cycle 11).

@layer: Tests (Unit)
@dependencies: [pytest, unittest.mock, mcp_server.tools.scaffold_artifact]
"""

from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.core.operation_notes import NoteContext
from mcp_server.schemas.tool_outputs import ScaffoldArtifactOutput
from mcp_server.tools.scaffold_artifact import (
    ScaffoldArtifactInput,
    ScaffoldArtifactTool,
)
from tests.mcp_server.test_support import get_default_server_root


class TestScaffoldArtifactTool:
    """Test ScaffoldArtifactTool."""

    @pytest.fixture
    def mock_manager(self) -> MagicMock:
        """Mock ArtifactManager."""
        manager = MagicMock()
        # scaffold_artifact is async, so use AsyncMock
        manager.scaffold_artifact = AsyncMock(return_value="mcp_server/dtos/UserDTO.py")
        manager.get_artifact_path = MagicMock(return_value="mcp_server/dtos/UserDTO.py")
        return manager

    @pytest.fixture
    def tool(self, mock_manager: MagicMock) -> ScaffoldArtifactTool:
        """Create tool with mocked manager."""
        return ScaffoldArtifactTool(manager=mock_manager)

    def test_tool_has_correct_metadata(self, tool: ScaffoldArtifactTool) -> None:
        """Tool should have proper name and description."""
        assert tool.name == "scaffold_artifact"
        assert "Scaffold" in tool.description
        assert "unified" in tool.description.lower()

    def test_input_schema_has_required_fields(self) -> None:
        """Input schema should require artifact_type and name."""
        # Pydantic model validation
        with pytest.raises(Exception):  # noqa: B017 — Missing required fields; pydantic.ValidationError
            ScaffoldArtifactInput()  # type: ignore[call-arg]

        # Valid input
        input_data = ScaffoldArtifactInput(artifact_type="dto", name="User")
        assert input_data.artifact_type == "dto"
        assert input_data.name == "User"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_scaffolds_code_artifact(
        self, tool: ScaffoldArtifactTool, mock_manager: MagicMock
    ) -> None:
        """Should scaffold code artifact (DTO)."""
        input_data = ScaffoldArtifactInput(
            artifact_type="dto", name="User", context={"fields": [{"name": "id", "type": "int"}]}
        )

        result = await tool.execute(input_data, NoteContext())

        # Verify manager called
        mock_manager.scaffold_artifact.assert_called_once_with(
            "dto", note_context=mock.ANY, name="User", fields=[{"name": "id", "type": "int"}]
        )

        # Verify result
        assert isinstance(result, ScaffoldArtifactOutput)
        assert result.success is True
        assert result.artifact_type == "dto"
        assert result.files_created == ["mcp_server/dtos/UserDTO.py"]

    @pytest.mark.asyncio
    async def test_scaffolds_document_artifact(
        self, tool: ScaffoldArtifactTool, mock_manager: MagicMock
    ) -> None:
        """Should scaffold document artifact (design)."""
        # Update the async mock's return value
        mock_manager.scaffold_artifact.return_value = "docs/development/design.md"

        input_data = ScaffoldArtifactInput(
            artifact_type="design",
            name="system-architecture",
            context={"title": "System Architecture", "author": "GitHub Copilot", "status": "DRAFT"},
        )

        result = await tool.execute(input_data, NoteContext())

        # Verify manager called
        mock_manager.scaffold_artifact.assert_called_once_with(
            "design",
            note_context=mock.ANY,
            name="system-architecture",
            title="System Architecture",
            author="GitHub Copilot",
            status="DRAFT",
        )

        # Verify result
        assert isinstance(result, ScaffoldArtifactOutput)
        assert result.success is True
        assert result.artifact_type == "design"
        assert result.files_created == ["docs/development/design.md"]

    def test_manager_requires_explicit_di(self) -> None:
        """Should require explicit manager dependency injection."""
        custom_manager = MagicMock()
        tool = ScaffoldArtifactTool(manager=custom_manager)
        assert tool.manager is custom_manager

        with pytest.raises(ValueError, match="ArtifactManager must be injected"):
            ScaffoldArtifactTool()

    @pytest.mark.asyncio
    async def test_validation_error_returns_error_result(
        self, tool: ScaffoldArtifactTool, mock_manager: MagicMock
    ) -> None:
        """Should return error result on validation failure."""
        mock_manager.scaffold_artifact.side_effect = ValidationError(
            "Invalid artifact type: unknown",
        )

        input_data = ScaffoldArtifactInput(artifact_type="unknown", name="Test")

        result = await tool.execute(input_data, NoteContext())

        assert isinstance(result, ScaffoldArtifactOutput)
        assert result.success is False
        assert result.error_message is not None
        assert "Invalid artifact type" in result.error_message

    @pytest.mark.asyncio
    async def test_config_error_returns_error_result(
        self, tool: ScaffoldArtifactTool, mock_manager: MagicMock
    ) -> None:
        """Should return error result on config error."""
        mock_manager.scaffold_artifact.side_effect = ConfigError(
            "No valid directory found for artifact type: dto",
            file_path=f"{get_default_server_root()}/config/project_structure.yaml",
        )

        input_data = ScaffoldArtifactInput(artifact_type="dto", name="User")

        result = await tool.execute(input_data, NoteContext())

        assert isinstance(result, ScaffoldArtifactOutput)
        assert result.success is False
        assert result.error_message is not None
        assert "No valid directory" in result.error_message

    @pytest.mark.asyncio
    async def test_context_dict_unpacked_to_kwargs(
        self, tool: ScaffoldArtifactTool, mock_manager: MagicMock
    ) -> None:
        """Should unpack context dict to kwargs."""
        input_data = ScaffoldArtifactInput(
            artifact_type="dto",
            name="User",
            context={
                "fields": [{"name": "id", "type": "int"}],
                "docstring": "User data transfer object",
                "generate_test": True,
            },
        )

        await tool.execute(input_data, NoteContext())

        # Verify all context items passed as kwargs
        mock_manager.scaffold_artifact.assert_called_once_with(
            "dto",
            note_context=mock.ANY,
            name="User",
            fields=[{"name": "id", "type": "int"}],
            docstring="User data transfer object",
            generate_test=True,
        )

    @pytest.mark.asyncio
    async def test_empty_context_dict_allowed(
        self, tool: ScaffoldArtifactTool, mock_manager: MagicMock
    ) -> None:
        """Should allow empty context dict."""
        input_data = ScaffoldArtifactInput(artifact_type="dto", name="Simple")

        result = await tool.execute(input_data, NoteContext())

        assert isinstance(result, ScaffoldArtifactOutput)
        assert result.success is True
        mock_manager.scaffold_artifact.assert_called_once()
