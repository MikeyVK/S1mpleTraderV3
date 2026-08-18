<!-- docs/development/issue433/planning.md -->
<!-- template=planning version=130ac5ea created=2026-07-21T11:34Z updated=2026-07-21T11:36Z -->
# Planning Document: Frictionless safe_edit_file with Clean Break

**Status:** APPROVED  
**Version:** 1.0.0  
**Last Updated:** 2026-07-21  

---

## 1. Summary

Implementation plan for refactoring `safe_edit_file` into a frictionless 4-operation tool (`replace`, `append`, `rewrite`, `pattern_replace`) with strict file existence enforcement (`must_exist=True`), generic `IAtomicFileWriter` protocol abstraction, `difflib` fuzzy-match diagnostics, and explicit hard-removal of all legacy line-number tests under the Approved Strategy (**Clean Break**).

---

## 2. TDD Cycles Breakdown

### Cycle 1: Schema & Abstractions (`C_SCHEMA.1`)

**Goal:** Establish `IAtomicFileWriter` protocol interface, concrete `AtomicFileWriter` utility, and 4-operation Pydantic models with `extra="forbid"`.

**Deliverables:**
- `DELIV_INTERFACE_FILE_WRITER_1`: `IAtomicFileWriter` protocol in `mcp_server/core/interfaces/file_writer.py` (and re-exported in `mcp_server/core/interfaces/__init__.py`).
- `DELIV_UTIL_ATOMIC_FILE_WRITER_1`: `AtomicFileWriter` implementation in `mcp_server/utils/atomic_file_writer.py` implementing `IAtomicFileWriter` with Windows permission retry logic.
- `DELIV_SCHEMA_SAFE_EDIT_INPUT_1`: 4-operation Pydantic models (`ReplaceOp`, `AppendOp`, `RewriteOp`, `PatternReplaceOp`, `OperationType` discriminated union, `SafeEditInput`) with `model_config = ConfigDict(extra="forbid")` in `mcp_server/tools/safe_edit_tool.py`.

**Affected Files:**
- `mcp_server/core/interfaces/file_writer.py` *(New)*
- `mcp_server/core/interfaces/__init__.py` *(Update re-exports)*
- `mcp_server/utils/atomic_file_writer.py` *(New)*
- `mcp_server/tools/safe_edit_tool.py` *(Refactor input models)*

**Tests:**
- `tests/mcp_server/unit/core/interfaces/test_file_writer_interface.py`
- `tests/mcp_server/unit/utils/test_atomic_file_writer.py`
- `tests/mcp_server/unit/tools/test_safe_edit_tool.py` (Schema discriminator tests)

**Success Criteria:**
- `IAtomicFileWriter` protocol defined with `@runtime_checkable` supporting `write_text` and `write_json`.
- `AtomicFileWriter` implements `IAtomicFileWriter` cleanly.
- `ReplaceOp`, `AppendOp`, `RewriteOp`, `PatternReplaceOp`, and `SafeEditInput` parse correctly and reject extra fields (`extra="forbid"`).

---

### Cycle 2: Execution Logic & Governance (`C_EXECUTE.2`)

**Goal:** Implement `SafeEditTool` execution handlers (`_generate_new_content`), `must_exist=True` governance enforcement, `difflib` fuzzy-match diagnostics, and atomic writer integration.

**Deliverables:**
- `DELIV_EXECUTE_CONTENT_GEN_2`: Pure query transformation `_generate_new_content(original_text, operation)` handling `ReplaceOp`, `AppendOp`, `RewriteOp`, `PatternReplaceOp`.
- `DELIV_GOVERNANCE_FILE_EXISTENCE_2`: Governance check ensuring target path exists (`must_exist=True`), returning clear rejection message if file is missing (directing caller to `scaffold_artifact`).
- `DELIV_DIAGNOSTIC_FUZZY_MATCH_2`: `difflib.SequenceMatcher` integration in `_find_fuzzy_matches` to suggest close matching strings when `target_content` is not found.
- `DELIV_TOOL_ATOMIC_WRITER_INTEGRATION_2`: Updated `SafeEditTool.__init__` accepting injected `IAtomicFileWriter` and `ValidationService`, replacing raw `Path.write_text()` with atomic temp-swap file write under mutex lock.

