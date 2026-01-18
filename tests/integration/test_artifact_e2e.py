"""
@module: tests.integration.test_artifact_e2e
@layer: Test Infrastructure
@dependencies: tests.fixtures.artifact_test_harness
@responsibilities:
  - E2E smoke test for unified artifact system
  - Happy path validation (scaffold -> disk)
  - Slice 0 acceptance test
"""

# Standard library
from pathlib import Path

# Project
from mcp_server.managers.artifact_manager import ArtifactManager


def test_artifact_scaffolding_smoke(
    artifact_manager: ArtifactManager, temp_workspace: Path
) -> None:
    """
    Smoke test: scaffold design doc to temp workspace.

    Validates basic E2E flow works:
    - ArtifactManager orchestration
    - Template rendering (Jinja2)
    - FilesystemAdapter writes to disk
    - File exists at expected location
    """
    # Arrange
    artifact_type = "design"
    output_path = "docs/design/test_design.md"

    # Act
    result = artifact_manager.scaffold_artifact(
        artifact_type=artifact_type,
        output_path=output_path,
        issue_number="123",
        title="Test Design Document",
        author="Test Author",
    )

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0

    # Verify file on disk
    output_file = temp_workspace / output_path
    assert output_file.exists()
    assert output_file.is_file()

    content = output_file.read_text(encoding="utf-8")
    assert len(content) > 0
    assert "Test Design Document" in content
    assert "Issue: #123" in content  # Hermetic template format
    assert "Test Author" in content


def test_artifact_scaffolding_code_to_disk(
    artifact_manager: ArtifactManager, temp_workspace: Path
) -> None:
    """
    E2E test: scaffold code artifact (DTO) to disk.

    Validates Slice 2 requirement: scaffold code artifact via
    JinjaRenderer to filesystem.

    Tests:
    - DTO template rendering
    - Code artifact file creation
    - Python file structure validation
    """
    # Arrange
    artifact_type = "dto"
    output_path = "mcp_server/dtos/user_dto.py"

    # Act
    result = artifact_manager.scaffold_artifact(
        artifact_type=artifact_type,
        output_path=output_path,
        name="UserDTO",
        description="User data transfer object",
        fields=[
            {"name": "id", "type": "int"},
            {"name": "username", "type": "str"},
            {"name": "email", "type": "str"},
        ]
    )

    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0

    # Verify file on disk
    output_file = temp_workspace / output_path
    assert output_file.exists()
    assert output_file.is_file()

    # Verify Python content structure
    content = output_file.read_text(encoding="utf-8")
    assert len(content) > 0
    assert "class UserDTO" in content
    assert "BaseModel" in content
    assert "User data transfer object" in content
    assert "id" in content
    assert "username" in content
    assert "email" in content
