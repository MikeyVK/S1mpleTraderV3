<!-- docs/development/issue132/pre-research.md -->
<!-- template=design version=5827e841 created=2026-02-12 updated= -->
# issue132-shared-formatting-pre-research

**Status:** pre-research  
**Version:** 1.0  
**Last Updated:** 2026-02-12

---

## Scope

**In Scope:**
['Python file formatting via Ruff', 'Integration with scaffold/create/edit tools', 'Rollback mechanism', 'Optional tool exposure']

**Out of Scope:**
['Markdown/YAML formatters (future)', 'Custom formatting rules beyond Ruff', 'Pre-commit hook integration', 'IDE integration']

---

## 1. Context & Requirements

### 1.1. Problem Statement

Formatting is currently handled separately from file operations, causing agent workflows to require 4+ tool calls per edit (write → validate → fix formatting → validate again). This creates friction and inconsistency across scaffold/create/edit operations.

### 1.2. Requirements

**Functional:**
- [ ] Service detects file type and applies appropriate formatter
- [ ] All file-writing tools (scaffold_artifact, create_file, safe_edit_file) support autoformat parameter
- [ ] Formatting failures trigger automatic rollback to original file state
- [ ] Service returns detailed FormatResult with changes summary
- [ ] Optional format_file MCP tool for explicit formatting
- [ ] Support Ruff formatter for Python files

**Non-Functional:**
- [ ] Formatting must complete in <500ms for typical files
- [ ] Rollback must be atomic (no partial writes)
- [ ] Service must be unit-testable without MCP runtime
- [ ] Formatting errors must provide actionable error messages
- [ ] Configuration via pyproject.toml (standard Python tooling)

### 1.3. Constraints

None
---

## 2. Design Options

### 2.1. Option A: Option 1: Embed formatting in each tool



**Pros:**
- ✅ Simple
- ✅ No shared dependencies

**Cons:**
- ❌ Code duplication
- ❌ Inconsistent behavior
- ❌ Violates DRY/SRP

### 2.2. Option B: Option 2: Shared FileFormattingService (SELECTED)



**Pros:**
- ✅ DRY/SRP compliant
- ✅ Testable
- ✅ Consistent
- ✅ Extensible

**Cons:**
- ❌ Extra service layer
- ❌ Slightly more complex

### 2.3. Option C: Option 3: Autofix in quality gates



**Pros:**
- ✅ Centralized validation + fixing

**Cons:**
- ❌ Breaks read-only validation principle
- ❌ Multiple tool calls needed
---

## 3. Chosen Design

**Decision:** Implement shared FileFormattingService used by all file-writing tools with opt-in/out autoformat parameter

**Rationale:** By integrating formatting directly into file-writing tools via a shared service, we achieve atomic operations (write + format = 1 transaction), reduce tool call overhead by 75%, and ensure consistent formatting across all file operations. The shared service pattern maintains SRP/DRY principles while remaining testable and extensible.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
|  |  |
|  |  |
|  |  |
|  |  |
|  |  |

---
## 4. Open Questions

| Question | Options | Status |
|----------|---------|--------|
| Should formatting be configurable per-tool or globally? |  |  |
| How to handle formatting conflicts with existing code style? |  |  |
| Should we support custom formatter plugins? |  |  |
## Related Documentation
- **[docs/coding_standards/CODE_STYLE.md][related-1]**
- **[docs/coding_standards/QUALITY_GATES.md][related-2]**
- **[.st3/quality.yaml][related-3]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/CODE_STYLE.md
[related-2]: docs/coding_standards/QUALITY_GATES.md
[related-3]: .st3/quality.yaml

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |