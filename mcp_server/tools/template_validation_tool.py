"""Tool for validating file structure against templates."""
from typing import Any

from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.validation.template_validator import TemplateValidator


class TemplateValidationTool(BaseTool):
    """Tool to validate a file against a specific template."""

    name = "validate_template"
    description = (
        "Validate a file's structure against a project template "
        "(worker, tool, dto, etc.)"
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the file"
            },
            "template_type": {
                "type": "string",
                "enum": list(TemplateValidator.RULES.keys()),
                "description": "Type of template to validate against"
            }
        },
        "required": ["path", "template_type"]
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute template validation."""
        path = kwargs.get("path")
        template_type = kwargs.get("template_type")

        if not path or not template_type:
            return ToolResult.text("❌ Missing required arguments: path, template_type")

        try:
            validator = TemplateValidator(template_type)
            val_result = await validator.validate(path)

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
