"""Tool for validating file structure against templates."""
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult
from mcp_server.validation.template_validator import TemplateValidator


class TemplateValidationInput(BaseModel):
    """Input for TemplateValidationTool."""
    path: str = Field(..., description="Absolute path to the file")
    template_type: str = Field(
        ...,
        description="Type of template to validate against",
        pattern="^(worker|tool|dto|adapter|base)$"
    )


class TemplateValidationTool(BaseTool):
    """Tool to validate a file against a specific template."""

    name = "validate_template"
    description = (
        "Validate a file's structure against a project template "
        "(worker, tool, dto, etc.)"
    )
    args_model = TemplateValidationInput

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: TemplateValidationInput) -> ToolResult:
        """Execute template validation."""
        try:
            validator = TemplateValidator(params.template_type)
            val_result = await validator.validate(params.path)

            status = (
                "✅ Template Validation Passed" if val_result.passed
                else "❌ Template Validation Failed"
            )
            details = ""
            if val_result.issues:
                details = "\n\nIssues:\n" + "\n".join(
                    f"- [{'❌' if i.severity == 'error' else '⚠️'}] {i.message}"
                    for i in val_result.issues
                )

            return ToolResult.text(f"{status}{details}")

        except (ValueError, OSError) as e:
            return ToolResult.text(f"❌ Validation error: {e}")
