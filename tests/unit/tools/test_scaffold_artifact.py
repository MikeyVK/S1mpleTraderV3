"""Unit tests for ScaffoldArtifactTool (Cycle 11)."""

import pytest
from unittest.mock import MagicMock

from mcp_server.tools.scaffold_artifact import ScaffoldArtifactTool, ScaffoldArtifactInput
from mcp_server.core.errors import ValidationError, ConfigError


class TestScaffoldArtifactTool:
    """Test ScaffoldArtifactTool."""

    @pytest.fixture
    def mock_manager(self):
        """Mock ArtifactManager."""
        manager = MagicMock()
        manager.scaffold_artifact.return_value = "mcp_server/dtos/UserDTO.py"
        manager.get_artifact_path.return_value = "mcp_server/dtos/UserDTO.py"
        return manager

    @pytest.fixture
    def tool(self, mock_manager):
        """Create tool with mocked manager."""
        return ScaffoldArtifactTool(manager=mock_manager)

    def test_tool_has_correct_metadata(self, tool):
        """Tool should have proper name and description."""
        assert tool.name == "scaffold_artifact"
        assert "Scaffold" in tool.description
        assert "unified" in tool.description.lower()

    def test_input_schema_has_required_fields(self):
        """Input schema should require artifact_type and name."""
        # Pydantic model validation
        with pytest.raises(Exception):  # Missing required fields
            ScaffoldArtifactInput()

        # Valid input
        input_data = ScaffoldArtifactInput(
            artifact_type="dto",
            name="User"
        )
        assert input_data.artifact_type == "dto"
        assert input_data.name == "User"

    @pytest.mark.asyncio
    async def test_scaffolds_code_artifact(self, tool, mock_manager):
        """Should scaffold code artifact (DTO)."""
        input_data = ScaffoldArtifactInput(
            artifact_type="dto",
            name="User",
            context={"fields": [{"name": "id", "type": "int"}]}
        )

        result = await tool.execute(input_data)

        # Verify manager called
        mock_manager.scaffold_artifact.assert_called_once_with(
            "dto",
            name="User",
            fields=[{"name": "id", "type": "int"}]
        )

        # Verify result
        assert not result.is_error
        assert "UserDTO.py" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_scaffolds_document_artifact(self, tool, mock_manager):
        """Should scaffold document artifact (design)."""
        mock_manager.scaffold_artifact.return_value = "docs/development/design.md"

        input_data = ScaffoldArtifactInput(
            artifact_type="design",
            name="system-architecture",
            context={
                "title": "System Architecture",
                "author": "GitHub Copilot",
                "status": "DRAFT"
            }
        )

        result = await tool.execute(input_data)

        # Verify manager called
        mock_manager.scaffold_artifact.assert_called_once_with(
            "design",
            name="system-architecture",
            title="System Architecture",
            author="GitHub Copilot",
            status="DRAFT"
        )

        # Verify result
        assert not result.is_error
        assert "design.md" in result.content[0]["text"]

    def test_manager_optional_di(self):
        """Should allow manager dependency injection."""
        # With custom manager
        custom_manager = MagicMock()
        tool = ScaffoldArtifactTool(manager=custom_manager)
        assert tool.manager is custom_manager

        # Without manager (creates default)
        tool_default = ScaffoldArtifactTool()
        assert tool_default.manager is not None

    @pytest.mark.asyncio
    async def test_validation_error_returns_error_result(self, tool, mock_manager):
        """Should return error result on validation failure."""
        mock_manager.scaffold_artifact.side_effect = ValidationError(
            "Invalid artifact type: unknown",
            hints=["Available types: dto, worker, design"]
        )

        input_data = ScaffoldArtifactInput(
            artifact_type="unknown",
            name="Test"
        )

        result = await tool.execute(input_data)

        assert result.is_error
        text = result.content[0]["text"]
        assert "Invalid artifact type" in text
        assert "Available types" in text

    @pytest.mark.asyncio
    async def test_config_error_returns_error_result(self, tool, mock_manager):
        """Should return error result on config error."""
        mock_manager.scaffold_artifact.side_effect = ConfigError(
            "No valid directory found for artifact type: dto",
            file_path=".st3/project_structure.yaml"
        )

        input_data = ScaffoldArtifactInput(
            artifact_type="dto",
            name="User"
        )

        result = await tool.execute(input_data)

        assert result.is_error
        text = result.content[0]["text"]
        assert "No valid directory" in text
        assert "project_structure.yaml" in text

    @pytest.mark.asyncio
    async def test_context_dict_unpacked_to_kwargs(self, tool, mock_manager):
        """Should unpack context dict to kwargs."""
        input_data = ScaffoldArtifactInput(
            artifact_type="dto",
            name="User",
            context={
                "fields": [{"name": "id", "type": "int"}],
                "docstring": "User data transfer object",
                "generate_test": True
            }
        )

        await tool.execute(input_data)

        # Verify all context items passed as kwargs
        mock_manager.scaffold_artifact.assert_called_once_with(
            "dto",
            name="User",
            fields=[{"name": "id", "type": "int"}],
            docstring="User data transfer object",
            generate_test=True
        )

    @pytest.mark.asyncio
    async def test_empty_context_dict_allowed(self, tool, mock_manager):
        """Should allow empty context dict."""
        input_data = ScaffoldArtifactInput(
            artifact_type="dto",
            name="Simple"
        )

        result = await tool.execute(input_data)

        assert not result.is_error
        mock_manager.scaffold_artifact.assert_called_once()
