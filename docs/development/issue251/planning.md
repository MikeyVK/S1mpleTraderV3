<!-- docs\development\issue251\planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-22T20:21Z updated=2026-02-22T21:05Z -->
# Issue #251: Refactor run_quality_gates — Scope-Driven Architecture, Config-Driven Parsing, ViolationDTO

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-02-22

---

## Purpose

Define a design-ready, atomic TDD plan for Issue #251 that fully aligns with research v1.6 and resolves all 15 findings without backward-compatibility constraints.

## Scope

**In Scope:**
- `mcp_server/managers/qa_manager.py`
- `mcp_server/tools/quality_tools.py`
- `mcp_server/config/quality_config.py`
- `.st3/quality.yaml`
- `.st3/state.json` (quality_gates state section)
- `mcp_server/tools/test_tools.py` (summary line follow-up)
- `tests/mcp_server/`

**Out of Scope:**
- CI/CD pipeline changes
- Non-Python gate execution
- pyproject-wide test strategy migration
- Frontend/UI changes
- `docs/coding_standards/QUALITY_GATES.md` update (documentation phase deliverable)

## Prerequisites

1. Research document complete: [research.md](research.md) v1.6
2. Current workflow phase is `planning`
3. Design decisions are locked (no backward compatibility for removed API)

---

## Summary

This plan refactors `run_quality_gates` into a scope-driven and config-driven architecture:
- Remove Gate 5/6 (pytest/coverage) from quality gates and keep tests in `run_tests`
- Replace `files` API with `scope: auto|branch|project`
- Replace tool-specific parsing with strategy-based `json_violations` and `text_violations`
- Standardize violations through `ViolationDTO`
- Introduce baseline state machine (`baseline_sha`, `failed_files`) for `auto` scope
- Return exactly two MCP content items in fixed order: text summary first, JSON payload second

---

## Dependency Graph (Corrected)

- **C0 has no dependencies** and should run first to unblock the TDD suite.
- Foundation contracts must exist first: C1–C6
- Parser implementation depends on foundation: C7–C14 depend on C1–C6
- Baseline state machine must exist before auto-scope: C19–C20 before C23–C24
- Scope resolution uses project scope model from C3: C21–C24 depend on C3
- Output model depends on parser output contract: C25–C27 depend on C7–C14
- Tool API switch depends on scope resolution and output contract: C28 depends on C21–C27
- Config migrations are split and can run after model contracts: C30–C31 depend on C2/C5
- `run_tests` summary follow-up is independent: C29

---

## TDD Execution Rules

Applies to all cycles in this plan:

1. **RED is for behavior, not mechanics.** Deletion, renaming, and pure file moves do not require a new failing unit test. Proof for those cycles is regression (no previously green test breaks) plus any contract test that would detect a behavioral regression.

2. **Deletion/refactor cycles prove via regression + contract.** Run the existing passing test suite after removal. Add a contract test only if a specific guarantee needs hardening (for example, "method no longer exists" or "field is absent from output").

3. **Minimum evidence.** One failing test per new or changed behavior path is sufficient to start a GREEN phase. Expand only for genuine risk: edge paths (empty inputs, boundary conditions) and error paths (exceptions, subprocess failures). One test per mechanism, not one test per line.

4. **Stop rule.** Do not add a test if it covers no new failure mechanism. If GREEN already handles all reachable paths that the proposed test exercises, stop.

---

## TDD Cycles

Each cycle is atomic: one observable behavior, one parser concern, or one API concern.

### Cluster 0 — Pre-flight Config Preparation

### Cycle 0: Remove gate5_tests and gate6_coverage from active_gates (quality.yaml)

**Goal:** Before any code changes, eliminate the root cause of the "system pytest" exit-code-4 bug (F1/F10) by removing the two broken gate entries from the active gate list. This unblocks the rest of the TDD run because the test suite itself will no longer invoke a broken pytest gate.

**Note:** This is a pure config change; no production Python code is modified in this cycle.

**RED:** No new unit test required. The existing regression suite must be green after the change. Write one config-contract test: the active gates list loaded from `.st3/quality.yaml` must not contain `gate5_tests` or `gate6_coverage`.

**GREEN:**
- Set the gate activation config in `.st3/quality.yaml` to include only the static analysis gates (0–4b).
- Remove or comment out `gate5_tests` and `gate6_coverage` entries.

