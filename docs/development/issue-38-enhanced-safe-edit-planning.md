# Issue #38: Enhanced SafeEditTool - Planning Phase

**Status:** DRAFT  
**Author:** AI Agent  
**Date:** 2025-12-23

## Executive Summary

Detailed algorithm design, API finalization, test strategy, and implementation roadmap for enhanced SafeEditTool

---

## API Finalization

### Input Model (Final)

```python
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class SafeEditInput(BaseModel):
    """Input for SafeEditTool with multiple edit modes."""
    
    path: str = Field(description="Absolute path to the file")
    mode: Literal["strict", "interactive", "verify_only"] = Field(
        default="strict",
        description="Validation mode: strict (reject on error), interactive (warn), verify_only (no write)"
    )
    show_diff: bool = Field(
        default=True,
        description="Show unified diff preview in output"
    )
    
    # Edit modes (mutually exclusive - exactly ONE must be set)
    content: str | None = Field(
        default=None,
        description="Full file content (replaces entire file)"
    )
    line_edits: list["LineEdit"] | None = Field(
        default=None,
        description="List of line-based edits to apply"
    )
    search_replace: "SearchReplace" | None = Field(
        default=None,
        description="Search and replace operation"
    )
    
    @model_validator(mode='after')
    def validate_edit_mode(self) -> "SafeEditInput":
        """Ensure exactly one edit mode is specified."""
        modes = [self.content, self.line_edits, self.search_replace]
        set_modes = [m for m in modes if m is not None]
        
        if len(set_modes) == 0:
            raise ValueError("At least one edit mode must be specified (content, line_edits, or search_replace)")
        if len(set_modes) > 1:
            raise ValueError("Only one edit mode can be specified at a time")
        
        return self


class LineEdit(BaseModel):
    """Single line-based edit operation."""
    
    start_line: int = Field(
        ge=1,
        description="1-based line number to start edit (inclusive)"
    )
    end_line: int = Field(
        ge=1,
        description="1-based line number to end edit (inclusive)"
    )
    new_content: str = Field(
        description="New content for line range (include newlines if multi-line)"
    )
    
    @model_validator(mode='after')
    def validate_range(self) -> "LineEdit":
        """Ensure end_line >= start_line."""
        if self.end_line < self.start_line:
            raise ValueError(f"end_line ({self.end_line}) must be >= start_line ({self.start_line})")
        return self


class SearchReplace(BaseModel):
    """Search and replace operation with regex support."""
    
    search: str = Field(
        description="Pattern to search for (literal string or regex)"
    )
    replace: str = Field(
        description="Replacement text (supports \\1, \\2, etc. for regex capture groups)"
    )
    regex: bool = Field(
        default=False,
        description="Treat search pattern as regular expression"
    )
    count: int | None = Field(
        default=None,
        ge=0,
        description="Maximum number of replacements (None = replace all occurrences)"
    )
    flags: int = Field(
        default=0,
        description="Regex flags (e.g., re.IGNORECASE, re.MULTILINE). Only used if regex=True."
    )
```

### Design Decisions

**1. Mutually Exclusive Edit Modes**
- **Rationale:** Prevents ambiguity (what if both content AND line_edits are set?)
- **Implementation:** Pydantic `@model_validator` enforces exactly one mode
- **User Experience:** Clear error messages guide correct usage

**2. Line Numbers are 1-based**
- **Rationale:** Matches editor conventions (VS Code, vim, etc.)
- **Trade-off:** Python uses 0-based indexing internally (conversion needed)
- **Benefit:** User-friendly, matches displayed line numbers

**3. show_diff Default True**
- **Rationale:** Transparency by default (user sees what will change)
- **Override:** Can set `show_diff=False` for cleaner output
- **Format:** Unified diff (standard, readable)

**4. SearchReplace flags Field**
- **Decision:** Add `flags: int` for regex flags (re.IGNORECASE, re.MULTILINE, etc.)
- **Rationale:** Common use case: case-insensitive search
- **Usage:** `flags=re.IGNORECASE | re.MULTILINE`

---

## Algorithm Design

### Line Edit Application Algorithm

**Goal:** Apply multiple `LineEdit` operations to file content

**Strategy:** Reject overlapping edits (simpler, safer)

