<!-- docs/development/issue125/design.md -->
<!-- template=design version=5827e841 created=2026-02-08T14:30:00+01:00 updated= -->
# Safe Edit Tool Improvements Design

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-08

---

## Purpose

Design error context enhancement and duplicate output fix for safe_edit_file tool

## Scope

**In Scope:**
['Error context preview design', 'File preview helper implementation', 'Duplicate output investigation approach', 'Test strategy for improvements']

**Out of Scope:**
['Full whitespace normalization design', 'Validation framework changes', 'Performance optimization', 'Alternative editing modes']

## Prerequisites

Read these first:
1. Research phase findings
2. bugtracking.md analysis
3. Understanding of safe_edit_tool architecture
---

## 1. Context & Requirements

### 1.1. Problem Statement

safe_edit_file tool exhibits two issues: (1) reported duplicate output when using line_edits mode (not reproduced in tests), and (2) insufficient error context when patterns are not found, leading to high agent retry rates. Initial investigation shows error context is implementable as a quick win, while duplicate bug needs further analysis and whitespace normalization exceeds quick wins scope.

### 1.2. Requirements

**Functional:**
- [ ] FR1: Pattern-not-found errors include first 10 lines of file with line numbers
- [ ] FR2: File preview helper reusable across error scenarios
- [ ] FR3: No duplicate output in diff or validation messages
- [ ] FR4: All existing edit modes (content, line_edits, insert_lines, search_replace) continue working

**Non-Functional:**
- [ ] NFR1: 10/10 pylint score maintained
- [ ] NFR2: DRY/SRP compliance per coding standards
- [ ] NFR3: No performance degradation (< 1ms overhead for preview)
- [ ] NFR4: Backward compatible with existing tool calls

### 1.3. Constraints

['Must maintain 10/10 pylint score', 'DRY/SRP compliance from coding standards', 'No breaking changes to public API', 'Backward compatible with existing tool calls']
---

## 2. Design Options

### 2.1. Option A: Error Context via File Preview



**Pros:**
- ✅ Reduces agent retry rate
- ✅ Simple implementation
- ✅ Reusable across error paths

**Cons:**
- ❌ Adds ~100 bytes to error messages
- ❌ Limited to first N lines

### 2.2. Option B: Whitespace Normalization via Regex



**Pros:**
- ✅ Fast
- ✅ Simple

**Cons:**
- ❌ Breaks syntax
- ❌ Unsafe for general use

### 2.3. Option C: Whitespace Normalization via AST



**Pros:**
- ✅ Syntax-aware
- ✅ Safe

**Cons:**
- ❌ Complex
- ❌ Language-specific
- ❌ 30-44h effort
---

## 3. Chosen Design

**Decision:** Ship error context enhancement (Priority 1) and no-duplicate guarantee tests (Priority 2); defer whitespace normalization to future issue

**Rationale:** Error context enhancement directly reduces agent retry rate (67% improvement target from Issue #121). No-duplicate regression tests provide ongoing protection even if bug is environmental. Whitespace normalization requires AST-level work incompatible with quick wins timeline, so defer with regex workaround available.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
|  |  |
|  |  |
|  |  |
|  |  |

---
## 4. Open Questions

| Question | Options | Status |
|----------|---------|--------|
| Is the duplicate bug environmental or version-specific? |  |  |
| Should preview line count be configurable? |  |  |
| Can we detect common pattern mistakes proactively? |  |  |
## Related Documentation
- **[docs/development/issue125/research.md][related-1]**
- **[docs/development/issue125/planning.md][related-2]**
- **[docs/development/issue125/bugtracking.md][related-3]**
- **[mcp_server/tools/safe_edit_tool.py][related-4]**

<!-- Link definitions -->

[related-1]: docs/development/issue125/research.md
[related-2]: docs/development/issue125/planning.md
[related-3]: docs/development/issue125/bugtracking.md
[related-4]: mcp_server/tools/safe_edit_tool.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-08 | Agent | Initial draft |