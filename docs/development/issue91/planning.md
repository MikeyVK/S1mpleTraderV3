# Issue #91 Planning: Restore clean tests + consistent ToolResult error contract

**Status:** DRAFT  
**Phase:** Planning  
**Date:** 2026-01-06  
**Issue:** #91 - Test suite cleanup + test structure consolidation

---

## Purpose

Translate the research findings in `docs/development/issue91/research.md` into an actionable plan that:

1. Restores a clean, stable CI/unit test baseline (no “drift failures”).
2. Consolidates all `mcp_server` **unit tests** into a mirrored layout under `tests/unit/mcp_server/` (including tools + scaffolding).
3. Clarifies and enforces the intended contracts where tests disagree with implementation (validation severity, state schema, scaffolding validity).

**Not Covered Here:**
- Detailed class designs (keep for design phase if needed)
- Implementation details (TDD phase)
- Full root-cause narratives (already in research)

---

## Scope

**In Scope:**
- Fixing/aligning tests and code so the current 10 failures are eliminated
- Removing/avoiding duplicate unit tests by consolidating into the mirror tree
- Updating docs/tests to match the intended contracts for:
  - GUIDELINE vs STRICT validation behavior
  - scaffold → validate expectations
  - `.st3/state.json` schema expectations
  - BOM/encoding handling where tests parse source

**Out of Scope:**
- Broad refactors unrelated to the failing clusters
- New features or additional tooling beyond what is needed for test correctness

---

## Current Baseline

- Latest test run: `10 failed, 1017 passed`
- Failures clustered into:
  - Validation severity contract drift
  - Scaffold→Validate E2E drift
  - State schema drift (`state.json`)
  - Git tools test patching/import drift
  - Parent-branch reflog drift
  - UTF-8 BOM encoding drift

---

## Implementation Goals

### Goal 1: Establish the canonical unit-test mirror layout
**Objective:** All unit tests whose subject is in `mcp_server/` live under `tests/unit/mcp_server/` in a mirrored path.

**Success Criteria:**
- ✅ No `mcp_server` unit tests remain under `tests/unit/tools/`, `tests/unit/scaffolding/`, or `tests/mcp_server/`
- ✅ For every `mcp_server/<area>/...` module, related unit tests are under `tests/unit/mcp_server/<area>/...`
- ✅ Duplicated test coverage is reduced by merging/moving rather than copying

**Work Items:**
- Inventory non-mirrored unit tests (already listed in research)
- Decide canonical destinations under `tests/unit/mcp_server/tools/`, `tests/unit/mcp_server/scaffolding/`, `tests/unit/mcp_server/managers/`, etc.
- Perform moves as pure refactors (file moves + import path adjustments) before behavior changes

---

### Goal 2: Align validation severity semantics (GUIDELINE vs STRICT)
**Objective:** Make validation behavior match the documented contract.

**Success Criteria:**
- ✅ `test_safe_edit_allows_with_guideline_warnings` passes
- ✅ “Guidelines warn but do not block” is true in practice, or the docs/tests are updated to reflect a different intended policy (choose one)

**Work Items:**
- Determine whether Pylint naming (`invalid-name`) is supposed to be “guideline” severity or “strict” severity
- Align validator/lint severity mapping with Issue #52 semantics (or explicitly change the contract)

---

### Goal 3: Restore scaffold→validate E2E correctness
**Objective:** Generated scaffolding output validates under the current validator/lint/type-check pipeline.

**Success Criteria:**
- ✅ `test_scaffold_dto_passes_validation` passes
- ✅ `test_scaffold_tool_passes_validation` passes

**Work Items:**
- Identify which templates are producing invalid output (DTO + Tool)
- Decide whether the requirement remains “generated output must validate” (Issue #52 indicates yes)
- Fix template output or adjust validation rules (minimally) to satisfy the intended contract

---

### Goal 4: Clarify and align `.st3/state.json` schema expectations
**Objective:** Tests and implementation agree on the state schema.

**Success Criteria:**
- ✅ `test_issue39_cross_machine` passes
- ✅ State schema is documented and stable

**Work Items:**
- Locate the intended schema documentation (Issue #45 referenced by Issue #39)
- Decide canonical schema shape (single-branch object vs mapping keyed by branch)
- Align tests + code accordingly

---

### Goal 5: Make git tools tests resilient to refactors
**Objective:** Tests patch the correct locations and do not depend on incidental import structure.

**Success Criteria:**
- ✅ `test_git_checkout_state_sync` tests pass
- ✅ `test_get_parent_branch_current_branch` passes

**Work Items:**
- Confirm intended import style (module-level vs local imports)
- Update tests to patch the correct symbol source and avoid leaking current-branch state

---

### Goal 6: Resolve UTF-8 BOM drift
**Objective:** Source parsing tests don’t fail due to BOM, and repo conventions are consistent.

**Success Criteria:**
- ✅ `test_git_checkout_does_not_call_protected_save_state` passes

**Work Items:**
- Decide policy: strip BOM from Python source files (recommended) vs update tests to read with `utf-8-sig`
- Apply minimal changes consistent with the chosen policy

---

## Sequencing (recommended)

1. Mirror consolidation (moves only) to reduce duplicate/competing test suites.
2. Fix the lowest-risk deterministic failures first:
   - BOM/encoding drift
   - import/patch drift
3. Address contract-level decisions next:
   - validation severity
   - state schema
   - scaffold→validate

---

## Acceptance Criteria (overall)

- ✅ All tests pass locally (`python -m pytest`)
- ✅ All `mcp_server` unit tests live under `tests/unit/mcp_server/` mirrored structure
- ✅ `research.md` + `planning.md` reflect the chosen contracts (severity/schema/scaffolding)

---

## Risks / notes

- Some failures likely require choosing a single “source of truth” (docs vs tests vs current behavior). We should decide explicitly and document it rather than patching around it.
