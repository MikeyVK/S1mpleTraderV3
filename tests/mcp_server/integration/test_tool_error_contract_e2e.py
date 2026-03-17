"""E2E test verifying MCPError contract preservation through tool layer.

This test proves that the unified exception hierarchy works end-to-end:
1. Domain layer raises MCPError with code/hints/file_path
2. Manager propagates exception
3. Tool error_handler decorator catches and extracts contract fields
4. ToolResult preserves error_code, hints, file_path
5. Client can access structured error information

This addresses Gap A from slice1_gaps.md.
"""

from unittest.mock import Mock

import pytest

from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.tools.scaffold_artifact import (
    ScaffoldArtifactInput,
    ScaffoldArtifactTool,
)


@pytest.mark.asyncio
async def test_config_error_preserves_contract(artifact_manager: ArtifactManager) -> None:
    """Test ConfigError contract preserved through tool layer."""
    tool = ScaffoldArtifactTool(manager=artifact_manager)

    # Invalid artifact type triggers ConfigError
    params = ScaffoldArtifactInput(
        artifact_type="nonexistent_type",
        name="TestArtifact",
    )

    result = await tool.execute(params)

    # Verify error structure
    assert result.is_error, "Expected error result"
    assert result.error_code == "ERR_CONFIG", "Expected config error code"
    # This ConfigError happens to have empty hints list (not None)
    # The important thing is error_code and file_path are preserved
    assert result.file_path is not None, "Expected file path"
    assert result.file_path.endswith("artifacts.yaml"), "Expected artifacts.yaml file path"
    # Check message contains helpful information
    assert "nonexistent_type" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_validation_error_preserves_contract(artifact_manager: ArtifactManager) -> None:
    """Test ValidationError contract preserved through tool layer."""
    from mcp_server.core.exceptions import ValidationError

    tool = ScaffoldArtifactTool(manager=artifact_manager)

    # Mock manager to raise ValidationError
    tool.manager.scaffold_artifact = Mock(
        side_effect=ValidationError(
            message="Missing required field: output_path",
            hints=["Provide output_path parameter", "Check artifact definition"],
        )
    )

    params = ScaffoldArtifactInput(
        artifact_type="dto",
        name="TestDTO",
    )

    result = await tool.execute(params)

    # Verify ValidationError contract preserved
    assert result.is_error, "Expected error result"
    assert result.error_code == "ERR_VALIDATION", "Expected validation error code"
    assert result.hints is not None, "Expected hints to be present"
    assert len(result.hints) == 2, "Expected 2 hints"
    assert "Provide output_path parameter" in result.hints
    assert "Check artifact definition" in result.hints
    assert "Missing required field" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_execution_error_preserves_contract(artifact_manager: ArtifactManager) -> None:
    """Test ExecutionError contract preserved through tool layer."""
    from mcp_server.core.exceptions import ExecutionError

    tool = ScaffoldArtifactTool(manager=artifact_manager)

    # Mock manager to raise ExecutionError
    tool.manager.scaffold_artifact = Mock(
        side_effect=ExecutionError(
            message="Template rendering failed",
            recovery=["Check template syntax", "Verify context variables"],
        )
    )

    params = ScaffoldArtifactInput(
        artifact_type="dto",
        name="TestDTO",
    )

    result = await tool.execute(params)

    # Verify ExecutionError contract preserved
    assert result.is_error, "Expected error result"
    assert result.error_code == "ERR_EXECUTION", "Expected execution error code"
    assert result.hints is not None, "Expected recovery hints"
    assert len(result.hints) == 2, "Expected 2 recovery hints"
    assert "Check template syntax" in result.hints
    assert "Verify context variables" in result.hints
    assert "Template rendering failed" in result.content[0]["text"]
