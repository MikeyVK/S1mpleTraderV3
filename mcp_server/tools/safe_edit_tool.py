# mcp_server/tools/safe_edit_tool.py
"""
Safe File Editing Tool with Validation and Mutex Protection.

Multi-mode file editing tool supporting string replacement, text appending,
complete file rewrites, and regex pattern replacement. Includes file-level mutex
protection to prevent concurrent edit race conditions and integrated template validation.

@layer: Service (MCP Tools)
@dependencies: [re, asyncio, difflib, pathlib, typing, pydantic]
@responsibilities:
    - Provide safe 4-operation file editing (replace/append/rewrite/pattern_replace)
    - Enforce file-level mutex to prevent concurrent edit race conditions
    - Validate edited content before writing (strict/interactive/verify_only modes)
    - Enforce file existence (must_exist=True) so new files use scaffold_artifact
    - Handle edge cases (fuzzy-match diagnostics for pattern/anchor mismatches)
"""

# Standard library
import asyncio
import re
from difflib import get_close_matches
from pathlib import Path
from typing import Annotated, Literal

# Third-party
from pydantic import BaseModel, ConfigDict, Field

from mcp_server.core.interfaces.file_writer import IAtomicFileWriter
from mcp_server.core.interfaces.icore_tool import ICoreTool
from mcp_server.core.operation_notes import NoteContext
from mcp_server.schemas.tool_outputs import SafeEditOutput
from mcp_server.utils.atomic_file_writer import AtomicFileWriter
from mcp_server.validation.base import ValidationIssue
from mcp_server.validation.validation_service import ValidationService


class ReplaceOp(BaseModel):
    """Replace target_content with replacement."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["replace"] = "replace"
    target_content: str = Field(..., description="Exact string sequence to find and replace")
    replacement: str = Field(..., description="Replacement content")
    search_window: list[int] | None = Field(
        default=None,
        description="Optional 1-based line window [start_line, end_line] to scope search",
    )


class AppendOp(BaseModel):
    """Append content to file end (EOF) or relative to text anchor."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["append"] = "append"
    content: str = Field(..., description="Content to append or insert")
    anchor: str | None = Field(
        default=None,
        description="Optional target anchor string. If None, appends to EOF.",
    )
    position: Literal["after", "before"] = Field(
        default="after",
        description="Insertion position relative to anchor",
    )


class RewriteOp(BaseModel):
    """Replace entire file content (file must already exist)."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["rewrite"] = "rewrite"
    content: str = Field(..., description="New complete file content")


class PatternReplaceOp(BaseModel):
    """Regex pattern replacement."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["pattern_replace"] = "pattern_replace"
    pattern: str = Field(..., description="Regex pattern to search")
    replacement: str = Field(..., description="Replacement string")
    regex: bool = Field(default=True, description="Treat pattern as regular expression")


OperationType = Annotated[
    ReplaceOp | AppendOp | RewriteOp | PatternReplaceOp,
    Field(discriminator="op"),
]


