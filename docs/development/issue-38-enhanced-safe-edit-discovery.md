# Issue #38: Enhanced SafeEditTool - Discovery Phase

**Status:** DRAFT  
**Author:** AI Agent  
**Date:** 2025-12-23

## Executive Summary

Analysis of current SafeEditTool implementation and requirements for line-based edits, diff preview, and search/replace functionality

---

## Current Implementation Analysis

### Architecture Overview
**File:** `mcp_server/tools/safe_edit_tool.py` (133 lines)

**Current Design:**
- **Input Model:** `SafeEditInput(path, content, mode)`
- **Single Edit Mode:** Full file content rewrite only
- **Validation Modes:** strict / interactive / verify_only
- **Validator Integration:** ValidatorRegistry with Python, Markdown, Template validators

**Key Components:**
1. `SafeEditTool(BaseTool)` - MCP tool wrapper
2. `_validate(path, content)` - Validator execution
3. **Validator Registry:**
   - Extension-based: `.py` → PythonValidator, `.md` → MarkdownValidator
   - Pattern-based: `*_worker.py` → TemplateValidator("worker")
   - Test file detection: Skips component templates for test files

**Current Flow:**
```
Input (path, content, mode)
  ↓
Validate content via ValidatorRegistry
  ↓
Mode decision:
  - verify_only: Return validation result
  - strict + failed: Reject edit
  - interactive OR strict+passed: Write file
  ↓
Return ToolResult (success/error with validation feedback)
```

### Strengths
✅ **Robust validation:** Pylint, mypy, pyright integration  
✅ **Safe by default:** Strict mode prevents invalid writes  
✅ **Flexible fallback:** Interactive mode for edge cases  
✅ **Template validation:** Ensures architectural patterns  
✅ **Test-aware:** Skips component validation for test files

### Limitations
❌ **Full file writes only:** Inefficient for small changes in large files  
❌ **No diff preview:** User doesn't see changes before applying  
❌ **No bulk operations:** Can't rename variables/imports across file  
❌ **No line-based edits:** Can't target specific line ranges

---

## Validator Flow

### Current Validator Pipeline
```python
ValidatorRegistry.get_validators(path)
  ↓
Filter validators:
  - Test files: Remove component TemplateValidators
  - Python files without template: Add base TemplateValidator
  ↓
For each validator:
  - await validator.validate(path, content)
  - Collect issues (errors/warnings)
  ↓
Return (passed: bool, issues_text: str)
```

### Validator Types
1. **PythonValidator:** Pylint, mypy, pyright (writes temp file)
2. **MarkdownValidator:** Structure and formatting checks
3. **TemplateValidator:** Architectural pattern compliance (worker, tool, dto, adapter, base)

### Critical Constraint
⚠️ **Validators require full file content** - They write temp files and run external tools (pylint/mypy). Line-based edits must reconstruct full file before validation.

---

## Requirements Breakdown

### 1. Line-Based Edits
**Goal:** Edit specific line ranges without full file rewrite

**Use Cases:**
- Change function implementation (lines 50-60)
- Update import statement (lines 1-5)
- Fix docstring (lines 10-15)

**Design Considerations:**
- Read original file content
- Apply line edits to construct new full content
- Validate reconstructed content
- Write if validation passes

**Edge Cases:**
- Line numbers out of range
- Overlapping edits
- Empty line ranges
- Line ending preservation (CRLF vs LF)

### 2. Search/Replace
**Goal:** Pattern-based bulk replacements with regex support

**Use Cases:**
- Rename variable: `old_name` → `new_name`
- Update import: `from typing import List` → `from collections.abc import Sequence`
- Fix typo across file: `recieve` → `receive`

**Design Considerations:**
- Regex support with capture groups
- Count limit (replace first N occurrences)
- Case sensitivity
- Whole word matching
- Multi-line patterns

**Edge Cases:**
- Pattern not found (0 matches)
- Replacement creates invalid syntax
- Regex compilation errors
- Overlapping matches

### 3. Diff Preview
**Goal:** Show unified diff before applying changes