**REFACTOR:** Verify that removing these entries produces no schema validation warnings from `QualityConfig.model_validate`.

**Exit Criteria:** Config contract test passes; `run_quality_gates()` completes without attempting to invoke pytest.

---

### Cluster A — Foundation Contracts

### Cycle 1: Add ViolationDTO dataclass

**Goal:** Create a single violation contract consumed by all gates.

**RED:** Test object creation with required and optional fields.

**GREEN:** Add `ViolationDTO` dataclass with fields: `file`, `message`, `line`, `col`, `rule`, `fixable`, `severity`.

**REFACTOR:** Add concise class docstring and keep defaults explicit.

**Exit Criteria:** Unit test passes; no type errors.

---

### Cycle 2: Add JsonViolationsParsing model

**Goal:** Introduce explicit JSON parsing strategy model.

**RED:** Validate model accepts `field_map`, `violations_path`, `line_offset`, `fixable_when`.

**GREEN:** Add `JsonViolationsParsing` Pydantic model.

**REFACTOR:** Normalize defaults and optional typing.

**Exit Criteria:** Validation tests pass for ruff and pyright schema variants.

---

### Cycle 3: Add project_scope to QualityConfig

**Goal:** Make project-level scope declarative in config.

**RED:** Validate config loads with `project_scope.include_globs`.

**GREEN:** Add `project_scope: GateScope | None` to `QualityConfig`.

**REFACTOR:** Ensure required/optional boundary is explicit.

**Exit Criteria:** Config model validation passes with and without project_scope.

---

### Cycle 4: Remove produces_json capability flag

**Goal:** Remove implicit parser coupling.

**RED:** Existing tests expecting `produces_json` fail.

**GREEN:** Delete `produces_json` from capability metadata and usages.

**REFACTOR:** Remove obsolete references in code/tests.

**Exit Criteria:** Codebase has zero `produces_json` references.

---

### Cycle 5: Add TextViolationsParsing model

**Goal:** Introduce explicit text parsing strategy model.

**RED:** Validate model accepts regex pattern, defaults, severity default.

**GREEN:** Add `TextViolationsParsing` model.

**REFACTOR:** Keep model minimal and deterministic.

**Exit Criteria:** Validation tests for model construction pass.

---

### Cycle 6: Validate defaults field interpolation

**Goal:** Enforce `{field}` placeholders in defaults reference known capture groups.

**RED:** Invalid placeholder test fails validation.

**GREEN:** Add model validator for placeholder checking.

**REFACTOR:** Keep error message actionable and specific.

**Exit Criteria:** Unknown placeholder raises clear validation error.

---

### Cluster B — Parser Engine in QAManager

### Cycle 7: Implement _parse_json_violations for root-array JSON

**Goal:** Parse ruff-style root-array JSON into `ViolationDTO`.

**RED:** Failing test for root-array + field_map mapping.

**GREEN:** Implement `_parse_json_violations` happy path.

**REFACTOR:** Extract simple mapping helper if needed.

**Exit Criteria:** Ruff-like sample converts to expected DTO list.

---

### Cycle 8: Add dotted-path extraction helper

**Goal:** Support nested fields like `range.start.line`.

**RED:** Test nested field lookup fails.

**GREEN:** Add helper to resolve dotted key path in dict payloads.

**REFACTOR:** Handle missing path safely (`None` return).

**Exit Criteria:** Nested pyright fields resolve correctly.

---

### Cycle 9: Add violations_path extraction for nested arrays

**Goal:** Support payload arrays under a configured top-level path.

**RED:** `generalDiagnostics` extraction test fails.

**GREEN:** Resolve `violations_path` before field mapping.

**REFACTOR:** Keep extraction reusable and side-effect free.

**Exit Criteria:** Pyright-like payload produces DTO list from nested array.

---

### Cycle 10: Apply line_offset and fixable_when in JSON parser

**Goal:** Support 0/1-based line normalization and computed fixable status.

**RED:** Failing tests for offset and fixability.

**GREEN:** Apply offset to mapped line and boolean from `fixable_when`.

**REFACTOR:** Guard against missing or non-int line values.

**Exit Criteria:** Parser returns expected normalized line and fixable flag.

---

### Cycle 11: Implement _parse_text_violations for named-group regex

**Goal:** Parse mypy-style text into `ViolationDTO`.

**RED:** Failing test for file/line/severity/message extraction.