**Affected Files:**
- `mcp_server/tools/safe_edit_tool.py` *(Refactor handlers & execution logic)*

**Tests:**
- `tests/mcp_server/unit/tools/test_safe_edit_tool.py` (Execution & governance handler tests)

**Success Criteria:**
- All 4 operations execute cleanly in pure CQS query transformer without side effects.
- Non-existent file path rejected with governance error directing caller to `scaffold_artifact`.
- Fuzzy-match diagnostics return actionable line suggestions on target mismatch.
- File writing uses `file_writer.write_text(...)` atomically under `asyncio.Lock`.

---

### Cycle 3: Test Suite Alignment & Legacy Cleanup (`C_INTEGRATION.3`)

**Goal:** Update unit and integration test suites, refactor validation integration tests, and perform explicit hard-removal of all legacy line-number test cases.

**Deliverables:**
- `DELIV_TEST_SAFE_EDIT_UNIT_3`: Updated unit tests in `tests/mcp_server/unit/tools/test_safe_edit_tool.py` covering all 4 operations, governance checks, fuzzy matching, and atomic writing.
- `DELIV_TEST_EXTRA_FORBID_3`: Updated schema tests in `tests/mcp_server/unit/tools/test_extra_forbid.py` testing `extra="forbid"` on `ReplaceOp`, `AppendOp`, `RewriteOp`, `PatternReplaceOp`, and `SafeEditInput`.
- `DELIV_TEST_VALIDATION_INTEGRATION_3`: Refactored integration tests in `tests/mcp_server/integration/mcp_server/validation/test_safe_edit_validation_integration.py` transitioning test cases to use the 4-operation schema.
- `DELIV_TEST_CLEANUP_LEGACY_3`: Explicit hard-removal of all legacy line-number and line-edit test methods (`test_line_edits`, `test_insert_lines`, legacy bounds-checking tests) across all test files. No skipped or commented-out legacy tests allowed.

**Affected Files:**
- `tests/mcp_server/unit/tools/test_safe_edit_tool.py` *(Update test cases & purge legacy tests)*
- `tests/mcp_server/unit/tools/test_extra_forbid.py` *(Update nested extra forbid tests)*
- `tests/mcp_server/integration/mcp_server/validation/test_safe_edit_validation_integration.py` *(Update input schemas)*

**Tests:**
- Full test suite run (`run_tests`).

**Success Criteria:**
- 100% test pass rate across all unit and integration suites.
- All legacy `line_edits` and `insert_lines` test methods hard-removed.
- 0 typing errors (Pyright & Mypy clean).
- Pylint score 10.00/10 compliance.

---

## 3. Obligations & Governance Checklist

### Typing Obligations
- Protocol `IAtomicFileWriter` marked `@runtime_checkable`.
- Discriminated union `OperationType` typed via `Annotated[Union[...], Field(discriminator="op")]`.
- Zero `cast` or `# type: ignore` directives added.

### Quality Gate Obligations
- Run `run_quality_gates` before phase transitions.
- Pylint score 10.00/10 + 0 Pyright / Mypy errors required.

---

## Related Documentation
- [Design Document](file:///c:/temp/pgmcp/docs/development/issue433/design.md)
- [Research Document](file:///c:/temp/pgmcp/docs/development/issue433/research.md)
- [Architecture Principles](file:///c:/temp/pgmcp/docs/coding_standards/ARCHITECTURE_PRINCIPLES.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-07-21 | @imp | Complete planning document with 3 sequential cycles and explicit legacy test cleanup |
