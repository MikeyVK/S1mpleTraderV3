# mcp_server/tools/safe_edit_tool.py
"""
Safe File Editing Tool with Validation and Mutex Protection.

Multi-mode file editing tool supporting full rewrites, line-based edits,
line insertions, and search/replace operations. Includes file-level mutex
protection to prevent concurrent edit race conditions, integrated validation,
and diff preview capabilities.

@layer: Service (MCP Tools)
@dependencies: [re, asyncio, difflib, pathlib, typing, dataclasses, pydantic]
@responsibilities:
    - Provide safe multi-mode file editing (content/line_edits/insert_lines/search_replace)
    - Enforce file-level mutex to prevent concurrent edit race conditions
    - Validate edited content before writing (strict/interactive/verify_only modes)
    - Generate unified diff previews for transparency
    - Handle edge cases (new files, encoding, line range validation)
"""

# Standard library
import asyncio
import re
from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path
from typing import Any

# Third-party
from pydantic import BaseModel, Field, field_validator, model_validator

# Project modules
from mcp_server.tools.base import BaseTool
from mcp_server.tools.tool_result import ToolResult
from mcp_server.validation.validation_service import ValidationService


@dataclass
class EditResponse:
    """Parameters for building edit response."""
    passed: bool
    issues: str
    diff: str


@dataclass
class SearchReplaceParams:
    """Parameters for search/replace operation."""
    search: str
    replace: str
    regex: bool = False
    count: int | None = None
    flags: int = 0


