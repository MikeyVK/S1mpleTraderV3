"""
@module: tests.integration.test_tool_error_e2e
@layer: Test Infrastructure
@dependencies: tests.fixtures.artifact_test_harness
@responsibilities:
  - E2E test for tool-layer error wrapping
  - Verify ToolResult preserves MCPError contract fields
"""

from __future__ import annotations

import asyncio

from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.tools.scaffold_artifact import ScaffoldArtifactInput, ScaffoldArtifactTool


def test_scaffold_artifact_tool_preserves_error_contract(
    artifact_manager: ArtifactManager,
) -> None:
    """Unknown artifact type is returned as ToolResult with preserved contract."""
    tool = ScaffoldArtifactTool(manager=artifact_manager)

    params = ScaffoldArtifactInput(
        artifact_type="nonexistent_type",
        name="TestArtifact",
        output_path="docs/test.md",
        context=None,
    )

    result = asyncio.run(tool.execute(params))

    assert result.is_error is True
    assert result.error_code == "ERR_CONFIG"
    assert result.file_path is not None
    assert result.file_path.endswith("artifacts.yaml")

    assert result.content
    assert "nonexistent_type" in result.content[0]["text"]