**Format:** Standard unified diff (like `git diff`)
```diff
--- original.py
+++ modified.py
@@ -50,3 +50,3 @@
 def process():
-    return old_value
+    return new_value
```

**Requirements:**
- Always shown by default (`show_diff: bool = True`)
- Included in ToolResult output
- Works with all edit modes (content, line_edits, search_replace)

**Library:** Python's `difflib.unified_diff()` - stdlib, no dependencies

### 4. Full Content Mode (Keep Existing)
**Goal:** Maintain backward compatibility for full file rewrites

**No Changes Needed:** Current implementation works perfectly for this use case.

---

## Edit Modes Design

### Input Model Enhancement
```python
class SafeEditInput(BaseModel):
    path: str
    mode: Literal["strict", "interactive", "verify_only"] = "strict"
    show_diff: bool = True
    
    # Mutually exclusive edit modes (exactly ONE must be set):
    content: str | None = None
    line_edits: list[LineEdit] | None = None
    search_replace: SearchReplace | None = None
    
    @model_validator(mode='after')
    def validate_edit_mode(self):
        modes = [self.content, self.line_edits, self.search_replace]
        set_modes = [m for m in modes if m is not None]
        if len(set_modes) != 1:
            raise ValueError("Exactly one edit mode must be specified")
        return self

class LineEdit(BaseModel):
    start_line: int = Field(ge=1, description="1-based line number to start edit")
    end_line: int = Field(ge=1, description="1-based line number to end edit (inclusive)")
    new_content: str = Field(description="New content for line range (with newlines)")
    
    @model_validator(mode='after')
    def validate_range(self):
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self

class SearchReplace(BaseModel):
    search: str = Field(description="Pattern to search for")
    replace: str = Field(description="Replacement text (supports \\1, \\2 for regex groups)")
    regex: bool = Field(default=False, description="Treat search as regex pattern")
    count: int | None = Field(default=None, ge=0, description="Max replacements (None = all)")
```

### Mode Selection Logic
```python
async def execute(self, params: SafeEditInput) -> ToolResult:
    # 1. Read original file
    original_content = Path(params.path).read_text(encoding="utf-8")
    
    # 2. Apply edit mode
    if params.content:
        new_content = params.content
    elif params.line_edits:
        new_content = self._apply_line_edits(original_content, params.line_edits)
    elif params.search_replace:
        new_content = self._apply_search_replace(original_content, params.search_replace)
    
    # 3. Generate diff
    diff = self._generate_diff(params.path, original_content, new_content)
    
    # 4. Validate new content
    passed, issues_text = await self._validate(params.path, new_content)
    
    # 5. Handle mode (verify_only / strict / interactive)
    # ... existing logic ...
```

---

## Diff Preview Strategy

### Implementation
**Library:** `difflib.unified_diff()` from Python stdlib

```python
from difflib import unified_diff

def _generate_diff(self, path: str, original: str, new: str) -> str:
    """Generate unified diff between original and new content."""
    original_lines = original.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    
    diff_lines = unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{Path(path).name}",
        tofile=f"b/{Path(path).name}",
        lineterm=""
    )
    
    return "".join(diff_lines)
```

### Output Format
```
**Diff Preview:**
```diff
--- a/safe_edit_tool.py
+++ b/safe_edit_tool.py
@@ -52,3 +52,3 @@
     def execute(self):
-        return old_logic()
+        return new_logic()
```
```

### Edge Cases
- Empty file → new content: Show all lines as additions
- Content → empty file: Show all lines as deletions
- No changes: Return "No changes detected"

---

## Edge Cases and Constraints

### Line-Based Edits
1. **Line numbers out of range:**
   - `start_line > file_line_count`: Error "Line X exceeds file length (Y lines)"
   - `end_line > file_line_count`: Clamp to file length or error (TBD in planning)

2. **Overlapping edits:**
   - Multiple LineEdit objects with overlapping ranges
   - Strategy: Apply edits sequentially, adjusting line numbers after each edit
   - OR: Reject overlapping edits with error (simpler, safer)

3. **Line ending consistency:**
   - Preserve original file line endings (CRLF vs LF)
   - Detect via `original_content.count('\r\n')` vs `original_content.count('\n')`
   - Normalize new_content to match

