"""E2E test verifying MCPError contract preservation through tool layer.

This test proves that the unified exception hierarchy works end-to-end:
1. Domain layer raises MCPError with code
2. Manager propagates exception
3. Tool error_handler decorator catches and extracts contract fields
4. ToolResult preserves error_code
5. Client can access structured error information

@layer: Tests (Integration)
@dependencies: [pytest, unittest.mock, mcp_server.tools.scaffold_artifact]
"""

from unittest.mock import Mock

import pytest

from mcp_server.core.exceptions import ExecutionError, ValidationError
from mcp_server.core.operation_notes import NoteContext
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

    result = await tool.execute(params, NoteContext())

    # Verify error structure
    assert result.is_error, "Expected error result"
    assert result.error_code == "ERR_CONFIG", "Expected config error code"
    assert result.file_path is None, "Unexpected file path on pure schema lookup error"
    assert "nonexistent_type" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_validation_error_preserves_contract(artifact_manager: ArtifactManager) -> None:
    """Test ValidationError contract preserved through tool layer."""
    tool = ScaffoldArtifactTool(manager=artifact_manager)

    # Mock manager to raise ValidationError (C4: no hints kwarg)
    tool.manager.scaffold_artifact = Mock(
        side_effect=ValidationError(
            message="Missing required field: output_path",
        )
    )

    params = ScaffoldArtifactInput(
        artifact_type="dto",
        name="TestDTO",
    )

    result = await tool.execute(params, NoteContext())

    # Verify ValidationError contract preserved
    assert result.is_error, "Expected error result"
    assert result.error_code == "ERR_VALIDATION", "Expected validation error code"
    assert "Missing required field" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_execution_error_preserves_contract(artifact_manager: ArtifactManager) -> None:
    """Test ExecutionError contract preserved through tool layer."""
    tool = ScaffoldArtifactTool(manager=artifact_manager)

    # Mock manager to raise ExecutionError (C4: no recovery kwarg)
    tool.manager.scaffold_artifact = Mock(
        side_effect=ExecutionError(
            message="Template rendering failed",
        )
    )

    params = ScaffoldArtifactInput(
        artifact_type="dto",
        name="TestDTO",
    )

    result = await tool.execute(params, NoteContext())

    # Verify ExecutionError contract preserved
    assert result.is_error, "Expected error result"
    assert result.error_code == "ERR_EXECUTION", "Expected execution error code"
    assert "Template rendering failed" in result.content[0]["text"]
