"""ScaffoldArtifactTool - Unified artifact scaffolding tool (Cycle 11).

Replaces scaffold_component and scaffold_design_doc tools.
Handles all artifact types (code + documents) via ArtifactManager.
"""

from typing import Any
from pydantic import BaseModel, Field

from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.core.errors import ValidationError, ConfigError


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
        "Scaffold any artifact type (code or document) from unified registry. "
        "Replaces scaffold_component and scaffold_design_doc tools."
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

        Args:
            params: Scaffolding parameters

        Returns:
            ToolResult with success message or error
        """
        try:
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
            artifact_path = self.manager.scaffold_artifact(
                params.artifact_type,
                **kwargs
            )

            # Success result
            return ToolResult.text(
                f"✅ Scaffolded {params.artifact_type}: {artifact_path}"
            )

        except ValidationError as e:
            # Validation failed - return helpful error
            error_msg = str(e)
            if e.hints:
                error_msg += "\n\n" + "\n".join(f"• {hint}" for hint in e.hints)
            return ToolResult.error(error_msg)

        except ConfigError as e:
            # Configuration error - return with file path
            error_msg = str(e)
            if e.file_path:
                error_msg += f"\n\nCheck configuration in: {e.file_path}"
            return ToolResult.error(error_msg)

        except Exception as e:
            # Unexpected error
            return ToolResult.error(f"Unexpected error: {e}")