**GREEN:** Implement text parser using regex named groups.

**REFACTOR:** Return empty list on no matches.

**Exit Criteria:** Mypy-style line parses into one DTO.

---

### Cycle 12: Apply defaults interpolation in text parser

**Goal:** Fill missing fields (for example format-fix message) via defaults.

**RED:** `{file}` interpolation test fails.

**GREEN:** Merge named groups with interpolated defaults.

**REFACTOR:** Keep merge order deterministic (groups first, defaults override only where configured).

**Exit Criteria:** Ruff-format line yields configured default message with interpolated file.

---

### Cycle 13: Switch execute_gate dispatch to parsing_strategy

**Goal:** Remove gate-name branching and dispatch only by strategy.

**RED:** Integration test fails when strategy-based dispatch not used.

**GREEN:** Add `match/case` on `json_violations` vs `text_violations`.

**REFACTOR:** Centralize parser selection in one branch point.

**Exit Criteria:** execute_gate parses via strategy without gate-name checks.

---

### Cycle 14: Remove legacy parser methods and parser branches

**Goal:** Delete `_parse_ruff_json`, `_parse_json_field_issues`, and obsolete parser branch paths.

**RED:** Tests still referencing legacy methods fail.

**GREEN:** Remove methods and update tests to new strategy parser.

**REFACTOR:** Verify no dead branches remain.

**Exit Criteria:** Zero references to removed parser methods in codebase.

---

### Cluster C — File Selection Cleanup

### Cycle 15: Add _files_for_gate based on file_types

**Goal:** Replace hardcoded extension filtering with declarative gate capability filtering.

**RED:** Mixed-extension test fails for gate-specific filtering.

**GREEN:** Implement `_files_for_gate(gate, files)` using `file_types`.

**REFACTOR:** Preserve stable ordering.

**Exit Criteria:** Filtering respects each gate’s configured file types.

---

### Cycle 16: Remove _filter_files

**Goal:** Remove hardcoded global `.py` filter.

**RED:** Reference test confirms method still exists.

**GREEN:** Delete method and update call sites.

**REFACTOR:** Keep only one filtering path.

**Exit Criteria:** `_filter_files` no longer exists and tests pass.

---

### Cycle 17: Remove pytest-specific helper methods

**Goal:** Remove dead pytest gate helpers from quality manager.

**RED:** Legacy helper existence test fails.

**GREEN:** Delete helper methods tied to pytest gate behavior.

**REFACTOR:** Remove related stale tests and fixtures.

**Exit Criteria:** No pytest helper methods remain in qa manager.

---

### Cycle 18: Remove mode bifurcation block (is_file_specific_mode)

**Goal:** Eliminate old dual execution mode based on files param.

**RED:** Test expecting old mode branch fails.

**GREEN:** Remove mode bifurcation; route through scope resolution only.

**REFACTOR:** Simplify run path to one flow.

**Exit Criteria:** Single execution path remains for all scopes.

---

### Cluster D — Baseline State and Scope Resolution

### Cycle 19: Baseline advance on all-pass

**Goal:** When all gates pass, persist current HEAD as `baseline_sha` and reset `failed_files`.

**RED:** State update test fails for pass-only run.

**GREEN:** Implement all-pass baseline update logic.

**REFACTOR:** Use one state update helper.

**Exit Criteria:** State contains new baseline SHA and empty failed files list.

---

### Cycle 20: Failure accumulation for failed_files

**Goal:** Union newly failed files with persisted failed file set.

**RED:** Existing failed file set overwritten instead of merged.

**GREEN:** Implement set union and deterministic sort.

**REFACTOR:** Keep baseline_sha unchanged on failure.

**Exit Criteria:** failed_files equals union of old and new failures.

---

### Cycle 21: Resolve scope=project from project_scope globs

**Goal:** Expand include globs from config into candidate files.

**RED:** Project scope returns empty when globs exist.

**GREEN:** Implement project scope expansion against workspace root.

**REFACTOR:** Deduplicate and normalize paths.

**Exit Criteria:** scope=project returns expected Python file set.

---

### Cycle 22: Resolve scope=branch using git diff parent..HEAD

**Goal:** Build candidate files from branch diff.

**RED:** Branch scope test fails to collect changed files.

**GREEN:** Implement git diff collection with parent fallback.

**REFACTOR:** Add subprocess error guard and empty-output handling.

**Exit Criteria:** scope=branch returns changed files from diff output.

