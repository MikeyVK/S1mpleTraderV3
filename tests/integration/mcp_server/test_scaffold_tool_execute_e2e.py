"""
@module: tests.integration.mcp_server.test_scaffold_tool_execute_e2e
@layer: Test Infrastructure
@dependencies: pytest, mcp_server.tools.scaffold_artifact
@responsibilities:
  - E2E test for ScaffoldArtifactTool.execute() (not manager)
  - Happy path validation via tool layer
  - Verify tool contract and file creation
"""

# Standard library
from pathlib import Path

# Third-party
import pytest

from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.tools.scaffold_artifact import ScaffoldArtifactTool, ScaffoldArtifactInput


@pytest.mark.asyncio
async def test_tool_execute_scaffolds_design_doc(
    temp_workspace: Path,
    artifact_manager: ArtifactManager
) -> None:
    """
    E2E test: ScaffoldArtifactTool.execute() scaffolds design doc to disk.

    This is the MANDATORY happy-path E2E via tool.execute() (not manager).
    Validates Slice 4 requirement: tool execution with real config.
    """
    # Arrange
    tool = ScaffoldArtifactTool(manager=artifact_manager)
    output_path = "docs/design/test_design.md"
    params = ScaffoldArtifactInput(
        artifact_type="design",
        name="test-design",
        output_path=output_path,
        context={
            "issue_number": "42",
            "title": "Test Design via Tool",
            "author": "E2E Test",
        }
    )

    # Act
    result = await tool.execute(params)

    # Assert
    assert result is not None
    assert hasattr(result, "content")
    assert len(result.content) > 0
    # ToolResult.text creates {"type": "text", "text": "..."}
    content_item = result.content[0]
    assert isinstance(content_item, dict)
    content_text = content_item.get("text", "")
    assert isinstance(content_text, str)
    assert len(content_text) > 0
    assert "test-design" in content_text or "test_design.md" in content_text

    # Verify file on disk
    output_file = temp_workspace / output_path
    assert output_file.exists(), f"Expected file at {output_file}"
    assert output_file.is_file()

    file_content = output_file.read_text(encoding="utf-8")
    assert len(file_content) > 0
    assert "Test Design via Tool" in file_content
    assert "Issue: #42" in file_content
    assert "E2E Test" in file_content


@pytest.mark.asyncio
async def test_tool_execute_scaffolds_dto(
    temp_workspace: Path,
    artifact_manager: ArtifactManager
) -> None:
    """
    E2E test: ScaffoldArtifactTool.execute() scaffolds DTO code to disk.

    Validates happy-path code artifact via tool layer.
    """
    # Arrange
    tool = ScaffoldArtifactTool(manager=artifact_manager)
    output_path = "mcp_server/dtos/test_dto.py"
    params = ScaffoldArtifactInput(
        artifact_type="dto",
        name="TestDTO",
        output_path=output_path,
        context={
            "description": "Test DTO via tool execute",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "str"},
            ]
        }
    )

    # Act
    result = await tool.execute(params)

    # Assert
    assert result is not None
    assert hasattr(result, "content")
    assert len(result.content) > 0
    content_item = result.content[0]
    assert isinstance(content_item, dict)
    content_text = content_item.get("text", "")
    assert isinstance(content_text, str)
    assert "TestDTO" in content_text or "test_dto.py" in content_text

    # Verify file on disk
    output_file = temp_workspace / output_path
    assert output_file.exists()
    assert output_file.is_file()

    file_content = output_file.read_text(encoding="utf-8")
    assert "class TestDTO" in file_content
    assert "BaseModel" in file_content
    assert "Test DTO via tool execute" in file_content
    assert "id" in file_content
    assert "name" in file_content
