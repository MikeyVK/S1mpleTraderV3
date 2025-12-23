# mcp_server/tools/safe_edit_tool.py
"""Safe file editing tool with validation."""
import re
from difflib import unified_diff
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.validation.registry import ValidatorRegistry
# Import validators to ensure registration
from mcp_server.validation.python_validator import PythonValidator
from mcp_server.validation.markdown_validator import MarkdownValidator
from mcp_server.validation.template_validator import TemplateValidator


class LineEdit(BaseModel):
    """Represents a line-based edit operation."""
    start_line: int = Field(..., description="Starting line number (1-based, inclusive)")
    end_line: int = Field(..., description="Ending line number (1-based, inclusive)")
    new_content: str = Field(..., description="New content for the line range")

    @model_validator(mode='after')
    def validate_line_range(self) -> "LineEdit":
        """Validate that line range is valid."""
        if self.start_line < 1:
            raise ValueError("start_line must be >= 1")
        if self.end_line < 1:
            raise ValueError("end_line must be >= 1")
        if self.start_line > self.end_line:
            raise ValueError("start_line must be <= end_line")
        return self


class SearchReplace(BaseModel):
    """Represents a search/replace operation."""
    search: str = Field(..., description="Pattern to search for")
    replace: str = Field(..., description="Replacement text")
    regex: bool = Field(default=False, description="Use regex pattern matching")
    count: int | None = Field(None, description="Maximum number of replacements (None = all)")
    flags: int = Field(default=0, description="Regex flags (e.g., re.IGNORECASE)")


class SafeEditInput(BaseModel):
    """Input for SafeEditTool."""
    path: str = Field(..., description="Absolute path to the file")
    content: str | None = Field(None, description="New content for the file (full rewrite)")
    line_edits: list[LineEdit] | None = Field(
        None,
        description="List of line-based edits (chirurgical edits)"
    )
    search_replace: SearchReplace | None = Field(
        None,
        description="Search and replace operation"
    )
    mode: str = Field(
        default="strict",
        description="Validation mode. 'strict' fails on error, 'interactive' writes but warns.",
        pattern="^(strict|interactive|verify_only)$"
    )
    show_diff: bool = Field(
        default=True,
        description="Show unified diff preview comparing original and new content"
    )