---

### Cycle 23: Resolve scope=auto happy path (baseline present)

**Goal:** Return union of diff files (`baseline_sha..HEAD`) and persisted `failed_files`.

**RED:** Auto scope ignores failed_files or diff.

**GREEN:** Implement union logic.

**REFACTOR:** Extract reusable git-diff helper.

**Exit Criteria:** scope=auto returns exact union set.

---

### Cycle 24: Resolve scope=auto edge cases

**Goal:** Handle no-baseline and empty-change behavior.

**RED:** No baseline does not fallback to project scope.

**GREEN:** Add two guards:
- no baseline → fallback to project scope
- no diff and no failed files → return empty list early

**REFACTOR:** Ensure no recursive auto-calls.

**Exit Criteria:** Both edge-case tests pass.

---

### Cluster E — Output Contract

### Cycle 25: Add summary_line formatter

**Goal:** Produce a concise status line for pass/fail/skip outcomes.

**RED:** Formatter tests fail for pass, fail, and skip variants.

**GREEN:** Implement `_format_summary_line(gate_results)`.

**REFACTOR:** Keep message stable and deterministic for tests.

**Exit Criteria:** Formatter tests pass for all three scenarios.

---

### Cycle 26: Build compact JSON payload

**Goal:** Return compact gate payload with violations only (no debug/raw fields).

**RED:** Payload test still includes debug fields.

**GREEN:** Implement compact payload builder with per-gate violations list.

**REFACTOR:** Ensure payload schema is stable for clients.

**Exit Criteria:** Payload contains only agreed schema fields.

---

### Cycle 27: Normalize ToolResult content contract

**Goal:** Enforce exactly two content items in fixed order:
1. text summary
2. json payload

**RED:** Contract test fails when second item is not JSON, or when more than two content items are present.

**GREEN:** Return exactly two content items in this fixed order:
1. `{"type": "text", "text": <summary_line>}` — human-readable status line
2. `{"type": "json", "json": <compact_payload>}` — structured gate results

Use whatever concrete types the existing ToolResult/content pattern requires; the contract is the order and count, not the class names.

**REFACTOR:** Remove any additional serialization branch that produces a third content item or duplicated JSON.

**Exit Criteria:** Tool response always has exactly two items; item 0 is text; item 1 is json.

---

### Cluster F — Tool API and Follow-up

### Cycle 28: Replace files API with scope API in RunQualityGatesTool

**Goal:** Public tool signature becomes `scope: Literal["auto", "branch", "project"] = "auto"`.

**RED:** Old files-based API tests fail.

**GREEN:** Update tool signature and internal call flow.

**REFACTOR:** Update tool schema/docs used by MCP routing.

**Exit Criteria:** Scope API works; files API no longer accepted.

---

### Cycle 29: Invert run_tests content order (contract change)

> ⚠️ **Contract Change:** Current implementation ([test_tools.py, ~L207](../../../mcp_server/tools/test_tools.py)) returns JSON first, summary text second:
> ```
> content=[{"type": "json", ...}, {"type": "text", text=summary_line}]
> ```
> This cycle inverts that order to match the quality gates contract: **text first, json second**.

**Goal:** Align `run_tests` output order with the `run_quality_gates` contract so callers can rely on `content[0]` being the human-readable summary in both tools.

**RED:** Write a test asserting `content[0].type == "text"` against the current implementation — this must fail to confirm the contract inversion is actually needed.

**GREEN:** In `test_tools.py`: move summary construction before the JSON payload and reorder the content list so the summary line comes first.

**REFACTOR:** Keep pytest output parsing isolated; only the content assembly order changes.

**Exit Criteria:** `content[0]` is the summary text and `content[1]` is the JSON payload; existing callers that relied on `content[1]` for summary must be updated.

---

### Cycle 30: quality.yaml gate activation + project_scope migration

**Goal:** Update gate activation and project scope in config.

**RED:** Config test fails if gate5/gate6 still active or project_scope missing.

**GREEN:**
- Remove `gate5_tests` and `gate6_coverage` from `active_gates`
- Add `project_scope.include_globs`

**REFACTOR:** Keep config readable and grouped by concern.

**Exit Criteria:** Config validation passes and active gates match design.

---

### Cycle 31: quality.yaml parsing strategy migration

**Goal:** Migrate gate parsing blocks from old forms to explicit strategy forms.

