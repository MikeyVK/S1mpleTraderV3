# Bug Tracking - Issue #125 Safe Edit Improvements

## Bugs Found During Implementation

### 1. **safe_edit_file produces duplicate lines** (META-BUG)
**Location:** Line edit operations in safe_edit_tool.py  
**Symptom:** When using `line_edits` mode, sometimes duplicate lines appear (e.g., two identical `return ToolResult.error(...)` statements)  
**Example:**
```python
# After edit:
return ToolResult.error(f"Search/replace failed: {e}")
return ToolResult.error(f"Search/replace failed: {e}")  # DUPLICATE
```
**Impact:** HIGH - The tool we're fixing has its own bugs!  
**Root Cause:** Likely in `_apply_line_edits` logic around line overlap detection or replacement  
**Status:** OBSERVED, needs investigation  
**Occurrences:** 
- First: Line 247 duplicate `return ToolResult.error(...)`
- Second: Line 242-247 duplicate `return new_content` + exception handler  
**Pattern:** Seems to happen when replacing multi-line blocks with line_edits mode
**Note:** Test also passed ValidationError when using undefined `normalize_whitespace` param (Pydantic should reject!)

### 2. **Whitespace normalization logic bug**
**Location:** `_apply_search_replace_flat` lines 407-440  
**Symptom:** Word-based splitting breaks on `"def foo(x, y):"` → `['def', 'foo(x,', 'y):']`  
**Impact:** MEDIUM - Feature doesn't work as intended  
**Root Cause:** Using `.split()` which splits on ALL whitespace, breaking syntax  
**Fix:** Use regex `\s+` replacement instead of word-based matching

---

## Priority 1: Duplicate Output Bug
**Status:** ✅ NOT FOUND - Test confirms no duplicates in current code  
**Test Added:** `test_no_duplicate_diff_in_response`, `test_no_duplicate_real_validation`

## Priority 2: Error Context
**Status:** ✅ IMPLEMENTED  
**Change:** Pattern not found now shows first 10 lines of file  
**Test Added:** `test_pattern_not_found_shows_context`

## Priority 3: Whitespace Normalization
**Status:** ⏸️ DEFERRED (complexity > quick wins scope)  
**Reason:** Whitespace inside syntax (e.g., `foo( x, y )` vs `foo(x, y)`) requires AST-level parsing, not simple regex collapse  
**Alternative:** User can use regex mode with `\s+` patterns for flexible matching  
**Test:** `test_whitespace_normalization` exists but feature incomplete

---

## Notes
- Started: Issue #125 investigation
- Branch: feature/125-safe-edit-improvements
- TDD Protocol: RED-GREEN-REFACTOR with commits per phase