class SafeEditTool(BaseTool):
    """Tool for safely editing files with validation."""

    name = "safe_edit_file"
    description = (
        "Write content to a file with automatic validation. "
        "Supports 'strict' mode (rejects on error) or 'interactive' (warns). "
        "Shows diff preview by default. "
        "Supports full content rewrite, chirurgical line-based edits, or search/replace."
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
        """Return the input schema for the tool."""
        return SafeEditInput.model_json_schema()

    async def execute(self, params: SafeEditInput) -> ToolResult:  # pylint: disable=too-many-return-statements,too-many-branches
        """Execute the safe edit."""
        path = params.path
        mode = params.mode
        show_diff = params.show_diff

        # Read original content
        original_content = ""
        try:
            original_content = Path(path).read_text(encoding="utf-8")
        except FileNotFoundError:
            # New file - empty original
            if params.line_edits:
                return ToolResult.error(
                    "Cannot apply line edits to non-existent file. "
                    "Use content mode to create the file first."
                )
            if params.search_replace:
                return ToolResult.error(
                    "Cannot apply search/replace to non-existent file. "
                    "Use content mode to create the file first."
                )
        except (UnicodeDecodeError, PermissionError) as e:
            return ToolResult.error(f"Failed to read file: {e}")

        # Determine edit mode and generate new content
        if params.content is not None:
            # Full content rewrite mode
            new_content = params.content
        elif params.line_edits is not None:
            # Line-based edit mode
            try:
                new_content = self._apply_line_edits(original_content, params.line_edits)
            except ValueError as e:
                return ToolResult.error(f"Line edit failed: {e}")
        elif params.search_replace is not None:
            # Search/replace mode
            try:
                new_content, replacement_count = self._apply_search_replace(
                    original_content, params.search_replace
                )
                # In strict mode, error if pattern not found
                if mode == "strict" and replacement_count == 0:
                    return ToolResult.error(
                        f"Pattern '{params.search_replace.search}' not found in file"
                    )
            except (ValueError, re.error) as e:
                return ToolResult.error(f"Search/replace failed: {e}")
        else:
            return ToolResult.error("Must provide 'content', 'line_edits', or 'search_replace'")

        # Generate diff preview
        diff_output = ""
        if show_diff:
            diff_output = self._generate_diff(path, original_content, new_content)

        passed, issues_text = await self._validate(path, new_content)

        # Handle specific modes
        if mode == "verify_only":
            status = "✅ Validation Passed" if passed else "❌ Validation Failed"
            result_text = f"{status}{issues_text}"
            if diff_output:
                result_text = f"**Diff Preview:**\n```diff\n{diff_output}\n```\n\n{result_text}"
            return ToolResult.text(result_text)

        if mode == "strict" and not passed:
            # Reject edit
            result_text = (
                f"❌ Edit rejected due to validation errors (Mode: strict):{issues_text}\n"
                "Use mode='interactive' to force save if necessary, or fix the content."
            )
            if diff_output:
                result_text = f"**Diff Preview:**\n```diff\n{diff_output}\n```\n\n{result_text}"
            return ToolResult.text(result_text)

        # Write Content (Interactive or Strict+Passed)
        try:
            # Ensure directory exists
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            file_path.write_text(new_content, encoding="utf-8")

            status = "✅ File saved successfully."
            if not passed:
                status += f"\n⚠️ Saved with validation warnings (Mode: interactive):{issues_text}"
            elif issues_text:
                status += f"\nℹ️ Saved with non-blocking issues:{issues_text}"

            # Add diff to output
            if diff_output:
                status = f"**Diff Preview:**\n```diff\n{diff_output}\n```\n\n{status}"

            return ToolResult.text(status)

        except OSError as e:
            return ToolResult.text(f"❌ Failed to write file: {e}")

    def _apply_line_edits(self, content: str, edits: list[LineEdit]) -> str:
        """Apply line-based edits to content.

        Args:
            content: Original file content
            edits: List of line edits to apply

        Returns:
            Modified content

        Raises:
            ValueError: If edits are invalid (out of bounds, overlapping)
        """
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        # Validate all edits first
        for edit in edits:
            if edit.start_line > total_lines:
                raise ValueError(
                    f"Line {edit.start_line} is out of bounds (file has {total_lines} lines)"
                )
            if edit.end_line > total_lines:
                raise ValueError(
                    f"Line {edit.end_line} is out of bounds (file has {total_lines} lines)"
                )

        # Check for overlapping edits
        sorted_edits = sorted(edits, key=lambda e: e.start_line)
        for i in range(len(sorted_edits) - 1):
            current = sorted_edits[i]
            next_edit = sorted_edits[i + 1]
            if current.end_line >= next_edit.start_line:
                raise ValueError(
                    f"Overlapping edits detected: lines {current.start_line}-{current.end_line} "
                    f"and {next_edit.start_line}-{next_edit.end_line}"
                )

        # Apply edits in reverse order to maintain line numbers
        for edit in sorted(edits, key=lambda e: e.start_line, reverse=True):
            # Convert to 0-based indexing
            start_idx = edit.start_line - 1
            end_idx = edit.end_line  # end_line is inclusive, so this is correct for slicing

            # Prepare new content with proper line ending
            new_lines = edit.new_content.splitlines(keepends=True)

            # Ensure last line has proper ending if original did
            if new_lines and lines and not new_lines[-1].endswith(('\n', '\r\n')):
                # Check if we're replacing lines that had endings
                if end_idx <= len(lines) and any(lines[start_idx:end_idx]):
                    # Add newline if original lines had them
                    new_lines[-1] = new_lines[-1] + '\n'

            # Replace the range
            lines[start_idx:end_idx] = new_lines

        return ''.join(lines)

    def _apply_search_replace(
        self, content: str, search_replace: SearchReplace
    ) -> tuple[str, int]:
        """Apply search and replace operation.

        Args:
            content: Original file content
            search_replace: Search/replace parameters

        Returns:
            Tuple of (modified_content, replacement_count)

        Raises:
            ValueError: If regex is invalid
            re.error: If regex pattern is malformed
        """
        if search_replace.regex:
            # Regex mode
            try:
                pattern = re.compile(search_replace.search, search_replace.flags)
                if search_replace.count is not None:
                    new_content, replacement_count = pattern.subn(
                        search_replace.replace, content, count=search_replace.count
                    )
                else:
                    new_content, replacement_count = pattern.subn(
                        search_replace.replace, content
                    )
                return new_content, replacement_count
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}") from e
        else:
            # Literal mode
            if search_replace.count is not None:
                # Python's str.replace() uses count parameter differently
                # We need to count manually for accurate reporting
                parts = content.split(search_replace.search, search_replace.count)
                new_content = search_replace.replace.join(parts)
                replacement_count = len(parts) - 1
            else:
                replacement_count = content.count(search_replace.search)
                new_content = content.replace(search_replace.search, search_replace.replace)

            return new_content, replacement_count

    def _generate_diff(self, path: str, original_content: str, new_content: str) -> str:
        """Generate unified diff between original and new content."""
        # Quick check: no changes
        if original_content == new_content:
            return ""

        # Generate diff
        filename = Path(path).name
        original_lines = original_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff_lines = unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )

        return "".join(diff_lines)

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
