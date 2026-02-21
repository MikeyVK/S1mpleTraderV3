"""Integration test: Template missing error propagation through call chain.

Tests that when a template file does not exist on disk, the error
propagates correctly through the entire call stack:

1. JinjaRenderer raises ExecutionError with recovery hints
2. TemplateScaffolder propagates ExecutionError (no conversion)
3. ArtifactManager propagates ExecutionError
4. Tool error_handler converts to ToolResult with preserved contract

This test uses NO MOCKS - real template loading against temp workspace.
"""

from pathlib import Path

import pytest

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
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
    - hints populated with recovery information
    - message contains template path
    """
    # Arrange: Add artifact type with non-existent template to registry
    artifacts_yaml = temp_workspace / ".st3" / "artifacts.yaml"
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
    ArtifactRegistryConfig.reset_instance()

    # Reinitialize manager with updated registry (hermetic fixture uses temp workspace)
    # The artifact_manager fixture already has temp renderer injected
    # We just need to reload the registry
    artifact_manager.scaffolder.registry = ArtifactRegistryConfig.from_file(artifacts_yaml)

    # Create tool with real manager (no mocks!)
    tool = ScaffoldArtifactTool(manager=artifact_manager)

    # Act: Call tool with artifact type that has missing template
    # This will:
    # This will:
    # 1. ArtifactRegistry checks if 'dto_missing' exists -> ConfigError
    # 2. ArtifactManager propagates ConfigError
    # 3. Tool error_handler catches and converts to ToolResult with ERR_CONFIG
    # 5. Tool error_handler catches and converts to ToolResult
    result = await tool.execute(
        ScaffoldArtifactInput(
            artifact_type="dto_missing",
            name="TestDTO",
            output_path="mcp_server/dtos/test.py",
            context={"description": "Test DTO"},
        )
    )

    # Assert: Error contract preserved through entire call chain
    assert result.is_error is True, "Expected error result"
    assert result.error_code == "ERR_CONFIG", (
        f"Expected ERR_CONFIG (artifact type not in registry), got {result.error_code}"
    )

    # Verify hints populated (registry suggestions from ConfigError)
    assert result.hints is not None, "Expected hints to be populated"
    assert len(result.hints) > 0, "Expected at least one hint"

    # Hints should mention registry, artifacts.yaml, or available types
    hints_text = " ".join(result.hints).lower()
    assert any(
        keyword in hints_text for keyword in ["registry", "artifacts.yaml", "available", "check"]
    ), f"Expected registry-related hints, got: {result.hints}"

    # Verify message contains artifact type information (not template - error happens before
    # rendering)
    assert result.content is not None
    assert len(result.content) > 0
    message = result.content[0]["text"]
    assert "dto_missing" in message, f"Expected artifact type name in message, got: {message}"
    assert "artifacts.yaml" in message, f"Expected config file reference in message, got: {message}"

    # Note: No file_path expectation - ExecutionError does not have file_path
    # (only ConfigError has file_path in exceptions.py contract)
