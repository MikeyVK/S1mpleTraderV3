<!-- docs/development/issue433/research.md -->
<!-- template=research version=8b7bb3ab created=2026-07-21T08:51Z updated=2026-07-21T08:52Z -->
# Research Report: Structurally Aware Append in safe_edit_file

**Status:** APPROVED  
**Version:** 1.0.0  
**Last Updated:** 2026-07-21  

---

## Problem Statement

The `safe_edit_file` tool currently requires rigid numeric line indices (`line_edits` with `start_line`/`end_line`, `insert_lines` with `at_line: int`), forcing AI agents to manually calculate line counts (`total_lines + 1`) when appending or editing code. LLMs tokenize text in chunks rather than counting lines, leading to frequent out-of-bounds `ValueError` exceptions and accidental line overwrites when line counts shift during multi-step edits.

To eliminate AI editing friction, `safe_edit_file` must be refactored into a frictionless, string-anchored editing primitive while retaining its unique platform capabilities.

### Rationale for Scope Expansion

While Issue #433 originated from a deferred finding in Issue #429 regarding `insert_lines` line-counting errors during appends, limiting the solution to a narrow "append flag" would leave the broader friction of rigid numeric line indexing (`line_edits`) intact across the rest of the tool. 

Analyzing industry prior art (Claude Code `str_replace_editor`, Antigravity `replace_file_content`, Aider diff blocks) demonstrated that AI agents achieve significantly higher edit reliability (>90%) when using string-anchored and symbol-anchored operations rather than counting line numbers. Broadening the scope to refactor `safe_edit_file` into a unified, frictionless editing tool eliminates line-counting friction entirely while providing unique platform value-adds (AST/template validation gates, atomic I/O, mutex locking, and fuzzy-match diagnostic suggestions).
---

## Research Goals

1. Eliminate numeric line-counting friction for AI agent file edits.
2. Introduce frictionless string-anchored and symbol-anchored edit operations (`replace`, `append`, `rewrite`, `pattern_replace`).
3. Maintain and enhance the unique value-adds of `phase-gate-mcp`: Python AST and template syntax validation gates (`strict` / `interactive` / `verify_only`), atomic file I/O, per-file mutex locks, and fuzzy-match diagnostic feedback.
4. Verify compliance with all core architectural principles in `ARCHITECTURE_PRINCIPLES.md` (SOLID, CQS, Value Objects `extra="forbid"`, Fail-Fast).

---

## Background & Prior Art Analysis

Industry analysis of AI coding assistants (Claude Code `str_replace_editor`, Antigravity `replace_file_content`, Aider diff blocks) demonstrates that string-anchored editing (`target_content` → `replacement`) achieves >90% success rates compared to ~60% for numeric line indexing.

| Feature | Standard Built-in Tools | `safe_edit_file` (Refactored) |
|:---|:---|:---|
| **String-Anchored Editing** | Yes (`TargetContent` / `old_string`) | **Yes (`target_content` → `replacement`)** |
| **Frictionless Append to EOF** | Requires line counting | **Yes (`append` with `content`)** |
| **Anchor-Relative Insertion** | No | **Yes (`anchor: "text"`, `position: "before" \| "after"`)** |
| **AST & Syntax Validation Gate** | No (blind file write) | **Yes (`strict` / `interactive` validation)** |
| **Atomic File I/O & Mutex Lock** | No | **Yes (Atomic temp-swap & Lock)** |
| **Fuzzy-Match Diagnostic Suggestions** | No ("Not found") | **Yes (Suggests nearest line snippet on typos)** |

---

## Technical Audit & Affected Surface

### Production Code
- `mcp_server/tools/safe_edit_tool.py`:
  - `SafeEditInput`: Refactor Pydantic input models to support `replace`, `append`, `rewrite`, and `pattern_replace` with `extra="forbid"`.
  - `SafeEditTool`: Refactor handlers to process string-anchored replacements, EOF/anchor appends, and fuzzy-match diagnostics.
- `mcp_server/schemas/tool_outputs.py`: `SafeEditOutput` DTO.

### Test Suites & Fixtures
- `tests/mcp_server/unit/tools/test_safe_edit_tool.py`: Update unit tests to verify the refactored operations and fuzzy-match diagnostics.
- `tests/mcp_server/unit/tools/test_extra_forbid.py`: Update `test_safe_edit_nested_extra_forbid` schema checks.
- `tests/mcp_server/integration/mcp_server/validation/test_safe_edit_validation_integration.py`: Update integration test suite.

---

## Architectural Principles Toetics (`ARCHITECTURE_PRINCIPLES.md`)

- **SRP (1.1)**: `SafeEditTool` isolates tool execution; transformation logic is isolated in pure content generators; validation is delegated to `ValidationService`.
- **OCP (1.2)**: `SafeEditInput` uses Pydantic discriminator validation for operations.
- **ISP (1.4) & DIP (1.5)**: `ValidationService` and `AtomicJsonWriter` dependencies injected via constructor.
- **CQS (5.0)**: Inhoudstransformatie (`_generate_new_content`) and validation (`_validate`) are pure queries; file writes occur atomically at the end.
- **Value Objects (5.0 & 12)**: `SafeEditInput` enforces `model_config = ConfigDict(extra="forbid")`.

---

## Approved Strategy

- **Affected Boundary**: `mcp_server/tools/safe_edit_tool.py` (`SafeEditInput`, `SafeEditTool`).
- **Selected Strategy**: **Clean Break** (Direct in-place refactor of `SafeEditInput` and `SafeEditTool` to the new frictionless operation model without preserving legacy line-number parameters or introducing temporary dual-tool shims).
- **Rationale**: Removes legacy line-number friction completely in a single PR, ensuring zero legacy debt or ambiguity for AI callers while preserving the exact tool interface name and server registration.

---

## Expected Results

1. `safe_edit_file` operates without requiring numeric line counts or line measurement.
2. Callers can replace target content, append to EOF, insert relative to text anchors, or rewrite files seamlessly.
3. Syntax validation (`strict`/`interactive`), atomic writes, mutex locks, and fuzzy-match typo diagnostics function reliably.
4. All unit and integration test suites pass with 100% quality gate compliance.

---

## Related Documentation
- [Safe Edit Tool Finding (Issue #429)](file:///c:/temp/pgmcp/docs/development/issue429/safe_edit_tool_finding.md)
- [Architecture Principles](file:///c:/temp/pgmcp/docs/coding_standards/ARCHITECTURE_PRINCIPLES.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-07-21 | @imp | Complete evidence-backed research report with Approved Strategy: Clean Break |
