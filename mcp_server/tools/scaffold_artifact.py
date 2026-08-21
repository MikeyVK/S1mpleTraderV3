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

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from mcp_server.core.exceptions import ConfigError, MCPError, ValidationError
from mcp_server.core.interfaces.icore_tool import ICoreTool
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.schemas.tool_outputs import ScaffoldArtifactOutput


class ScaffoldArtifactInput(BaseModel):
    """Input for scaffold_artifact tool."""

    model_config = ConfigDict(extra="forbid")

    artifact_type: str = Field(
        ..., description="Artifact type ID from registry (e.g., 'dto', 'design', 'worker')"
    )
    name: str = Field(..., description="Artifact name (PascalCase for code, kebab-case for docs)")
    output_path: str | None = Field(
        default=None, description="Optional explicit path (overrides auto-resolution)"
    )
    context: dict[str, Any] | None = Field(
        default=None, description="Template rendering context (varies by artifact type)"
    )


class ScaffoldArtifactTool(ICoreTool[ScaffoldArtifactInput, ScaffoldArtifactOutput]):
    """Unified artifact scaffolding tool.

    Handles both code artifacts (dto, worker, adapter, etc.)
    and document artifacts (design, architecture, etc.).
    """

    output_model: ClassVar[type[BaseModel]] = ScaffoldArtifactOutput

    def __init__(self, manager: ArtifactManager | None = None) -> None:
        """Initialize tool with an explicitly injected artifact manager."""
        if manager is None:
            raise ValueError("ArtifactManager must be injected for scaffold_artifact")
        self.manager = manager

    @property
    def name(self) -> str:
        return "scaffold_artifact"

    @property
    def description(self) -> str:
        return "Scaffold any artifact type (code or document) from unified registry."

    @property
    def args_model(self) -> type[ScaffoldArtifactInput] | None:
        return ScaffoldArtifactInput

    @property
    def input_schema(self) -> dict[str, Any]:
        from mcp_server.utils.schema_utils import resolve_schema_refs  # noqa: PLC0415

        assert self.args_model is not None
        schema = resolve_schema_refs(self.args_model.model_json_schema())
        schema["properties"]["artifact_type"]["enum"] = self.manager.registry.list_type_ids()
        return schema

    async def execute(
        self,
        params: ScaffoldArtifactInput,
        context: NoteContext,
    ) -> ScaffoldArtifactOutput:
        """Execute artifact scaffolding.

        Args:
            params: Scaffolding parameters
            context: NoteContext for note production

        Returns:
            ScaffoldArtifactOutput DTO
        """
        # Prepare kwargs from template context
        template_ctx = params.context or {}
        kwargs = {"name": params.name, **template_ctx}

        # Add output_path if provided
        if params.output_path:
            kwargs["output_path"] = params.output_path

        try:
            # Scaffold artifact via manager, forwarding NoteContext for note production
            artifact_path = await self.manager.scaffold_artifact(
                params.artifact_type, note_context=context, **kwargs
            )

            files_created = [str(artifact_path)]

            return ScaffoldArtifactOutput(
                success=True,
                artifact_type=params.artifact_type,
                name=params.name,
                files_created=files_created,
            )
        except ValidationError as e:
            validation_schema = getattr(e, "schema", None)
            if validation_schema is not None:
                if hasattr(validation_schema, "to_dict"):
                    validation_schema = validation_schema.to_dict()
                elif isinstance(validation_schema, BaseModel):
                    validation_schema = validation_schema.model_dump()
            missing_fields = getattr(e, "missing_fields", [])
            provided_fields = getattr(e, "provided_fields", [])

            return ScaffoldArtifactOutput(
                success=False,
                error_message=str(e),
                artifact_type=params.artifact_type,
                name=params.name,
                validation_schema=validation_schema,
                missing_fields=missing_fields,
                provided_fields=provided_fields,
            )
        except (ConfigError, OSError, ValueError, RuntimeError, MCPError) as e:
            return ScaffoldArtifactOutput(
                success=False,
                error_message=str(e),
                artifact_type=params.artifact_type,
                name=params.name,
            )