class LineEdit(BaseModel):
    """Represents a line-based edit operation.
    
    IMPORTANT: new_content must include trailing newline (\\n) to replace the line correctly.
    Without it, the next line will be appended to the edited line.
    """

    start_line: int = Field(..., description="Starting line number (1-based, inclusive)")
    end_line: int = Field(..., description="Ending line number (1-based, inclusive)")
    new_content: str = Field(
        ...,
        description=(
            "New content for the line range. "
            "⚠️ MUST include trailing newline (\\n) unless intentionally joining with next line. "
            "Example: 'def foo():\\n' not 'def foo():'"
        )
    )

    @model_validator(mode="after")
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
        ..., description="Insert before this line (1-based). Use file_lines+1 to append."
    )
    content: str = Field(..., description="Content to insert")

    @model_validator(mode="after")
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
        description=(
            "List of line-based edits (chirurgical edits). "
            "⚠️ CRITICAL: Bundle ALL edits for the same file in ONE call! "
            "Multiple sequential calls will cause race conditions. "
            "File-level mutex protection enforces sequential execution."
        )
    )
    insert_lines: list[InsertLine] | None = Field(
        None, description="List of line insert operations"
    )
    # Flattened search/replace parameters (no nested SearchReplace object)
    search: str | None = Field(None, description="Pattern to search for (search/replace mode)")
    replace: str | None = Field(None, description="Replacement text (search/replace mode)")
    regex: bool = Field(
        default=False, description="Use regex pattern matching (search/replace mode)"
    )
    search_count: int | None = Field(
        None, description="Maximum number of replacements, None = all (search/replace mode)"
    )
    search_flags: int = Field(
        default=0, description="Regex flags e.g. re.IGNORECASE (search/replace mode)"
    )

    mode: str = Field(
        default="strict",
        description="Validation mode. 'strict' fails on error, 'interactive' writes but warns.",
        pattern="^(strict|interactive|verify_only)$",
    )
    show_diff: bool = Field(
        default=True, description="Show unified diff preview comparing original and new content"
    )

    @field_validator("search_flags", mode="before")
    @classmethod
    def _coerce_flags(cls, value: Any) -> int:
        if value is None:
            return 0
        return int(value)

    @model_validator(mode="after")
    def validate_edit_modes(self) -> "SafeEditInput":
        """Validate that exactly one edit mode is specified."""
        # Check if search/replace mode is active
        search_replace_active = self.search is not None or self.replace is not None

        modes = [self.content, self.line_edits, self.insert_lines, search_replace_active]

        # Count non-None modes
        specified_modes = sum(1 for mode in modes if mode)

        if not specified_modes:
            raise ValueError(
                "At least one edit mode must be specified: "
                "content, line_edits, insert_lines, or search/replace (search + replace)"
            )

        if specified_modes > 1:
            raise ValueError(
                "Only one edit mode can be specified at a time. "
                "Choose one of: content, line_edits, insert_lines, or search/replace"
            )

        # If search/replace mode, both search and replace must be provided
        if search_replace_active:
            if self.search is None or self.replace is None:
                raise ValueError(
                    "Both search and replace parameters must be provided for search/replace mode"
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
    
    **IMPORTANT - Concurrent Edit Protection:**
    - File-level mutex prevents race conditions
    - Bundle multiple edits in ONE call using line_edits list
    - Sequential calls on same file will wait for lock (10ms timeout)
    - Example: [{"start_line": 1, "end_line": 1, "new_content": "..."}, ...]
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
        """Initialize tool and validation service."""
        super().__init__()
        self.validation_service = ValidationService()
        # Mutex for preventing concurrent edits on same file
        self._file_locks: dict[str, asyncio.Lock] = {}

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return the input schema for the tool."""
        return SafeEditInput.model_json_schema()

    async def execute(self, params: SafeEditInput) -> ToolResult:
        """Execute the safe edit with validation.
        
        Uses file-level locking to prevent concurrent edits on the same file.
        Multiple edits for the same file should be batched in line_edits list.
        """
        # Normalize path for lock key
        file_key = str(Path(params.path).resolve())
        # Get or create lock for this file
        if file_key not in self._file_locks:
            self._file_locks[file_key] = asyncio.Lock()
        file_lock = self._file_locks[file_key]
        # Try to acquire lock with timeout
        try:
            async with asyncio.timeout(0.01):  # 10ms timeout - very aggressive
                async with file_lock:
                    # Read original content
                    original_result = self._read_original(params)
                    if isinstance(original_result, ToolResult):
                        return original_result  # Error
                    original_content = original_result

                    # Generate new content based on edit mode
                    new_result = self._generate_new_content(params, original_content)
                    if isinstance(new_result, ToolResult):
                        return new_result  # Error
                    new_content = new_result

                    # Generate diff if requested
                    diff_output = ""
                    if params.show_diff:
                        diff_output = self._generate_diff(
                            params.path, original_content, new_content
                        )

                    # Validate new content
                    passed, issues_text = await self._validate(params.path, new_content)

                    # Build response object
                    response = EditResponse(
                        passed=passed,
                        issues=issues_text,
                        diff=diff_output
                    )

                    # Handle verify_only mode
                    if params.mode == "verify_only":
                        return self._build_verify_response(response)

                    # Handle strict mode with validation failure
                    if params.mode == "strict" and not passed:
                        return self._build_rejection_response(response)

                    # Write file (strict+passed or interactive)
                    return self._write_and_respond(params.path, new_content, response)
        except TimeoutError:
            return ToolResult.error(
                f"❌ File '{params.path}' is already being edited. "
                "Please wait or bundle multiple edits in one call using line_edits list."
            )


    def _read_original(self, params: SafeEditInput) -> str | ToolResult:
        """Read original file content or return error for new files with incompatible modes."""
        try:
            return Path(params.path).read_text(encoding="utf-8")
        except FileNotFoundError:
            # New file - check if edit mode is compatible
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
            if params.search is not None:
                return ToolResult.error(
                    "Cannot apply search/replace to non-existent file. "
                    "Use content mode to create the file first."
                )
            return ""  # Empty file for content mode
        except (UnicodeDecodeError, PermissionError) as e:
            return ToolResult.error(f"Failed to read file: {e}")

    def _generate_new_content(self, params: SafeEditInput, original: str) -> str | ToolResult:
        """Generate new content based on edit mode."""
        if params.content is not None:
            return params.content
        if params.line_edits is not None:
            return self._handle_line_edits(original, params.line_edits)
        if params.insert_lines is not None:
            return self._handle_insert_lines(original, params.insert_lines)
        if params.search is not None and params.replace is not None:
            return self._handle_search_replace(params, original)
        return ToolResult.error(
            "Must provide 'content', 'line_edits', 'insert_lines', or 'search' + 'replace'"
        )

    def _handle_line_edits(
        self, original: str, line_edits: list[LineEdit]
    ) -> str | ToolResult:
        """Handle line_edits mode."""
        try:
            return self._apply_line_edits(original, line_edits)
        except ValueError as e:
            return ToolResult.error(f"Line edit failed: {e}")

    def _handle_insert_lines(
        self, original: str, insert_lines: list[InsertLine]
    ) -> str | ToolResult:
        """Handle insert_lines mode."""
        try:
            return self._apply_insert_lines(original, insert_lines)
        except ValueError as e:
            return ToolResult.error(f"Insert lines failed: {e}")

    def _handle_search_replace(self, params: SafeEditInput, original: str) -> str | ToolResult:
        """Handle search/replace mode."""
        try:
            new_content, count = self._apply_search_replace(params, original)
            if params.mode == "strict" and not count:
                error_msg = f"❌ Pattern '{params.search}' not found in file\n\n"
                error_msg += self._build_file_context_preview(original)
                return ToolResult.error(error_msg)
            return new_content
        except (ValueError, re.error) as e:
            return ToolResult.error(f"Search/replace failed: {e}")

    def _apply_search_replace(self, params: SafeEditInput, content: str) -> tuple[str, int]:
        """Apply search/replace with params."""
        assert params.search is not None and params.replace is not None
        srp = SearchReplaceParams(
            search=params.search,
            replace=params.replace,
            regex=params.regex,
            count=params.search_count,
            flags=params.search_flags,
        )
        return self._apply_search_replace_flat(content, srp)

    def _build_verify_response(self, response: EditResponse) -> ToolResult:
        """Build response for verify_only mode."""
        status = "✅ Validation Passed" if response.passed else "❌ Validation Failed"
        text = f"{status}{response.issues}"
        if response.diff:
            text = f"**Diff Preview:**\n```diff\n{response.diff}\n```\n\n{text}"
        return ToolResult.text(text)

    def _build_rejection_response(self, response: EditResponse) -> ToolResult:
        """Build response for strict mode rejection."""
        text = (
            f"❌ Edit rejected due to validation errors (Mode: strict):{response.issues}\n"
            "Use mode='interactive' to force save if necessary, or fix the content."
        )
        if response.diff:
            text = f"**Diff Preview:**\n```diff\n{response.diff}\n```\n\n{text}"
        return ToolResult.text(text)

    def _write_and_respond(
        self, path: str, content: str, response: EditResponse
    ) -> ToolResult:
        """Write file and build success response."""
        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

            status = "✅ File saved successfully."
            if not response.passed:
                status += (
                    f"\n⚠️ Saved with validation warnings (Mode: interactive):"
                    f"{response.issues}"
                )
            elif response.issues:
                status += f"\nℹ️ Saved with non-blocking issues:{response.issues}"

            if response.diff:
                status = f"**Diff Preview:**\n```diff\n{response.diff}\n```\n\n{status}"

            return ToolResult.text(status)
        except OSError as e:
            return ToolResult.error(f"❌ Failed to write file: {e}")

    def _apply_line_edits(self, content: str, edits: list[LineEdit]) -> str:
        """Apply line-based edits to content."""
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
            start_idx = edit.start_line - 1
            end_idx = edit.end_line

            new_lines = edit.new_content.splitlines(keepends=True)

            if new_lines and lines and not new_lines[-1].endswith(("\n", "\r\n")):
                if end_idx <= len(lines) and any(lines[start_idx:end_idx]):
                    new_lines[-1] = new_lines[-1] + "\n"

            lines[start_idx:end_idx] = new_lines

        return "".join(lines)

    def _apply_insert_lines(self, content: str, inserts: list[InsertLine]) -> str:
        """Apply line insert operations to content."""
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)

        for insert in inserts:
            if insert.at_line < 1 or insert.at_line > total_lines + 1:
                raise ValueError(
                    f"Insert at_line {insert.at_line} is out of bounds "
                    f"(valid range: 1-{total_lines + 1})"
                )

        sorted_inserts = sorted(inserts, key=lambda i: i.at_line, reverse=True)

        for insert in sorted_inserts:
            insert_idx = insert.at_line - 1
            insert_lines = insert.content.splitlines(keepends=True)

            if insert_lines and not insert_lines[-1].endswith(("\n", "\r\n")):
                insert_lines[-1] = insert_lines[-1] + "\n"

            lines[insert_idx:insert_idx] = insert_lines

        return "".join(lines)

    def _apply_search_replace_flat(
        self,
        content: str,
        params: SearchReplaceParams,
    ) -> tuple[str, int]:
        """Apply search and replace operation.
        
        Args:
            content: Content to search in.
            params: Search/replace parameters.
            
        Returns:
            Tuple of (new_content, replacement_count).
        """
        if params.regex:
            try:
                pattern = re.compile(params.search, params.flags or 0)
                if params.count is not None:
                    new_content, replacement_count = pattern.subn(
                        params.replace, content, count=params.count
                    )
                else:
                    new_content, replacement_count = pattern.subn(params.replace, content)
                return new_content, replacement_count
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}") from e

        # Literal string matching
        if params.count is not None:
            parts = content.split(params.search, params.count)
            new_content = params.replace.join(parts)
            replacement_count = len(parts) - 1
        else:
            replacement_count = content.count(params.search)
            new_content = content.replace(params.search, params.replace)

        return new_content, replacement_count

    def _generate_diff(self, path: str, original_content: str, new_content: str) -> str:
        """Generate unified diff between original and new content."""
        if original_content == new_content:
            return ""

        filename = Path(path).name
        original_lines = original_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff_lines = unified_diff(
            original_lines, new_lines, fromfile=f"a/{filename}", tofile=f"b/{filename}", lineterm=""
        )

        return "".join(diff_lines)

    async def _validate(self, path: str, content: str) -> tuple[bool, str]:
        """Delegate validation to ValidationService."""
        return await self.validation_service.validate(path, content)

    def _build_file_context_preview(self, content: str, max_lines: int = 10) -> str:
        """Build file preview for error messages (DRY helper).
        
        Args:
            content: File content to preview.
            max_lines: Maximum number of lines to show.
            
        Returns:
            Formatted preview string with line numbers.
        """
        lines = content.splitlines()[:max_lines]
        preview = "**File Preview (first 10 lines):**\n"
        for i, line in enumerate(lines, 1):
            preview += f"{i:3}: {line}\n"

        total_lines = len(content.splitlines())
        if total_lines > max_lines:
            preview += f"... ({total_lines} total lines)\n"

        return preview
