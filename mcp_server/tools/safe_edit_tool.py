"""Safe file editing tool with validation."""
from pathlib import Path
from typing import Any, Literal

from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.validation.registry import ValidatorRegistry
# Import validators to ensure registration
from mcp_server.validation.python_validator import PythonValidator
from mcp_server.validation.markdown_validator import MarkdownValidator
from mcp_server.validation.template_validator import TemplateValidator


class SafeEditTool(BaseTool):
    """Tool for safely editing files with validation."""

    name = "safe_edit_file"
    description = (
        "Write content to a file with automatic validation. "
        "Supports 'strict' mode (rejects on error) or 'interactive' (warns)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the file"
            },
            "content": {
                "type": "string",
                "description": "New content for the file"
            },
            "mode": {
                "type": "string",
                "enum": ["strict", "interactive", "verify_only"],
                "default": "strict",
                "description": (
                    "Validation mode. 'strict' fails on error, "
                    "'interactive' writes but reports issues."
                )
            }
        },
        "required": ["path", "content"]
    }

    def __init__(self) -> None:
        """Initialize and register default validators."""
        super().__init__()
        
        # Ensure registry is populated with Extensions
        ValidatorRegistry.register(".py", PythonValidator)
        ValidatorRegistry.register(".md", MarkdownValidator)
        
        # Register Patterns for Templates
        ValidatorRegistry.register_pattern(r".*_worker\.py$", TemplateValidator("worker"))
        ValidatorRegistry.register_pattern(r".*_tool\.py$", TemplateValidator("tool"))
        ValidatorRegistry.register_pattern(r".*_dto\.py$", TemplateValidator("dto"))
        ValidatorRegistry.register_pattern(r".*_adapter\.py$", TemplateValidator("adapter"))

    async def execute(
        self,
        path: str,
        content: str,
        mode: Literal["strict", "interactive", "verify_only"] = "strict",
        **kwargs: Any
    ) -> ToolResult:
        """Execute the safe edit."""
        # pylint: disable=too-many-locals
        file_path = Path(path)
        
        # 1. Get Validator
        # Check backward compatibility or use new list
        validators = ValidatorRegistry.get_validators(path)
        
        issues_text = ""
        passed = True
        
        # 2. Validate (run all validators)
        for validator in validators:
            result = await validator.validate(path, content=content)
            if not result.passed:
                passed = False
            
            if result.issues:
                issues_text += "\n\n**Validation Issues:**\n"
                for issue in result.issues:
                    icon = "❌" if issue.severity == "error" else "⚠️"
                    loc = f" (line {issue.line})" if issue.line else ""
                    issues_text += f"{icon} {issue.message}{loc}\n"
        
        # 3. Handle specific modes
        if mode == "verify_only":
            status = "✅ Validation Passed" if passed else "❌ Validation Failed"
            return ToolResult.text(f"{status}{issues_text}")

        if mode == "strict" and not passed:
            # Reject edit
            return ToolResult.text(
                f"❌ Edit rejected due to validation errors (Mode: strict):{issues_text}\n"
                "Use mode='interactive' to force save if necessary, or fix the content."
            )

        # 4. Write Content (Interactive or Strict+Passed)
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            file_path.write_text(content, encoding="utf-8")
            
            status = "✅ File saved successfully."
            if not passed:
                status += f"\n⚠️ Saved with validation warnings (Mode: interactive):{issues_text}"
            elif issues_text:
                status += f"\nℹ️ Saved with non-blocking issues:{issues_text}"

            return ToolResult.text(status)

        except Exception as e:  # pylint: disable=broad-exception-caught
            return ToolResult.text(f"❌ Failed to write file: {e}")
