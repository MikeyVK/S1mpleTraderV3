# mcp_server/tools/scaffold_schema_tool.py
"""
Scaffold Schema Tool - Expose artifact context JSON Schema.

Returns the JSON Schema for the context parameter of an artifact type,
enabling agents to discover required/optional fields before scaffolding.

@layer: Backend (Tools)
@dependencies: [ArtifactManager, BaseTool, ToolResult]
@responsibilities:
    - Accept artifact_type from MCP client
    - Delegate to ArtifactManager.get_context_schema()
    - Return JSON Schema dict as ToolResult
    - Let tool_error_handler handle ConfigError for types without schemas
"""

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from mcp_server.core.exceptions import ConfigError
from mcp_server.core.interfaces.icore_tool import ICoreTool
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.schemas.tool_outputs import ScaffoldSchemaOutput


class ScaffoldSchemaInput(BaseModel):
    """Input for scaffold_schema tool."""

    model_config = ConfigDict(extra="forbid")

    artifact_type: str = Field(
        ...,
        description="Artifact type ID from registry (e.g., 'dto', 'design', 'research')",
    )


class ScaffoldSchemaTool(ICoreTool[ScaffoldSchemaInput, ScaffoldSchemaOutput]):
    """Read-only tool that returns the JSON Schema for an artifact context.

    Enables agents to discover required and optional context fields
    before calling scaffold_artifact.
    """

    output_model: ClassVar[type[BaseModel]] = ScaffoldSchemaOutput

    def __init__(self, manager: ArtifactManager | None = None) -> None:
        """Initialize tool with an explicitly injected artifact manager."""
        if manager is None:
            raise ValueError("ArtifactManager must be injected for scaffold_schema")
        self.manager = manager

    @property
    def name(self) -> str:
        return "scaffold_schema"

    @property
    def description(self) -> str:
        return "Return the JSON Schema for the context parameter of an artifact type."

    @property
    def args_model(self) -> type[ScaffoldSchemaInput] | None:
        return ScaffoldSchemaInput

    @property
    def input_schema(self) -> dict[str, Any]:
        from mcp_server.utils.schema_utils import resolve_schema_refs  # noqa: PLC0415

        assert self.args_model is not None
        schema = resolve_schema_refs(self.args_model.model_json_schema())
        schema["properties"]["artifact_type"]["enum"] = self.manager.registry.list_type_ids()
        return schema

    async def execute(
        self,
        params: ScaffoldSchemaInput,
        context: NoteContext,
    ) -> ScaffoldSchemaOutput:
        """Return JSON Schema for the artifact type's context model.

        Args:
            params: Input containing artifact_type
            context: NoteContext (unused)

        Returns:
            ScaffoldSchemaOutput DTO
        """
        del context
        try:
            schema_dict = self.manager.get_context_schema(params.artifact_type)
            return ScaffoldSchemaOutput(
                success=True,
                artifact_type=params.artifact_type,
                schema_data=schema_dict,
            )
        except (ConfigError, ValueError, RuntimeError) as e:
            return ScaffoldSchemaOutput(
                success=False,
                error_message=str(e),
                artifact_type=params.artifact_type,
                schema_data={},
            )