4. **Empty ranges:**
   - `start_line == end_line`: Valid (single line edit)
   - `new_content == ""`: Valid (delete lines)

### Search/Replace
1. **Pattern not found:**
   - Return warning: "Pattern 'X' not found in file"
   - Mode handling:
     - strict: Error (no changes made)
     - interactive: Warning (file unchanged)

2. **Regex errors:**
   - Invalid pattern: Catch `re.error`, return validation error
   - Invalid replacement: Test replacement before applying

3. **Count limit edge cases:**
   - `count=0`: Valid (no replacements, but why?)
   - `count > matches`: Replace all matches (not an error)

4. **Multi-line patterns:**
   - Regex flag `re.MULTILINE` or `re.DOTALL`?
   - TBD: Add `multiline` flag to SearchReplace model

### Validation
1. **Large files:**
   - Line edit on 10,000 line file: Need to read/write entire file
   - Performance acceptable? (Python I/O is fast, validators are bottleneck)

2. **Binary files:**
   - Detect binary via file extension or content sniffing
   - Reject binary files explicitly

3. **File encoding:**
   - Assume UTF-8 (current behavior)
   - Handle encoding errors gracefully

### Atomicity
1. **Validation failure after file write:**
   - Current: File already written on validation failure in interactive mode
   - New: Must write file after validation passes (all modes)
   - Rollback: Keep original content backup, restore on failure

2. **Filesystem errors:**
   - Permission denied, disk full, file locked
   - Atomic writes: Use temp file + rename pattern

---

## Dependencies and Integration Points

### Internal Dependencies
- `mcp_server/tools/base.py`: BaseTool, ToolResult
- `mcp_server/validation/registry.py`: ValidatorRegistry
- `mcp_server/validation/python_validator.py`: PythonValidator
- `mcp_server/validation/markdown_validator.py`: MarkdownValidator
- `mcp_server/validation/template_validator.py`: TemplateValidator

### External Dependencies
- **difflib** (stdlib): Unified diff generation
- **re** (stdlib): Regex for search/replace
- **pathlib** (stdlib): File I/O

### No New Dependencies Required ✅

### Integration Points
1. **ValidatorRegistry:** No changes needed (still validates full content)
2. **MCP Server:** Tool already registered, input schema updates automatically
3. **Tests:** Existing test helpers (mock filesystem, validators) reusable

---

## Success Criteria

### Functional Requirements
✅ Line edits work for single and multiple ranges  
✅ Search/replace works with literal and regex patterns  
✅ Full content mode unchanged (backward compatible)  
✅ Unified diff preview generated for all modes  
✅ All validators run on final content (pylint/mypy/pyright)  
✅ Strict/interactive/verify_only modes work identically  
✅ Atomic operations: rollback on validation failure  

### Quality Gates
✅ 15+ unit tests covering all edit modes  
✅ Integration tests with real validators  
✅ Edge case tests (overlapping edits, regex errors, etc.)  
✅ Pylint 10/10  
✅ Mypy pass  
✅ Pyright pass  

### Performance
✅ Line edits on 1000-line file < 1 second  
✅ Search/replace with 100 matches < 1 second  
✅ Diff generation for 500-line change < 0.5 seconds  

### Documentation
✅ Updated tool description with examples  
✅ API documentation for new models  
✅ Migration guide (none needed - backward compatible)  

---

## Next Steps: Planning Phase

1. **API Finalization:**
   - Confirm LineEdit model fields
   - Confirm SearchReplace model fields (add multiline flag?)
   - Decide overlapping edit strategy (error vs sequential)

2. **Algorithm Design:**
   - Line edit application algorithm
   - Line number adjustment after edits
   - Search/replace with count limit logic

3. **Test Strategy:**
   - Test file structure (unit vs integration)
   - Mock filesystem vs real files
   - Validator mocking strategy

4. **Implementation Order:**
   - Phase 1: Diff preview (foundation)
   - Phase 2: Line edits
   - Phase 3: Search/replace
   - Phase 4: Integration and edge cases
