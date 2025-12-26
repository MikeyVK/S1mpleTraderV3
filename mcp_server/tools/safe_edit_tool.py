# mcp_server/tools/safe_edit_tool.py
"""Safe file editing tool with validation."""
import re
from difflib import unified_diff
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

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


class InsertLine(BaseModel):
    """Represents a line insert operation."""
    at_line: int = Field(
        ...,
        description="Insert before this line (1-based). Use file_lines+1 to append."
    )
    content: str = Field(..., description="Content to insert")

    @model_validator(mode='after')
    def validate_at_line(self) -> "InsertLine":
        """Validate that at_line is valid."""
        if self.at_line < 1:
            raise ValueError("at_line must be >= 1")
        return self


class SafeEditInput(BaseModel):
    """Input for SafeEditTool."""
    path: str = Field(..., description="Absolute path to the file")
    content: str | None = Field(None, description="New content for the file (full rewrite)")
    line_edits: list[LineEdit] | None = Field(
        None,
        description="List of line-based edits (chirurgical edits)"
    )
    insert_lines: list[InsertLine] | None = Field(
        None,
        description="List of line insert operations"
    )
    # Flattened search/replace parameters (no nested SearchReplace object)
    search: str | None = Field(
        None, description="Pattern to search for (search/replace mode)"
    )
    replace: str | None = Field(
        None, description="Replacement text (search/replace mode)"
    )
    regex: bool = Field(
        default=False, description="Use regex pattern matching (search/replace mode)"
    )
    search_count: int | None = Field(
        None,
        description="Maximum number of replacements, None = all (search/replace mode)",
    )
    search_flags: int = Field(
        default=0, description="Regex flags e.g. re.IGNORECASE (search/replace mode)"
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

    @field_validator("search_flags", mode="before")
    @classmethod
    def _coerce_flags(cls, value: Any) -> int:
        if value is None:
            return 0
        return int(value)

    @model_validator(mode='after')
    def validate_edit_modes(self) -> "SafeEditInput":
        """Validate that exactly one edit mode is specified."""
        # Check if search/replace mode is active
        search_replace_active = self.search is not None or self.replace is not None

        modes = [
            self.content,
            self.line_edits,
            self.insert_lines,
            search_replace_active
        ]

        # Count non-None modes
        specified_modes = sum(1 for mode in modes if mode)

        if not specified_modes:
            raise ValueError(
                'At least one edit mode must be specified: '
                'content, line_edits, insert_lines, or search/replace (search + replace)'
            )

        if specified_modes > 1:
            raise ValueError(
                'Only one edit mode can be specified at a time. '
                'Choose one of: content, line_edits, insert_lines, or search/replace'
            )

        # If search/replace mode, both search and replace must be provided
        if search_replace_active:
            if self.search is None or self.replace is None:
                raise ValueError(
                    'Both search and replace parameters must be provided for search/replace mode'
                )

        return self


class SafeEditTool(BaseTool):
    """Tool for safely editing files with validation and multiple edit modes.
    
    Supports four mutually exclusive edit modes:
    1. **content**: Full file rewrite
    2. **line_edits**: Replace specific line ranges (surgical edits)
    3. **insert_lines**: Insert content without replacing existing lines
    4. **search_replace**: Pattern-based find/replace (literal or regex)
    
    All modes support:
    - Validation modes: strict (reject on error) / interactive (warn) / verify_only (dry-run)
    - Diff preview: Shows unified diff before applying changes (default: enabled)
    - Validator integration: PythonValidator, MarkdownValidator, TemplateValidator
    
    Examples:
    
    **Full content rewrite:**
    ```python
    SafeEditInput(
        path="file.py",
        content="def hello():\\n    print('Hello')\\n",
        mode="strict"
    )
    ```
    
    **Line-based edits (replace specific lines):**
    ```python
    SafeEditInput(
        path="file.py",
        line_edits=[
            LineEdit(start_line=10, end_line=12, new_content="new code\\n")
        ],
        mode="interactive"
    )
    ```
    
    **Insert lines (add without replacing):**
    ```python
    SafeEditInput(
        path="file.py",
        insert_lines=[
            InsertLine(at_line=1, content="import sys\\n"),
            InsertLine(at_line=10, content="# Comment\\n")
        ],
        mode="interactive"
    )
    ```
    
    **Search/replace (literal):**
    ```python
    SafeEditInput(
        path="file.py",
        search_replace=SearchReplace(search="old_name", replace="new_name"),
        mode="strict"
    )
    ```
    
    **Search/replace (regex with capturing groups):**
    ```python
    SafeEditInput(
        path="file.py",
        search_replace=SearchReplace(
            search=r"from typing import (\\w+)",
            replace=r"from collections.abc import \\1",
            regex=True
        ),
        mode="interactive"
    )
    ```
    """

    name = "safe_edit_file"
    description = (
        "Write content to a file with automatic validation. "
        "Supports 'strict' mode (rejects on error) or 'interactive' (warns). "
        "Shows diff preview by default. "
        "Supports full content rewrite, chirurgical line-based edits, "
        "line inserts, or search/replace."
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

        # Determine if search/replace mode is active
        search_replace_active = params.search is not None and params.replace is not None

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
            if params.insert_lines:
                return ToolResult.error(
                    "Cannot insert lines into non-existent file. "
                    "Use content mode to create the file first."
                )
            if search_replace_active:
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
        elif params.insert_lines is not None:
            # Insert lines mode
            try:
                new_content = self._apply_insert_lines(original_content, params.insert_lines)
            except ValueError as e:
                return ToolResult.error(f"Insert lines failed: {e}")
        elif search_replace_active:
            # Search/replace mode - use flattened parameters
            # Type narrowing: we validated that both are not None in validate_edit_modes
            assert params.search is not None and params.replace is not None
            try:
                new_content, replacement_count = self._apply_search_replace_flat(
                    original_content,
                    search=params.search,
                    replace=params.replace,
                    regex=params.regex,
                    count=params.search_count,
                    flags=params.search_flags
                )
                # In strict mode, error if pattern not found
                if mode == "strict" and not replacement_count:
                    return ToolResult.error(
                        f"Pattern '{params.search}' not found in file"
                    )
            except (ValueError, re.error) as e:
                return ToolResult.error(f"Search/replace failed: {e}")
        else:
            return ToolResult.error(
                "Must provide 'content', 'line_edits', 'insert_lines', or 'search' + 'replace'"
            )

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

    def _apply_insert_lines(self, content: str, inserts: list[InsertLine]) -> str:
        """Apply line insert operations to content.

        Args:
            content: Original file content
            inserts: List of line inserts to apply

        Returns:
            Modified content

        Raises:
            ValueError: If inserts are invalid (out of bounds)
        """
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        # Validate all inserts first
        for insert in inserts:
            # at_line can be 1 to total_lines+1 (append at end)
            if insert.at_line < 1 or insert.at_line > total_lines + 1:
                raise ValueError(
                    f"Insert at_line {insert.at_line} is out of bounds "
                    f"(valid range: 1-{total_lines + 1})"
                )

        # Sort inserts by at_line in reverse order to maintain line numbers
        sorted_inserts = sorted(inserts, key=lambda i: i.at_line, reverse=True)

        # Apply inserts in reverse order
        for insert in sorted_inserts:
            # Convert to 0-based indexing
            insert_idx = insert.at_line - 1

            # Prepare content with proper line ending
            insert_lines = insert.content.splitlines(keepends=True)

            # Ensure last line has newline
            if insert_lines and not insert_lines[-1].endswith(('\n', '\r\n')):
                insert_lines[-1] = insert_lines[-1] + '\n'

            # Insert at position
            lines[insert_idx:insert_idx] = insert_lines

        return ''.join(lines)
    def _apply_search_replace_flat(
        self,
        content: str,
        search: str,
        replace: str,
        regex: bool = False,
        count: int | None = None,
        flags: int = 0
    ) -> tuple[str, int]:
        """Apply search and replace operation with flattened parameters.

        Args:
            content: Original file content
            search: Pattern to search for
            replace: Replacement text
            regex: Use regex pattern matching
            count: Maximum number of replacements (None = all)
            flags: Regex flags (e.g., re.IGNORECASE)

        Returns:
            Tuple of (modified_content, replacement_count)

        Raises:
            ValueError: If regex is invalid
            re.error: If regex pattern is malformed
        """
        if regex:
            # Regex mode
            try:
                pattern = re.compile(search, flags or 0)
                if count is not None:
                    new_content, replacement_count = pattern.subn(
                        replace, content, count=count
                    )
                else:
                    new_content, replacement_count = pattern.subn(
                        replace, content
                    )
                return new_content, replacement_count
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}") from e
        else:
            # Literal mode
            if count is not None:
                # Python's str.replace() uses count parameter differently
                # We need to count manually for accurate reporting
                parts = content.split(search, count)
                new_content = replace.join(parts)
                replacement_count = len(parts) - 1
            else:
                replacement_count = content.count(search)
                new_content = content.replace(search, replace)


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
