<!-- docs/development/issue137/planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-14T12:25:00Z updated=2026-02-14T12:30:00Z -->
# Issue #137: TDD Cycle Planning for Remote Branch Checkout

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-02-14T12:30:00Z

---

## Purpose

Plan TDD cycles for implementing remote branch checkout support

## Scope

**In Scope:**
Test cases from research, TDD cycle breakdown, acceptance criteria

**Out of Scope:**
Implementation details, architectural decisions, design choices

## Prerequisites

Read these first:
1. Research document approved
2. Test coverage gaps identified
---

## Summary

Break down remote branch checkout implementation into 4 TDD cycles based on identified test coverage gaps from research phase.

---

## TDD Cycles

### Cycle 1: Remote-Only Branch Checkout (Happy Path)

**Goal:** Enable checkout of branches that exist in remote-tracking refs but not locally

**Tests:**
- `test_checkout_remote_only_branch`

**Test Requirements:**
- **Setup:** Mock repo with remote-tracking ref `origin/feature/test` but no local branch `feature/test`
- **Action:** Call `checkout("feature/test")`
- **Expected Outcome:**
  - Local branch `feature/test` created
  - Local branch set to track `origin/feature/test`
  - Checkout succeeds (active branch is `feature/test`)
  - No ExecutionError raised

**Success Criteria:**
- ✅ Test fails initially (RED) - ExecutionError "Branch does not exist"
- ✅ Implementation makes test pass (GREEN)
- ✅ Existing `test_checkout_existing_branch` still passes (regression check)

---

### Cycle 2: Input Normalization (Origin Prefix)

**Goal:** Handle branch names provided with `origin/` prefix

**Tests:**
- `test_checkout_with_origin_prefix`

**Test Requirements:**
- **Setup:** Mock repo with remote-tracking ref `origin/feature/test`, no local branch
- **Action:** Call `checkout("origin/feature/test")` (with prefix)
- **Expected Outcome:** One of:
  - A) Prefix stripped, local branch `feature/test` created (normalized)
  - B) Validation error with helpful message ("use branch name without origin/ prefix")
  - **NOTE:** Actual behavior determined by implementation; test validates consistency

**Success Criteria:**
- ✅ Test fails initially (RED) - current code doesn't handle prefix
- ✅ Implementation handles prefix consistently (GREEN)
- ✅ Error message clear if prefix rejected

---

### Cycle 3: Error Scenarios

**Goal:** Proper error handling for edge cases

**Tests:**
- `test_checkout_no_remote_configured`
- `test_checkout_nonexistent_remote_branch`

#### Test 3A: No Origin Remote

**Test Requirements:**
- **Setup:** Mock repo with NO origin remote configured
- **Action:** Call `checkout("feature/test")`
- **Expected Outcome:**
  - ExecutionError raised
  - Error message indicates remote not configured (not generic "branch not found")

**Success Criteria:**
- ✅ Test fails initially (RED) - ValueError from `repo.remote("origin")` not caught
- ✅ Implementation catches ValueError and converts to clear ExecutionError (GREEN)

#### Test 3B: Branch Missing Everywhere

**Test Requirements:**
- **Setup:** Mock repo with origin configured but branch `missing` exists neither locally nor in remote-tracking refs
- **Action:** Call `checkout("missing")`
- **Expected Outcome:**
  - ExecutionError raised
  - Error message indicates checked both local and remote (e.g., "not found (checked local + origin)")

**Success Criteria:**
- ✅ Test fails initially (RED) - error message only mentions local
- ✅ Implementation provides descriptive error (GREEN)

---

### Cycle 4: Regression Validation

**Goal:** Ensure existing functionality unaffected

**Tests:**
- `test_checkout_existing_branch` (existing)
- `test_checkout_nonexistent_branch_raises_error` (existing)

**Test Requirements:**
- **Test 4A:** Checkout local branch that already exists
  - **Setup:** Local branch `feature/test` exists
  - **Action:** `checkout("feature/test")`
  - **Expected:** Checkout succeeds, no remote lookup
  
