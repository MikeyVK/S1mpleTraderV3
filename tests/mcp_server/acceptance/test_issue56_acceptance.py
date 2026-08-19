"""
@module: tests.acceptance.test_issue56_acceptance
@layer: Test Infrastructure
@dependencies: pytest, mcp_server tools, managers
@responsibilities:
  - Issue #56 acceptance criteria validation
  - Repeatable smoke tests for scaffold workflows
  - Verify unified artifact system end-to-end
"""

from pathlib import Path

import pytest

from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.tools.scaffold_artifact import ScaffoldArtifactInput, ScaffoldArtifactTool


@pytest.mark.asyncio
async def test_scaffold_design_doc_with_required_context(
    temp_workspace: Path,
    artifact_manager: ArtifactManager,
) -> None:
    """
    Acceptance: scaffold_artifact design requires context (issue_number/title/author).

    Validates Issue #56 Slice 7 requirement: design artifacts scaffold successfully
    with all required context fields.
    """
    # Arrange
    tool = ScaffoldArtifactTool(manager=artifact_manager)
    params = ScaffoldArtifactInput(
        artifact_type="design",
        name="issue56-acceptance-test",
        output_path="docs/design/issue56_acceptance.md",
        context={
            "issue_number": "56",
            "title": "Unified Artifact System Acceptance",
            "author": "Acceptance Test Suite",
            "status": "DRAFT",
            "version": "1.0",
            "last_updated": "2026-01-20",
            "problem_statement": "Define test architecture",
            "requirements_functional": ["Req 1"],
            "requirements_nonfunctional": ["Req 2"],
            "decision": "Use layered arch",
            "rationale": "Simple",
            "options": [{"name": "Layered", "description": "Layered arch"}],
            "key_decisions": [{"area": "Architecture", "decision": "MVC"}],
        },
    )

    # Act
    result = await tool.execute(params, NoteContext())

    # Assert
    assert result.success
    content_text = result.formatted_files_created
    assert "issue56_acceptance.md" in content_text or "issue56-acceptance-test" in content_text
    # Verify file created on disk
    output_file = temp_workspace / "docs/design/issue56_acceptance.md"
    assert output_file.exists(), f"Expected design doc at {output_file}"
    assert output_file.is_file()

    file_content = output_file.read_text(encoding="utf-8")
    assert "Issue: #56" in file_content
    assert "Unified Artifact System Acceptance" in file_content
    assert "Acceptance Test Suite" in file_content


@pytest.mark.asyncio
async def test_scaffold_dto_with_description(
    temp_workspace: Path,
    artifact_manager: ArtifactManager,
) -> None:
    """
    Acceptance: scaffold_artifact dto requires description.

    Validates Issue #56 Slice 7 requirement: code artifacts (dto) scaffold successfully
    with required description field.
    """
    # Arrange
    tool = ScaffoldArtifactTool(manager=artifact_manager)
    params = ScaffoldArtifactInput(
        artifact_type="dto",
        name="AcceptanceTestDto",
        output_path="backend/dtos/acceptance_test_dto.py",
        context={
            "name": "AcceptanceTestDto",
            "description": "Acceptance test DTO for Issue #56 validation",
            "fields": [
                {"name": "test_id", "type": "str"},
                {"name": "status", "type": "str"},
            ],
        },
    )

    # Act
    result = await tool.execute(params, NoteContext())

    # Assert
    assert result.success
    content_text = result.formatted_files_created
    assert "AcceptanceTestDto" in content_text or "acceptance_test_dto.py" in content_text
    # Verify file created on disk
    output_file = temp_workspace / "backend/dtos/acceptance_test_dto.py"
    assert output_file.exists(), f"Expected DTO at {output_file}"
    assert output_file.is_file()

    file_content = output_file.read_text(encoding="utf-8")
    assert "AcceptanceTestDto" in file_content
    assert "Acceptance test DTO for Issue #56 validation" in file_content
    assert "test_id" in file_content
    assert "status" in file_content
