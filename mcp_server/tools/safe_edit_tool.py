# mcp_server/tools/safe_edit_tool.py
"""Safe file editing tool with validation."""
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.validation.registry import ValidatorRegistry
# Import validators to ensure registration
from mcp_server.validation.python_validator import PythonValidator
from mcp_server.validation.markdown_validator import MarkdownValidator
from mcp_server.validation.template_validator import TemplateValidator


class SafeEditInput(BaseModel):
    """Input for SafeEditTool."""
    path: str = Field(..., description="Absolute path to the file")
    content: str = Field(..., description="New content for the file")
    mode: str = Field(
        default="strict",
        description="Validation mode. 'strict' fails on error, 'interactive' writes but warns.",
        pattern="^(strict|interactive|verify_only)$"
    )


class SafeEditTool(BaseTool):
    """Tool for safely editing files with validation."""

    name = "safe_edit_file"
    description = (
        "Write content to a file with automatic validation. "
        "Supports 'strict' mode (rejects on error) or 'interactive' (warns)."
    )
    args_model = SafeEditInput

    def __init__(self) -> None:
        """Initialize and register default validators."""
        super().__init__()

        # Ensure registry is populated with Extensions
        ValidatorRegistry.register(".py", PythonValidator)
        ValidatorRegistry.register(".md", MarkdownValidator)

        # Register Patterns for Templates
        ValidatorRegistry.register_pattern(r".*_workers?\.py$", TemplateValidator("worker"))
        ValidatorRegistry.register_pattern(r".*_tools?\.py$", TemplateValidator("tool"))
        ValidatorRegistry.register_pattern(r".*_dtos?\.py$", TemplateValidator("dto"))
        ValidatorRegistry.register_pattern(r".*_adapters?\.py$", TemplateValidator("adapter"))

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    async def execute(self, params: SafeEditInput) -> ToolResult:
        """Execute the safe edit."""
        path = params.path
        content = params.content
        mode = params.mode

        passed, issues_text = await self._validate(path, content)

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
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            file_path.write_text(content, encoding="utf-8")

            status = "✅ File saved successfully."
            if not passed:
                status += f"\n⚠️ Saved with validation warnings (Mode: interactive):{issues_text}"
            elif issues_text:
                status += f"\nℹ️ Saved with non-blocking issues:{issues_text}"

            return ToolResult.text(status)

        except OSError as e:
            return ToolResult.text(f"❌ Failed to write file: {e}")

    async def _validate(self, path: str, content: str) -> tuple[bool, str]:
        """Run validators on content."""
        validators = ValidatorRegistry.get_validators(path)

        # Skip component templates (Tool, Worker, etc.) for test files
        # Tests should not be forced to look like the components they test
        is_test = "tests/" in path.replace("\\", "/") or Path(path).name.startswith("test_")
        if is_test:
            validators = [
                v for v in validators
                if not isinstance(v, TemplateValidator) or v.template_type == "base"
            ]

        # Fallback logic: If it's a Python file but no specific TemplateValidator is found,
        # apply the 'base' template validator.
        if path.endswith(".py"):
            has_template_validator = any(
                isinstance(v, TemplateValidator) for v in validators
            )
            if not has_template_validator:
                validators.append(TemplateValidator("base"))

        issues_text = ""
        passed = True

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

        return passed, issues_text