**Algorithm:**
```python
def _apply_line_edits(self, original_content: str, line_edits: list[LineEdit]) -> str:
    """Apply line-based edits to original content.
    
    Args:
        original_content: Original file content
        line_edits: List of line edits to apply
        
    Returns:
        Modified content
        
    Raises:
        ValueError: If line ranges overlap or exceed file bounds
    """
    # 1. Split content into lines (preserve line endings)
    lines = original_content.splitlines(keepends=True)
    total_lines = len(lines)
    
    # 2. Validate all edits before applying
    for edit in line_edits:
        # Check bounds
        if edit.start_line > total_lines:
            raise ValueError(
                f"start_line {edit.start_line} exceeds file length ({total_lines} lines)"
            )
        if edit.end_line > total_lines:
            raise ValueError(
                f"end_line {edit.end_line} exceeds file length ({total_lines} lines)"
            )
    
    # 3. Check for overlapping ranges
    sorted_edits = sorted(line_edits, key=lambda e: e.start_line)
    for i in range(len(sorted_edits) - 1):
        current = sorted_edits[i]
        next_edit = sorted_edits[i + 1]
        if current.end_line >= next_edit.start_line:
            raise ValueError(
                f"Overlapping edits: lines {current.start_line}-{current.end_line} "
                f"and {next_edit.start_line}-{next_edit.end_line}"
            )
    
    # 4. Apply edits in reverse order (avoids line number shifts)
    for edit in reversed(sorted_edits):
        # Convert to 0-based indexing
        start_idx = edit.start_line - 1
        end_idx = edit.end_line  # Inclusive, so end_line is last line to replace
        
        # Split new_content into lines (preserve endings)
        new_lines = edit.new_content.splitlines(keepends=True)
        
        # Ensure last line has ending if original did
        if new_lines and not new_lines[-1].endswith(('\n', '\r\n')):
            if lines and lines[-1].endswith(('\n', '\r\n')):
                new_lines[-1] += '\n'
        
        # Replace lines
        lines[start_idx:end_idx] = new_lines
    
    # 5. Join lines back
    return ''.join(lines)
```

**Key Points:**
- **Reverse order application:** Prevents line number shifts affecting subsequent edits
- **Bounds checking:** Fail fast with clear error messages
- **Overlap detection:** Sort edits by start_line, check adjacent ranges
- **Line ending preservation:** Maintain original file's line ending style

**Edge Cases Handled:**
- Empty new_content: Deletes line range
- Single line edit: start_line == end_line
- Multiple edits: Applied in reverse sorted order
- Out of bounds: Explicit error with line count

---

## Search Replace Implementation

**Algorithm:**
```python
def _apply_search_replace(
    self,
    original_content: str,
    search_replace: SearchReplace
) -> tuple[str, int]:
    """Apply search and replace to content.
    
    Args:
        original_content: Original file content
        search_replace: Search/replace configuration
        
    Returns:
        Tuple of (modified_content, replacement_count)
        
    Raises:
        ValueError: If regex pattern is invalid
    """
    import re
    
    search = search_replace.search
    replace = search_replace.replace
    count = search_replace.count or 0  # 0 means replace all
    
    if search_replace.regex:
        # Regex mode
        try:
            pattern = re.compile(search, flags=search_replace.flags)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
        
        # Apply replacement
        new_content, num_subs = pattern.subn(replace, original_content, count=count)
        
        return new_content, num_subs
    else:
        # Literal string mode
        if count is None or count == 0:
            # Replace all
            num_subs = original_content.count(search)
            new_content = original_content.replace(search, replace)
        else:
            # Replace up to count occurrences
            new_content = original_content.replace(search, replace, count)
            num_subs = count if original_content.count(search) >= count else original_content.count(search)
        
        return new_content, num_subs
```

**Return Value Enhancement:**
- Return tuple `(new_content, replacement_count)`
- Include replacement count in ToolResult output
- Example: "✅ Replaced 5 occurrences of 'old_name' → 'new_name'"

**Pattern Not Found Handling:**
```python
new_content, num_subs = self._apply_search_replace(original_content, params.search_replace)

if num_subs == 0:
    # No replacements made
    if params.mode == "strict":
        return ToolResult.error(f"❌ Pattern '{params.search_replace.search}' not found in file")
    else:
        return ToolResult.text(f"⚠️ Pattern '{params.search_replace.search}' not found (no changes made)")
```

