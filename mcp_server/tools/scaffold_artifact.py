# mcp_server/tools/scaffold_artifact.py
"""
Scaffold Artifact Tool - Unified artifact scaffolding.

Unified scaffolding for all artifact types (code + documents).
Handles all artifact types (code + documents) via ArtifactManager.

@layer: Backend (Tools)
@dependencies: [ArtifactManager, BaseTool, ToolResult]
@responsibilities:
    - Accept artifact scaffolding requests from MCP clients
    - Delegate to ArtifactManager for orchestration
    - Format success results for LLM consumption
    - Let tool_error_handler decorator handle all errors uniformly
"""

from typing import Any

from pydantic import BaseModel, Field

from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult


class ScaffoldArtifactInput(BaseModel):
    """Input for scaffold_artifact tool."""

    artifact_type: str = Field(
        ...,
        description="Artifact type ID from registry (e.g., 'dto', 'design', 'worker')"
    )
    name: str = Field(
        ...,
        description="Artifact name (PascalCase for code, kebab-case for docs)"
    )
    output_path: str | None = Field(
        default=None,
        description="Optional explicit path (overrides auto-resolution)"
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Template rendering context (varies by artifact type)"
    )


class ScaffoldArtifactTool(BaseTool):
    """Unified artifact scaffolding tool.

    Handles both code artifacts (dto, worker, adapter, etc.)
    and document artifacts (design, architecture, etc.).
    """

    name = "scaffold_artifact"
    description = (
        "Scaffold any artifact type (code or document) from unified registry."
    )
    args_model = ScaffoldArtifactInput

    def __init__(self, manager: ArtifactManager | None = None) -> None:
        """Initialize tool with optional manager DI.

        Args:
            manager: ArtifactManager instance (default: create new)
        """
        super().__init__()
        self.manager = manager or ArtifactManager()

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return JSON schema for input validation."""
        if self.args_model is None:
            return {}
        return self.args_model.model_json_schema()

    async def execute(self, params: ScaffoldArtifactInput) -> ToolResult:
        """Execute artifact scaffolding.

        All exceptions are handled by tool_error_handler decorator,
        which preserves MCPError contract (error_code, hints, file_path).

        Args:
            params: Scaffolding parameters

        Returns:
            ToolResult with success message
        """
        # Prepare kwargs from context
        context = params.context or {}
        kwargs = {
            "name": params.name,
            **context
        }

        # Add output_path if provided
        if params.output_path:
            kwargs["output_path"] = params.output_path

        # Scaffold artifact via manager
        # Exceptions (ValidationError, ConfigError, etc.) propagate to decorator
        artifact_path = await self.manager.scaffold_artifact(
            params.artifact_type,
            **kwargs
        )

        # Success result
        return ToolResult.text(
            f"✅ Scaffolded {params.artifact_type}: {artifact_path}"
        )