class SafeEditInput(BaseModel):
    """Input for SafeEditTool."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="Path to target file (must exist)")
    operation: OperationType = Field(..., description="Edit operation to perform")
    mode: Literal["strict", "interactive", "verify_only"] = Field(
        default="strict",
        description="Validation mode. 'strict' fails on error, 'interactive' writes but warns.",
    )


class SafeEditTool(ICoreTool[SafeEditInput, SafeEditOutput]):
    """Tool for safely editing existing files with validation and multiple edit operations.

    Supports four mutually exclusive edit operations:
    1. **replace**: String-anchored find and replace (with optional line window scoping)
    2. **append**: Append content to EOF or relative to a text anchor (before/after)
    3. **rewrite**: Complete file rewrite for existing files
    4. **pattern_replace**: Regex pattern replacement

    All operations support:
    - Validation modes: strict (reject on error) / interactive (warn) / verify_only (dry-run)
    - Validator integration: PythonValidator, MarkdownValidator, TemplateValidator
    - Governance enforcement: must_exist=True (non-existent files direct to scaffold_artifact)
    - Fuzzy match diagnostics: suggests close string matches on anchor/target mismatches

    **IMPORTANT - Concurrent Edit Protection:**
    - File-level mutex prevents race conditions
    - Sequential calls on same file will wait for lock (10ms timeout)
    """

    @property
    def name(self) -> str:
        return "safe_edit_file"

    @property
    def description(self) -> str:
        return (
            "Edit an existing file with automatic validation. "
            "Supports 'strict' mode (rejects on error) or 'interactive' (warns). "
            "Supports string replacement, anchored/EOF text appending, "
            "full content rewrite, and regex pattern replacement."
        )

    @property
    def args_model(self) -> type[SafeEditInput] | None:
        return SafeEditInput

    def __init__(
        self,
        validator: ValidationService | None = None,
        file_writer: IAtomicFileWriter | None = None,
    ) -> None:
        """Initialize tool, validation service, and atomic file writer."""
        self.validation_service = validator if validator is not None else ValidationService()
        self.file_writer: IAtomicFileWriter = (
            file_writer if file_writer is not None else AtomicFileWriter()
        )
        # Mutex for preventing concurrent edits on same file
        self._file_locks: dict[str, asyncio.Lock] = {}

    async def execute(self, params: SafeEditInput, context: NoteContext) -> SafeEditOutput:
        """Execute the safe edit operation with validation.

        Uses file-level locking to prevent concurrent edits on the same file.
        Enforces target file existence (must_exist=True).
        """
        del context  # Not used
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
                    if isinstance(original_result, SafeEditOutput):
                        return original_result  # Error
                    original_content = original_result

                    # Generate new content based on edit mode
                    new_result = self._generate_new_content(params, original_content)
                    if isinstance(new_result, SafeEditOutput):
                        return new_result  # Error
                    new_content = new_result

                    # Diff preview is no longer part of the public agent-facing contract.
                    diff_output = ""
                    passed, issues = await self._validate(params.path, new_content)

                    # Build response DTO
                    if params.mode == "verify_only":
                        return SafeEditOutput(
                            success=True,
                            path=params.path,
                            passed=passed,
                            issues=issues,
                            mode=params.mode,
                            written=False,
                            diff=diff_output,
                            has_diff=False,
                        )

                    # Handle strict mode with validation failure
                    if params.mode == "strict" and not passed:
                        return SafeEditOutput(
                            success=False,
                            error_message=(
                                "Edit rejected due to validation errors "
                                "(Mode: strict). Use mode='interactive' to force "
                                "save if necessary, or fix the content."
                            ),
                            path=params.path,
                            passed=passed,
                            issues=issues,
                            mode=params.mode,
                            written=False,
                            diff=diff_output,
                            has_diff=False,
                        )

                    # Write file atomically
                    try:
                        self.file_writer.write_text(Path(params.path), new_content)
                    except OSError as e:
                        return SafeEditOutput(
                            success=False,
                            error_message=f"Failed to write file: {e}",
                            path=params.path,
                            passed=passed,
                            issues=issues,
                            mode=params.mode,
                            written=False,
                            diff=diff_output,
                            has_diff=False,
                        )

                    return SafeEditOutput(
                        success=True,
                        path=params.path,
                        passed=passed,
                        issues=issues,
                        mode=params.mode,
                        written=True,
                        diff=diff_output,
                        has_diff=False,
                    )
        except TimeoutError:
            return SafeEditOutput(
                success=False,
                error_message=(
                    f"File '{params.path}' is already being edited. "
                    "Please wait before attempting another edit operation."
                ),
                path=params.path,
                passed=False,
                mode=params.mode,
                written=False,
            )

    def _read_original(self, params: SafeEditInput) -> str | SafeEditOutput:
        """Read original file content or return error if file does not exist."""
        try:
            return Path(params.path).read_text(encoding="utf-8")
        except FileNotFoundError:
            return SafeEditOutput(
                success=False,
                error_message=(
                    f"File '{params.path}' does not exist. "
                    "safe_edit_file is strictly an edit tool for existing files. "
                    "To create new code or documentation files, call scaffold_artifact."
                ),
                path=params.path,
                passed=False,
                mode=params.mode,
                written=False,
            )
        except (UnicodeDecodeError, PermissionError) as e:
            return SafeEditOutput(
                success=False,
                error_message=f"Failed to read file: {e}",
                path=params.path,
                passed=False,
                mode=params.mode,
                written=False,
            )

    def _find_fuzzy_matches(self, original_text: str, target: str) -> str | None:
        """Find close matching lines in original_text for diagnostic error messages."""
        lines = original_text.splitlines()
        target_line = target.splitlines()[0] if target.splitlines() else target
        matches = get_close_matches(target_line, lines, n=3, cutoff=0.6)
        if matches:
            suggestions = "\n".join(f"  - '{m.strip()}'" for m in matches)
            return f"Did you mean one of these lines?\n{suggestions}"
        return None

    def _generate_new_content(self, params: SafeEditInput, original: str) -> str | SafeEditOutput:
        """Generate new content based on operation."""
        op = params.operation
        if isinstance(op, RewriteOp):
            return op.content
        if isinstance(op, ReplaceOp):
            search_text = original
            if op.search_window is not None:
                start_line, end_line = op.search_window
                lines = original.splitlines(keepends=True)
                window_lines = lines[start_line - 1 : end_line]
                search_text = "".join(window_lines)

            if op.target_content not in search_text:
                fuzzy = self._find_fuzzy_matches(original, op.target_content)
                err_msg = f"Pattern '{op.target_content}' not found in file"
                if fuzzy:
                    err_msg += f"\n\n{fuzzy}"
                err_msg += f"\n\n{self._build_file_context_preview(original)}"
                return SafeEditOutput(
                    success=False,
                    error_message=err_msg,
                    path=params.path,
                    passed=False,
                    mode=params.mode,
                    written=False,
                )

            if op.search_window is not None:
                start_line, end_line = op.search_window
                lines = original.splitlines(keepends=True)
                target_chunk = "".join(lines[start_line - 1 : end_line])
                replaced_chunk = target_chunk.replace(op.target_content, op.replacement, 1)
                lines[start_line - 1 : end_line] = [replaced_chunk]
                return "".join(lines)

            return original.replace(op.target_content, op.replacement, 1)
        if isinstance(op, AppendOp):
            append_text = op.content
            if not append_text.endswith("\n"):
                append_text += "\n"

            if op.anchor is None:
                prefix = "" if original.endswith("\n") or not original else "\n"
                return original + prefix + append_text

            if op.anchor not in original:
                fuzzy = self._find_fuzzy_matches(original, op.anchor)
                err_msg = f"Anchor '{op.anchor}' not found in file"
                if fuzzy:
                    err_msg += f"\n\n{fuzzy}"
                err_msg += f"\n\n{self._build_file_context_preview(original)}"
                return SafeEditOutput(
                    success=False,
                    error_message=err_msg,
                    path=params.path,
                    passed=False,
                    mode=params.mode,
                    written=False,
                )

            if op.position == "before":
                return original.replace(op.anchor, append_text + op.anchor, 1)
            return original.replace(op.anchor, op.anchor + "\n" + append_text.rstrip("\n"), 1)
        if isinstance(op, PatternReplaceOp):
            try:
                if op.regex:
                    return re.sub(op.pattern, op.replacement, original)
                return original.replace(op.pattern, op.replacement)
            except re.error as e:
                return SafeEditOutput(
                    success=False,
                    error_message=f"Regex pattern error: {e}",
                    path=params.path,
                    passed=False,
                    mode=params.mode,
                    written=False,
                )
        return original

    async def _validate(self, path: str, content: str) -> tuple[bool, tuple[ValidationIssue, ...]]:
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