---

## Diff Generation

**Algorithm:**
```python
from difflib import unified_diff
from pathlib import Path

def _generate_diff(
    self,
    path: str,
    original_content: str,
    new_content: str
) -> str:
    """Generate unified diff between original and new content.
    
    Args:
        path: File path (for diff header)
        original_content: Original file content
        new_content: Modified file content
        
    Returns:
        Unified diff string (empty if no changes)
    """
    # Quick check: no changes
    if original_content == new_content:
        return ""
    
    # Split into lines
    original_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    # Generate diff
    filename = Path(path).name
    diff_lines = unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    
    return "".join(diff_lines)
```

**Output Formatting:**
```python
if params.show_diff and diff:
    output = f"**Diff Preview:**\n```diff\n{diff}\n```\n\n"
else:
    output = ""

output += status_message  # ✅ File saved successfully, etc.
return ToolResult.text(output)
```

**Edge Cases:**
- No changes: Return empty string (don't show empty diff)
- Large diffs: No truncation (user needs full context)
- Binary files: Detected before diff generation (not supported)

---

## Validation Flow

**No Changes to Validator Pipeline** - Validators still receive full content

**Flow:**
```python
async def execute(self, params: SafeEditInput) -> ToolResult:
    # 1. Read original file
    try:
        original_content = Path(params.path).read_text(encoding="utf-8")
    except FileNotFoundError:
        # New file creation - use empty string as original
        original_content = ""
    except UnicodeDecodeError:
        return ToolResult.error("❌ Cannot edit binary file")
    
    # 2. Apply edit mode to generate new content
    try:
        if params.content is not None:
            new_content = params.content
        elif params.line_edits is not None:
            new_content = self._apply_line_edits(original_content, params.line_edits)
        elif params.search_replace is not None:
            new_content, num_subs = self._apply_search_replace(original_content, params.search_replace)
            # Check for zero replacements
            if num_subs == 0:
                # Handle based on mode (see Search Replace section)
                ...
    except ValueError as e:
        # Edit operation errors (overlapping ranges, invalid regex, etc.)
        return ToolResult.error(f"❌ Edit failed: {e}")
    
    # 3. Generate diff (if requested)
    diff = ""
    if params.show_diff:
        diff = self._generate_diff(params.path, original_content, new_content)
    
    # 4. Validate new content (existing validator pipeline)
    passed, issues_text = await self._validate(params.path, new_content)
    
    # 5. Handle mode (verify_only / strict / interactive)
    if params.mode == "verify_only":
        status = "✅ Validation Passed" if passed else "❌ Validation Failed"
        output = f"{status}{issues_text}"
        if diff:
            output = f"**Diff Preview:**\n```diff\n{diff}\n```\n\n{output}"
        return ToolResult.text(output)
    
    if params.mode == "strict" and not passed:
        # Reject edit
        output = f"❌ Edit rejected due to validation errors (Mode: strict):{issues_text}\n"
        if diff:
            output = f"**Diff Preview:**\n```diff\n{diff}\n```\n\n{output}"
        return ToolResult.text(output)
    
    # 6. Write file (interactive OR strict+passed)
    try:
        file_path = Path(params.path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(new_content, encoding="utf-8")
        
        status = "✅ File saved successfully."
        if not passed:
            status += f"\n⚠️ Saved with validation warnings (Mode: interactive):{issues_text}"
        
        if diff:
            output = f"**Diff Preview:**\n```diff\n{diff}\n```\n\n{status}"
        else:
            output = status
        
        return ToolResult.text(output)
        
    except OSError as e:
        return ToolResult.error(f"❌ Failed to write file: {e}")
```

**Atomicity:**
- Read original content first (backup in memory)
- Generate new content
- Validate new content
- Write ONLY if validation passes (strict mode) or in interactive mode
- No temp file needed (original content held in memory for rollback)

---

## Error Handling Strategy

### User Input Errors (Validation Errors)
**Handled by:** Pydantic validation (before execute() is called)

Examples:
- Missing edit mode: "At least one edit mode must be specified"
- Multiple edit modes: "Only one edit mode can be specified"
- Invalid line range: "end_line must be >= start_line"
- Negative count: "count must be >= 0"

**Response:** ToolResult.error() is never reached (Pydantic fails earlier)

### Edit Operation Errors
**Handled by:** Try/except in execute()

Examples:
- Line out of bounds: "start_line 500 exceeds file length (100 lines)"
- Overlapping edits: "Overlapping edits: lines 50-60 and 55-65"
- Invalid regex: "Invalid regex pattern: unbalanced parenthesis"
- Pattern not found: "Pattern 'xyz' not found in file" (mode=strict)

**Response:** `return ToolResult.error(f"❌ Edit failed: {e}")`

### File I/O Errors
**Handled by:** Try/except in execute()

Examples:
- File not found: Treat as new file (empty original content)
- Binary file: "Cannot edit binary file"
- Permission denied: "Failed to write file: Permission denied"
- Disk full: "Failed to write file: No space left on device"

**Response:** `return ToolResult.error(f"❌ {message}")`

### Validation Errors
**Handled by:** Mode-specific logic

- `mode="strict"`: Reject edit, return validation errors
- `mode="interactive"`: Write file, show warnings
- `mode="verify_only"`: Return validation result, no write

---

## Test Strategy

### Test Structure
```
tests/unit/mcp_server/tools/
├── test_safe_edit_tool.py  # Enhanced with new tests
```

### Test Categories (15+ tests total)

**1. Input Validation Tests (Pydantic) - 4 tests**
- `test_input_requires_one_edit_mode` - Error if no mode set
- `test_input_rejects_multiple_edit_modes` - Error if >1 mode set
- `test_line_edit_validates_range` - Error if end_line < start_line
- `test_search_replace_validates_count` - Error if count < 0

**2. Content Mode Tests (Existing) - 2 tests**
- `test_content_mode_full_file_rewrite` - Full content replacement
- `test_content_mode_with_validation` - Validation in strict mode

**3. Line Edit Tests - 5 tests**
- `test_line_edit_single_line` - Edit one line
- `test_line_edit_multiple_lines` - Edit line range
- `test_line_edit_multiple_ranges` - Multiple non-overlapping edits
- `test_line_edit_out_of_bounds` - Error on line > file length
- `test_line_edit_overlapping_ranges` - Error on overlaps

**4. Search/Replace Tests - 5 tests**
- `test_search_replace_literal` - Simple string replacement
- `test_search_replace_regex` - Regex with capture groups
- `test_search_replace_count_limit` - Replace first N occurrences
- `test_search_replace_pattern_not_found` - Error in strict mode
- `test_search_replace_invalid_regex` - Error on bad regex pattern

**5. Diff Preview Tests - 3 tests**
- `test_diff_preview_shown_by_default` - Diff in output (show_diff=True)
- `test_diff_preview_can_be_disabled` - No diff (show_diff=False)
- `test_diff_preview_empty_for_no_changes` - No diff if identical

**6. Mode Handling Tests - 3 tests**
- `test_verify_only_no_write` - No file modification
- `test_strict_rejects_invalid` - Reject on validation failure
- `test_interactive_writes_with_warnings` - Write despite warnings

**7. Integration Tests (with real validators) - 3 tests**
- `test_line_edit_with_python_validator` - Pylint/mypy on Python file
- `test_search_replace_preserves_validation` - Validators run after replace
- `test_all_modes_validated_consistently` - All edit modes use same validators

### Test Helpers
```python
@pytest.fixture
def temp_file(tmp_path):
    """Create temporary file with known content."""
    file = tmp_path / "test.py"
    file.write_text("line 1\nline 2\nline 3\n")
    return file

@pytest.fixture
def tool():
    """Create SafeEditTool instance."""
    return SafeEditTool()

def assert_file_content(path: Path, expected: str):
    """Helper to verify file content."""
    actual = path.read_text()
    assert actual == expected
```

### Mock Strategy
- **Real files:** Use pytest `tmp_path` for file I/O tests
- **Mock validators:** For fast unit tests (mock `_validate()`)
- **Real validators:** For integration tests (ensure validators work)

---

## Implementation Roadmap

### Phase 1: Foundation (Diff + Refactor)
**Goal:** Add diff preview to existing content mode, refactor for new modes

**Tasks:**
1. Add `show_diff` parameter to SafeEditInput
2. Implement `_generate_diff()` method
3. Update execute() to include diff in output
4. Add diff preview tests
5. **Commit:** `green: Add diff preview to SafeEditTool`

**Outcome:** Content mode has diff preview, foundation for new modes

### Phase 2: Line Edit Mode
**Goal:** Implement line-based edits

**Tasks:**
1. Add `LineEdit` model to safe_edit_tool.py
2. Add `line_edits` field to SafeEditInput
3. Implement `_apply_line_edits()` method
4. Update execute() to handle line_edits mode
5. Add line edit tests (5 tests)
6. **Commit:** `green: Implement line-based edit mode with bounds checking`

**Outcome:** Line edits working, bounds checked, overlaps rejected

### Phase 3: Search/Replace Mode
**Goal:** Implement search and replace

**Tasks:**
1. Add `SearchReplace` model to safe_edit_tool.py
2. Add `search_replace` field to SafeEditInput
3. Implement `_apply_search_replace()` method
4. Handle pattern not found (strict vs interactive)
5. Add search/replace tests (5 tests)
6. **Commit:** `green: Implement search/replace mode with regex support`

**Outcome:** Search/replace working with literal and regex modes

### Phase 4: Input Validation
**Goal:** Enforce mutually exclusive edit modes

**Tasks:**
1. Add `@model_validator` to SafeEditInput
2. Add input validation tests (4 tests)
3. **Commit:** `green: Add input validation for mutually exclusive edit modes`

**Outcome:** Clear errors if multiple modes specified

### Phase 5: Integration & Edge Cases
**Goal:** Integration tests with real validators, edge cases

**Tasks:**
1. Add integration tests (3 tests)
2. Test with PythonValidator (pylint/mypy)
3. Test edge cases (binary files, empty files, etc.)
4. **Commit:** `green: Add integration tests and edge case handling`

**Outcome:** All validators work with all modes

### Phase 6: Refactor & Quality Gates
**Goal:** Pass quality gates, optimize, document

**Tasks:**
1. Run pylint, fix issues → 10/10
2. Run mypy, fix type issues
3. Run pyright, fix type issues
4. Update tool description with examples
5. Add docstrings
6. **Commit:** `refactor: Pass quality gates and add documentation`

**Outcome:** Pylint 10/10, mypy pass, pyright pass

### Estimated Timeline
- Phase 1: 1 hour (diff foundation)
- Phase 2: 1.5 hours (line edits + tests)
- Phase 3: 1.5 hours (search/replace + tests)
- Phase 4: 0.5 hours (input validation)
- Phase 5: 1 hour (integration + edge cases)
- Phase 6: 1 hour (refactor + QA)
- **Total: ~6.5 hours**

---

## Performance Considerations

### Line Edit Performance
**Algorithm Complexity:** O(n * m) where n=file lines, m=number of edits
- Sorting edits: O(m log m)
- Applying edits: O(m * avg_edit_size)
- **Worst case:** 100 edits on 10,000 line file ≈ 100ms

**Optimization:** Apply edits in reverse order (no line number recalculation)

### Search/Replace Performance
**Algorithm Complexity:** 
- Literal: O(n) where n=file size (Python's str.replace is optimized)
- Regex: O(n * pattern_complexity) (re module is C-optimized)

**Worst case:** Regex search on 100KB file ≈ 50ms

### Diff Generation Performance
**Algorithm Complexity:** O(n) where n=file size (difflib is C-optimized)
- 500-line change on 1000-line file ≈ 100ms

**Conclusion:** All operations well within < 1 second target

### Memory Considerations
- Original content in memory (string)
- New content in memory (string)
- Validators write temp files (not in memory)
- **Peak memory:** ~2x file size + temp file

**Large file handling:** 
- 1MB file ≈ 2MB RAM (acceptable)
- 10MB file ≈ 20MB RAM (still acceptable)
- No streaming needed for typical use cases

---

## Next Steps: Design Phase

1. **Component Design:**
   - Class structure diagram
   - Method signatures
   - Data flow diagrams

2. **Detailed Pseudocode:**
   - Line edit application with edge cases
   - Search/replace with all flags
   - Error handling paths

3. **Test Case Matrix:**
   - Input → Expected Output for all test cases
   - Edge case coverage matrix

**Transition to Design:** Once planning approved