**RED:** Validation fails when old `json_field`/`text_regex` blocks remain.

**GREEN:**
- Replace old JSON parsing blocks with `json_violations`
- Replace old text parsing blocks with `text_violations`
- Add Gate 0 default fix message with `{file}` interpolation

**REFACTOR:** Keep per-gate parser schema uniform.

**Exit Criteria:** Live `.st3/quality.yaml` validates against new models with no compatibility shim.

---

## Design Exit Criteria

Design is ready for implementation only when all criteria are true:

1. **Scope Contract Finalized**
   - Public API is `scope` only (`auto|branch|project`), no `files` parameter.
   - Scope resolution semantics are fixed for baseline-present and baseline-missing scenarios.

2. **Violation Contract Finalized**
   - `ViolationDTO` field set and default semantics are fixed.
   - All gate parsers return `list[ViolationDTO]`.

3. **Parsing Strategy Contract Finalized**
   - Only `json_violations` and `text_violations` are supported.
   - No tool-name-dependent parser logic remains.

4. **Baseline State Contract Finalized**
   - State shape is fixed: `quality_gates.baseline_sha`, `quality_gates.failed_files`.
   - Update rules are fixed for all-pass and failure runs.

5. **Response Schema Finalized**
   - ToolResult has exactly two content items in fixed order: text summary, json payload.
   - Compact JSON payload schema is fixed and excludes debug/raw fields.

---

## Traceability Matrix (Research v1.6 → Design Decision → Planned Cycles)

| Finding | Design Decision | Planned Cycles |
|--------:|-----------------|----------------|
| F1 | Remove pytest/coverage from quality gates | C0, C30 |
| F2 | Parse format violations via text strategy with actionable message | C5, C6, C11, C12, C31 |
| F3 | Exactly two content items; summary then json | C25, C26, C27 |
| F4 | Remove files mode; use scope-driven flow | C18, C28 |
| F5 | Add deterministic summary_line first | C25, C27, C29 |
| F6 | Scope selected by explicit enum | C21, C22, C23, C24, C28 |
| F7 | Re-run narrowed by baseline diff ∪ failed_files | C19, C20, C23, C24 |
| F8 | Separate static analysis from test execution | C17, C30, C29 |
| F9 | Project scope from declarative config globs | C3, C21, C30 |
| F10 | Remove broken pytest gate config entries | C0, C30 |
| F11 | Remove hardcoded .py global filtering | C15, C16 |
| F12 | Remove dead pytest-related code paths | C17, C18 |
| F13 | Correct project scope globs | C21, C30 |
| F14 | Parse mypy output into structured violations | C5, C11, C12 |
| F15 | Replace implicit parser coupling with explicit strategies | C2, C4, C5, C6, C13, C14, C31 |

---

## Risks & Mitigation

- **Risk:** Large `qa_manager.py` refactor introduces regressions.
  - **Mitigation:** Keep parser and scope changes in atomic cycles, run focused tests per cycle.

- **Risk:** State update logic might overwrite unrelated state branches.
  - **Mitigation:** Isolate `quality_gates` state writes and verify branch-scoped behavior in tests.

- **Risk:** Git diff behavior may vary by branch ancestry assumptions.
  - **Mitigation:** Add fallback to `main` parent and robust empty-diff handling tests.

- **Risk:** Config migration may fail if mixed old/new parser blocks are present.
  - **Mitigation:** Complete model-first migration (C2/C5), then single-pass YAML migration (C31).

---

## Milestones

- **M0 (Pre-flight Ready):** C0 complete — TDD suite no longer blocked by broken pytest gate
- **M1 (Foundation Ready):** C1–C6 complete
- **M2 (Parser Engine Ready):** C7–C14 complete
- **M3 (Scope and Baseline Ready):** C15–C24 complete
- **M4 (Output and API Ready):** C25–C28 complete
- **M5 (Integration Ready):** C29–C31 complete

---

## Related Documentation

- [research.md](research.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-22 | Agent | Initial planning draft |
| 1.1 | 2026-02-22 | Agent | English rewrite; dependency order fixed; oversized cycles split; ToolResult contract normalized; Design Exit Criteria + Traceability Matrix added |
| 1.2 | 2026-02-22 | Agent | Add C0 (quality.yaml pre-flight); neutral C27 contract; C29 contract-change annotation; TDD Execution Rules; dependency graph + milestones + traceability updated |
