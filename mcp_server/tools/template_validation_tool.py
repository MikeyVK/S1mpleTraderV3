"""Tool for validating file structure against templates."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mcp_server.core.interfaces.icore_tool import ICoreTool
from mcp_server.core.operation_notes import NoteContext
from mcp_server.schemas.tool_outputs import TemplateValidationErrorDTO, TemplateValidationOutput
from mcp_server.validation.template_validator import TemplateValidator


class TemplateValidationInput(BaseModel):
    """Input for TemplateValidationTool."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="Absolute path to the file")
    template_type: str = Field(
        ...,
        description="Type of template to validate against",
        pattern="^(worker|tool|dto|adapter|base)$",
    )


class TemplateValidationTool(ICoreTool[TemplateValidationInput, TemplateValidationOutput]):
    """Tool to validate a file against a specific template."""

    @property
    def name(self) -> str:
        return "validate_template"

    @property
    def description(self) -> str:
        return "Validate a file's structure against a project template (worker, tool, dto, etc.)"

    @property
    def args_model(self) -> type[TemplateValidationInput] | None:
        return TemplateValidationInput

    @property
    def input_schema(self) -> dict[str, Any]:
        assert self.args_model is not None
        return self.args_model.model_json_schema()

    async def execute(
        self, params: TemplateValidationInput, context: NoteContext
    ) -> TemplateValidationOutput:
        """Execute template validation."""
        del context  # Not used
        try:
            validator = TemplateValidator(params.template_type)
            val_result = await validator.validate(params.path)

            errors_list = []
            for issue in val_result.issues:
                errors_list.append(
                    TemplateValidationErrorDTO(
                        severity=issue.severity,
                        message=issue.message,
                    )
                )

            return TemplateValidationOutput(
                success=True,
                passed=val_result.passed,
                errors_count=len(errors_list),
                errors=errors_list,
            )

        except (ValueError, OSError) as e:
            return TemplateValidationOutput(
                success=False,
                error_message=str(e),
                passed=False,
                errors_count=0,
                errors=[],
            )
