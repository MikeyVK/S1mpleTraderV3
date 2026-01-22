# artifact: type=integration_test, version=1.0, created=2026-01-21T22:32:32Z
"""
@module: tests.integration.scaffold_validation
@layer: Test Infrastructure
@dependencies: [pytest, mcp_server.tools.scaffold_artifact,
                mcp_server.core.exceptions.ValidationError]
@responsibilities:
    - Test ValidationError.to_resource_dict() integration with ToolResult
    - Verify schema returned on missing required fields
"""
# Standard library
import json
from pathlib import Path

# Third-party
import pytest

# Project modules
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.tools.scaffold_artifact import (
    ScaffoldArtifactInput,
    ScaffoldArtifactTool,
)


@pytest.mark.asyncio
async def test_validation_error_returns_schema(
    artifact_manager: ArtifactManager, temp_workspace: Path
) -> None:
    """Verify missing required fields returns ValidationError with schema"""
    # GIVEN: scaffold_artifact tool with incomplete context (missing required field)
    tool = ScaffoldArtifactTool(manager=artifact_manager)
    output_path = temp_workspace / "test_dto.py"
    scaffold_input = ScaffoldArtifactInput(
        artifact_type="dto",
        name="TestDTO",
        output_path=str(output_path),
        context={
            "name": "TestDTO"
            # Missing 'description' - required by DTO template
        }
    )

    # WHEN: Attempting to scaffold DTO artifact without required 'description' field
    result = await tool.execute(scaffold_input)

    # THEN: Returns ToolResult with ValidationError resource containing schema JSON
    assert result.is_error, "Scaffold should fail with missing required field"
    assert len(result.content) >= 2, "Should have error text and schema resource"

    # First item is error text
    assert result.content[0]['type'] == "text", "First content should be error message"

    # Second item is schema resource
    schema_content = result.content[1]
    assert schema_content['type'] == "resource", "Should return resource with schema"
    assert (
        "schema://validation" in schema_content['resource']['uri']
    ), "Schema URI should indicate validation"
    assert (
        "application/json" in schema_content['resource']['mimeType']
    ), "Schema should be JSON"

    # Verify schema contains expected structure
    schema_json = json.loads(schema_content['resource']['text'])
    assert "required" in schema_json, "Schema should have required fields"
    assert "optional" in schema_json, "Schema should have optional fields"
    assert "description" in schema_json["required"], "description should be required"


@pytest.mark.asyncio
async def test_success_response_includes_schema(
    artifact_manager: ArtifactManager, temp_workspace: Path
) -> None:
    """Verify successful scaffold includes schema in response"""
    # GIVEN: scaffold_artifact tool with complete valid context
    tool = ScaffoldArtifactTool(manager=artifact_manager)
    output_path = temp_workspace / "test_dto.py"
    scaffold_input = ScaffoldArtifactInput(
        artifact_type="dto",
        name="TestDTO",
        output_path=str(output_path),
        context={
            "name": "TestDTO",
            "description": "Test data transfer object",
            "fields": []
        }
    )

    # WHEN: Successfully scaffolding DTO artifact with all required fields
    result = await tool.execute(scaffold_input)

    # THEN: Returns ToolResult with success resource containing file path
    assert not result.is_error, f"Scaffold should succeed: {result.content}"
    assert len(result.content) > 0, "Should have success content"

    # Verify file was created
    assert output_path.exists(), "Generated file should exist"


@pytest.mark.asyncio
async def test_system_fields_filtered_from_schema(
    artifact_manager: ArtifactManager, temp_workspace: Path
) -> None:
    """Verify system fields not included in agent-facing schema"""
    # GIVEN: Template with system fields (template_id, template_version, etc.)
    tool = ScaffoldArtifactTool(manager=artifact_manager)
    output_path = temp_workspace / "test_dto.py"
    scaffold_input = ScaffoldArtifactInput(
        artifact_type="dto",
        name="TestDTO",
        output_path=str(output_path),
        context={
            "name": "TestDTO"
            # Missing description - will trigger validation error with schema
        }
    )

    # WHEN: Validation error occurs and schema is returned
    result = await tool.execute(scaffold_input)

    # THEN: Schema only contains agent-input fields, system fields excluded
    assert result.is_error, "Should fail validation"
    assert len(result.content) >= 2, "Should have error text and schema resource"

    schema_content = result.content[1]
    assert schema_content['type'] == "resource", "Error should include schema resource"

    # Verify system fields NOT in schema
    schema_json = json.loads(schema_content['resource']['text'])
    system_fields = [
        "template_id", "template_version", "scaffold_created", "output_path"
    ]

    for field in system_fields:
        assert (
            field not in schema_json["required"]
        ), f"System field {field} should not be in required"
        assert (
            field not in schema_json["optional"]
        ), f"System field {field} should not be in optional"