- **Test 4B:** Checkout non-existent branch (no remote configured)
  - **Setup:** Branch `nonexistent` doesn't exist locally, no remote-tracking ref
  - **Action:** `checkout("nonexistent")`
  - **Expected:** ExecutionError raised

**Success Criteria:**
- ✅ Both existing tests continue passing throughout Cycles 1-3
- ✅ No performance regression (local branch fast path preserved)

---

## Test Execution Order

**Sequential order (RED → GREEN → REFACTOR per cycle):**

1. **Cycle 1 (RED):** Write `test_checkout_remote_only_branch` → fails
2. **Cycle 1 (GREEN):** Implement remote-tracking ref lookup → test passes
3. **Cycle 1 (REFACTOR):** Clean up, run all tests (include Cycle 4 regression)
4. **Cycle 2 (RED):** Write `test_checkout_with_origin_prefix` → fails
5. **Cycle 2 (GREEN):** Handle prefix → test passes
6. **Cycle 2 (REFACTOR):** Clean up, run all tests
7. **Cycle 3 (RED):** Write `test_checkout_no_remote_configured` → fails
8. **Cycle 3 (GREEN):** Catch ValueError → test passes
9. **Cycle 3 (RED):** Write `test_checkout_nonexistent_remote_branch` → fails
10. **Cycle 3 (GREEN):** Improve error message → test passes
11. **Cycle 3 (REFACTOR):** Clean up, run all tests
12. **Final:** Run full test suite, verify quality gates

---

## Acceptance Criteria

**Issue #137 is complete when:**

### Functional
- ✅ `git_checkout` works for remote-only branches (after `git_fetch`)
- ✅ Local tracking branch automatically created
- ✅ No terminal workaround needed
- ✅ Existing local branch checkout unaffected

### Test Coverage
- ✅ All 4 test cycles pass
- ✅ Existing `test_checkout_*` tests still pass
- ✅ Code coverage >= 90% for modified methods

### Quality Gates
- ✅ Ruff (no lint errors)
- ✅ MyPy (type checking passes)
- ✅ Pylint (acceptable score)

### Documentation
- ✅ `GitAdapter.checkout()` docstring updated
- ✅ Behavior documented in method docstring

---

## Dependencies

**Blocking:**
- None (research complete, can proceed to TDD)

**Non-blocking:**
- Issue #138 (git_add_or_commit phase validation) - separate concern

---

## Risks

### Risk 1: Alternative Selection
**Risk:** Planning doesn't specify WHICH alternative (A/B/C) to implement.

**Mitigation:** TDD phase will make pragmatic choice during GREEN step based on:
- Simplicity (fastest to make tests pass)
- Consistency (matches existing patterns in git_adapter.py)
- Research trade-offs

**Accepted:** Planning phase is implementation-agnostic; design emerges from TDD.

### Risk 2: Origin Prefix Handling Ambiguity
**Risk:** Test 2 has two valid outcomes (strip vs reject).

**Mitigation:** TDD GREEN step will choose one approach. If need changes later, test documents expected behavior.

**Accepted:** Test validates consistency, not specific choice.

### Risk 3: Stale Remote-Tracking Refs
**Risk:** User must run `git_fetch` before `git_checkout` for fresh refs.

**Mitigation:** Document dependency in checkout() docstring.

**Out of scope:** Auto-fetch behavior not addressed in this issue.

---

## Related Documentation
- **[research.md](research.md)** - Research findings and alternatives
- **[mcp_server/adapters/git_adapter.py](../../../mcp_server/adapters/git_adapter.py)** - Implementation target
- **[tests/unit/mcp_server/adapters/test_git_adapter.py](../../../tests/unit/mcp_server/adapters/test_git_adapter.py)** - Test location

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-14T12:25:00Z | Agent | Initial scaffold |
| 1.1 | 2026-02-14T12:30:00Z | Agent | Complete TDD cycle breakdown with test requirements and acceptance criteria |
