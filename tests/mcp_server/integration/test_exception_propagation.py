"""
@module: tests.integration.test_exception_propagation
@layer: Test Infrastructure
@dependencies: pytest, mcp_server.core.exceptions, mcp_server.managers
@responsibilities:
  - Integration test for exception propagation through layers
  - Verify tool -> manager -> scaffolder error flow
  - Ensure exceptions maintain contract across boundaries
"""

# Standard library
from pathlib import Path

# Third-party
import pytest

# Project
from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.managers.artifact_manager import ArtifactManager


@pytest.fixture(autouse=True)
def _force_v1_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force V1 pipeline: these tests validate V1 scaffolding infrastructure."""
    monkeypatch.setenv("PYDANTIC_SCAFFOLDING_ENABLED", "false")


@pytest.mark.asyncio
async def test_validation_error_propagates_from_scaffolder(
    artifact_manager: ArtifactManager, temp_workspace: Path
) -> None:
    """ValidationError propagates from TemplateScaffolder through ArtifactManager."""
    # Missing required field should trigger ValidationError
    with pytest.raises(ValidationError) as exc_info:
        await artifact_manager.scaffold_artifact(
            artifact_type="design",
            output_path="docs/test.md",
            # Missing: issue_number, title, author
        )

    # Verify error contract
    error = exc_info.value
    assert error.code == "ERR_VALIDATION"
    assert "required" in error.message.lower()
    assert isinstance(error, ValidationError)


@pytest.mark.asyncio
async def test_config_error_for_unknown_artifact_type(
    artifact_manager: ArtifactManager, temp_workspace: Path
) -> None:
    """ConfigError raised for unknown artifact type."""
    with pytest.raises(ConfigError) as exc_info:
        await artifact_manager.scaffold_artifact(
            artifact_type="nonexistent_type",
            output_path="docs/test.md",
        )

    # Verify error contract
    error = exc_info.value
    assert error.code == "ERR_CONFIG"
    assert "nonexistent_type" in error.message
    assert isinstance(error, ConfigError)


@pytest.mark.asyncio
async def test_validation_error_has_hints(
    artifact_manager: ArtifactManager, temp_workspace: Path
) -> None:
    """ValidationError includes actionable hints."""
    with pytest.raises(ValidationError) as exc_info:
        await artifact_manager.scaffold_artifact(
            artifact_type="design",
            output_path="docs/test.md",
        )

    error = exc_info.value
    # TemplateScaffolder should provide field names in error message
    assert "issue_number" in error.message or "title" in error.message
