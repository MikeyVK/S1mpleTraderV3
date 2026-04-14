"""Integration test: Template missing error propagation through call chain.

Tests that when a template file does not exist on disk, the error
propagates correctly through the entire call stack:

1. JinjaRenderer raises ExecutionError
2. TemplateScaffolder propagates ExecutionError (no conversion)
3. ArtifactManager propagates ExecutionError
4. Tool error_handler converts to ToolResult with preserved contract

This test uses NO MOCKS - real template loading against temp workspace.

@layer: Tests (Integration)
@dependencies: [pytest, pathlib, mcp_server.tools.scaffold_artifact]
"""

from pathlib import Path

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.tools.scaffold_artifact import (
    ScaffoldArtifactInput,
    ScaffoldArtifactTool,
)


@pytest.mark.asyncio
async def test_template_missing_error_propagates_through_call_chain(
    temp_workspace: Path,
    artifact_manager: ArtifactManager,
) -> None:
    """
    Real E2E test: Template file missing on disk.

    NO MOCKS - proves actual error flow:
    - JinjaRenderer fails with ExecutionError (template not found)
    - TemplateScaffolder propagates ExecutionError
    - ArtifactManager propagates ExecutionError
    - Tool error_handler converts to ToolResult with contract preserved

    Validates:
    - is_error=True
    - error_code="ERR_EXECUTION"
    - message contains template path
    """
    # Arrange: Add artifact type with non-existent template to registry
    artifacts_yaml = temp_workspace / ".st3" / "config" / "artifacts.yaml"
    content = artifacts_yaml.read_text(encoding="utf-8")

    # Add dto_missing artifact type with non-existent template
    missing_artifact = """
  - type: code
    type_id: dto_missing
    name: "DTO with missing template"
    description: "Test artifact with non-existent template"
    template_path: components/does_not_exist.py.jinja2
    fallback_template: null
    name_suffix: null
    file_extension: ".py"
    generate_test: false
    required_fields:
      - name
      - description
    optional_fields: []
    state_machine:
      states: [CREATED]
      initial_state: CREATED
      valid_transitions: []
"""
    content = content.replace("artifact_types:", f"artifact_types:{missing_artifact}")
    artifacts_yaml.write_text(content, encoding="utf-8")

    # Reload registry to pick up new artifact type
    fresh_registry = ConfigLoader(artifacts_yaml.parent).load_artifact_registry_config(
        config_path=artifacts_yaml
    )

    # Reinitialize manager with updated registry (hermetic fixture uses temp workspace)
    artifact_manager.scaffolder.registry = fresh_registry
    artifact_manager.registry = fresh_registry

    # Create tool with real manager (no mocks!)
    tool = ScaffoldArtifactTool(manager=artifact_manager)

    # Act: Call tool with artifact type that has missing template
    result = await tool.execute(
        ScaffoldArtifactInput(
            artifact_type="dto_missing",
            name="TestDTO",
            output_path="mcp_server/dtos/test.py",
            context={"description": "Test DTO"},
        ),
        NoteContext(),
    )

    # Assert: Error contract preserved through entire call chain
    assert result.is_error is True, "Expected error result"
    assert result.error_code == "ERR_EXECUTION", (
        f"Expected ERR_EXECUTION (template resolution failure), got {result.error_code}"
    )

    # Verify message contains template path information
    assert result.content is not None
    assert len(result.content) > 0
    message = result.content[0]["text"]
    assert "does_not_exist.py.jinja2" in message, (
        f"Expected missing template path in message, got: {message}"
    )
    assert "dto_missing" in message or "template" in message.lower(), (
        f"Expected artifact/template context in message, got: {message}"
    )
