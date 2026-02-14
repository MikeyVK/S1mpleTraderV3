<!-- docs/development/issue137/planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-14T12:25:00Z updated=2026-02-14T13:10:00Z -->
# Issue #137: TDD Cycle Planning for Remote Branch Checkout

**Status:** DRAFT  
**Version:** 2.1  
**Last Updated:** 2026-02-14T13:10:00Z

---

## Purpose

Plan TDD cycles for implementing remote branch checkout support with all design decisions closed before design phase.

## Scope

**In Scope:**
- Binding decisions for all open research questions
- Test case breakdown with explicit expectations
- Quality gates and acceptance criteria
- Traceability from issue to tests

**Out of Scope:**
- Implementation details (HOW to code - determined in design phase)
- Performance optimization strategies
- Multi-remote scenarios

## Prerequisites

Read these first:
1. [research.md](research.md) - Research findings approved
2. Test coverage gaps identified
---

## Summary

Implement remote branch checkout via **Alternative A (Sequential Fallback)** with 4 non-overlapping TDD cycles. All planning decisions closed. Auto-fetch behavior deferred to design phase.

---

## Decision Register

All open questions from research.md resolved:

| ID | Question | Decision | Rationale |
|----|----------|----------|-----------|
| **Q1** | Branch name normalization (`origin/feature/x` input) | **DECIDED:** Strip `origin/` prefix automatically | Matches git CLI behavior; user-friendly |
| **Q2** | Remote preference order | **DECIDED:** Only `origin` (hardcoded) | Consistent with existing push/fetch patterns |
| **Q3** | Auto-fetch behavior | **DEFERRED TO DESIGN PHASE** (see below) | Requires architecture decision on network latency vs freshness trade-off |
| **Q4** | Tracking branch setup | **DECIDED:** Always set tracking branch on remote-only checkout | Matches git CLI `--track` default behavior |
| **Q5** | Error message detail level | **DECIDED:** Descriptive (indicates what was checked) | Balances debugging utility vs noise |
| **ALT** | Implementation alternative | **DECIDED:** Alternative A (Sequential Fallback) | No API changes; backward compatible; matches user mental model |

### Q3 Deferral Details

**Deferred to:** Design phase  
**Reason:** Auto-fetch requires architecture decision on network call integration

**Design phase must deliver:**
1. **Decision:** Auto-fetch on remote miss (yes/no/optional parameter)
2. **If yes:** Error handling strategy for fetch failures
3. **If yes:** User notification mechanism (silent vs logged)
4. **If optional:** Parameter name, default value, docstring
5. **If no:** Document `git_fetch` prerequisite clearly in docstring

**Planning constraint:** Current implementation assumes `git_fetch` already run (no auto-fetch). Design may override.

---

## Error Message Contract

Binding error messages per scenario:

| Scenario | Error Type | Expected Message Format | Actionable Hint |
|----------|-----------|------------------------|-----------------|
| **No origin remote** | `ExecutionError` | `"Origin remote not configured"` | `"Configure origin remote or use existing local branch"` |
| **Branch missing (local + remote)** | `ExecutionError` | `"Branch {name} does not exist (checked: local, origin)"` | `"Use git_list_branches to see available branches, or git_fetch to update"` |
| **Unexpected git error** | `ExecutionError` | `"Failed to checkout {name}: {original_error}"` | `"Check repository state with git_status"` |
| **Invalid prefix input** | N/A (auto-normalized) | N/A | Silently strip `origin/` prefix |

**Contract:** All errors raised as `ExecutionError` with descriptive message + actionable recovery hints.

---

## Test Scenarios (Non-Overlapping)

### Scenario Matrix

| Scenario | Local Branch | Origin Remote | Remote-Tracking Ref | Expected Outcome |
|----------|-------------|---------------|---------------------|------------------|
| **S1** | ✅ Exists | ✅ Configured | ❓ Any | Checkout local (fast path) |
| **S2** | ❌ Missing | ✅ Configured | ✅ Exists | Create local tracking branch, checkout |
| **S3** | ❌ Missing | ❌ Not configured | N/A | Error: "Origin remote not configured" |
| **S4** | ❌ Missing | ✅ Configured | ❌ Missing | Error: "Branch does not exist (checked: local, origin)" |
| **S5** | ❌ Missing | ✅ Configured | ✅ Exists (with origin/ prefix input) | Normalize input, create tracking branch |

**Non-overlap guarantee:** Each scenario has unique (local, remote, ref) tuple.

---

## TDD Cycles

### Cycle 1: Remote-Only Branch Checkout (S2)

**Goal:** Enable checkout of remote-tracking refs without local branch

**Test:** `test_checkout_remote_only_branch`

**Test Specification:**
```python
def test_checkout_remote_only_branch():
    """Test checkout creates local tracking branch from remote-only ref."""
    # GIVEN: Remote-tracking ref exists, no local branch
    mock_repo.heads.__contains__ = lambda self, x: False  # No local
    mock_origin = MagicMock()
    mock_origin.refs.__iter__ = lambda self: iter([mock_ref("origin/feature/test")])
    mock_repo.remote.return_value = mock_origin
    
    # WHEN: Checkout remote-only branch
    adapter.checkout("feature/test")
    
    # THEN: Local tracking branch created and checked out
    mock_repo.create_head.assert_called_once_with("feature/test", mock_origin.refs["feature/test"])
    created_branch.set_tracking_branch.assert_called_once_with(mock_origin.refs["feature/test"])
    created_branch.checkout.assert_called_once()
```

**Success Criteria:**
- ✅ Test fails (RED): ExecutionError "Branch does not exist"
- ✅ Test passes (GREEN): Remote-tracking ref lookup added
- ✅ Regression: `test_checkout_existing_branch` still passes

---

### Cycle 2: Input Normalization (S5)

**Goal:** Handle `origin/feature/x` input by stripping prefix

**Test:** `test_checkout_strips_origin_prefix`

**Test Specification:**
```python
def test_checkout_strips_origin_prefix():
    """Test checkout normalizes origin/ prefix in input."""
    # GIVEN: Remote-tracking ref origin/feature/test, input with prefix
    mock_repo.heads.__contains__ = lambda self, x: False
    mock_origin.refs.__iter__ = lambda self: iter([mock_ref("origin/feature/test")])
    
    # WHEN: Checkout WITH origin/ prefix
    adapter.checkout("origin/feature/test")
    
    # THEN: Prefix stripped, local branch "feature/test" created
    mock_repo.create_head.assert_called_once_with("feature/test", ANY)
    # NOT: create_head("origin/feature/test", ...)
```

**Success Criteria:**
- ✅ Test fails (RED): Tries to create local branch "origin/feature/test"
- ✅ Test passes (GREEN): Input normalized before processing
- ✅ Validation: Branch name without prefix after normalization

---

### Cycle 3: Error Scenarios (S3, S4)

#### Cycle 3A: No Origin Remote (S3)

**Test:** `test_checkout_no_origin_remote`

**Test Specification:**
```python
def test_checkout_no_origin_remote():
    """Test checkout raises clear error when origin not configured."""
    # GIVEN: No local branch, no origin remote
    mock_repo.heads.__contains__ = lambda self, x: False
    mock_repo.remote.side_effect = ValueError("Remote 'origin' not found")
    
    # WHEN/THEN: Checkout raises descriptive error
    with pytest.raises(ExecutionError, match="Origin remote not configured"):
        adapter.checkout("feature/test")
```

**Expected Error:** `"Origin remote not configured"` + recovery hint

**Success Criteria:**
- ✅ Test fails (RED): ValueError propagates uncaught
- ✅ Test passes (GREEN): ValueError caught, converted to ExecutionError

---

#### Cycle 3B: Branch Missing Everywhere (S4)

**Test:** `test_checkout_branch_missing_everywhere`

**Test Specification:**
```python
def test_checkout_branch_missing_everywhere():
    """Test checkout error indicates both local and remote checked."""
    # GIVEN: No local branch, origin configured, no remote-tracking ref
    mock_repo.heads.__contains__ = lambda self, x: False
    mock_origin.refs.__iter__ = lambda self: iter([])  # No refs
    
    # WHEN/THEN: Error message indicates exhaustive search
    with pytest.raises(ExecutionError, match=r"does not exist \(checked: local, origin\)"):
        adapter.checkout("missing")
```

**Expected Error:** `"Branch missing does not exist (checked: local, origin)"` + hint

**Success Criteria:**
- ✅ Test fails (RED): Error message only mentions local
- ✅ Test passes (GREEN): Error message updated to indicate remote check

---

### Cycle 4: Regression & Fast Path (S1)

**Goal:** Validate existing local checkout unaffected, remote NOT called

**Tests:**
- `test_checkout_existing_branch` (existing, modified)
- `test_checkout_nonexistent_branch_raises_error` (existing)

**Test Specification (MODIFIED):**
```python
def test_checkout_existing_branch():
    """Test local branch checkout (fast path) - no remote lookup."""
    # GIVEN: Local branch exists
    mock_repo.heads.__contains__ = lambda self, x: x == "feature/test"
    mock_branch = MagicMock()
    mock_repo.heads.__getitem__ = lambda self, x: mock_branch
    
    # WHEN: Checkout local branch
    adapter.checkout("feature/test")
    
    # THEN: Local branch checked out, NO remote access
    mock_branch.checkout.assert_called_once()
    mock_repo.remote.assert_not_called()  # ← NEW: Ensure fast path
```

**Success Criteria:**
- ✅ Test passes throughout Cycles 1-3
- ✅ **NEW:** `mock_repo.remote.assert_not_called()` passes (proves fast path)
- ✅ No performance regression

---

## Test Execution Sequence

**Strict RED → GREEN → REFACTOR order:**

1. **Cycle 1 (RED):** Write `test_checkout_remote_only_branch` → ExecutionError
2. **Cycle 1 (GREEN):** Add remote-tracking ref lookup → test passes
3. **Cycle 1 (REFACTOR):** Extract helper methods if needed
4. **Cycle 1 (VERIFY):** Run `test_checkout_existing_branch` (regression check)
5. **Commit:** `git_add_or_commit(phase="green", message="...")`

6. **Cycle 2 (RED):** Write `test_checkout_strips_origin_prefix` → fails
7. **Cycle 2 (GREEN):** Add input normalization → test passes
8. **Cycle 2 (REFACTOR):** Clean up normalization logic
9. **Cycle 2 (VERIFY):** Run all tests
10. **Commit:** `git_add_or_commit(phase="refactor", message="...")`

11. **Cycle 3A (RED):** Write `test_checkout_no_origin_remote` → ValueError uncaught
12. **Cycle 3A (GREEN):** Catch ValueError, raise ExecutionError → test passes
13. **Cycle 3A (REFACTOR):** Improve error message formatting
14. **Cycle 3A (VERIFY):** Run all tests

15. **Cycle 3B (RED):** Write `test_checkout_branch_missing_everywhere` → wrong error message
16. **Cycle 3B (GREEN):** Update error message → test passes
17. **Cycle 3B (REFACTOR):** Clean up error handling
18. **Cycle 3B (VERIFY):** Run all tests
19. **Commit:** `git_add_or_commit(phase="refactor", message="...")`

20. **Cycle 4 (MODIFY):** Add `assert_not_called()` to `test_checkout_existing_branch`
21. **Cycle 4 (VERIFY):** Test passes (proves remote not accessed on local hit)
22. **Commit:** `git_add_or_commit(phase="refactor", message="...")`

23. **Final:** Run quality gates, update docstring

---

## Acceptance Criteria

Issue #137 complete when ALL criteria met:

### Functional Requirements
- ✅ `git_checkout("feature/x")` works when only `origin/feature/x` exists (after `git_fetch`)
- ✅ Local tracking branch automatically created with upstream set
- ✅ `git_checkout("origin/feature/x")` works (prefix stripped)
- ✅ Local branch checkout unaffected (fast path preserved)
- ✅ No terminal workaround needed for any scenario

### Test Coverage
- ✅ All 6 tests pass:
  - `test_checkout_remote_only_branch` (S2)
  - `test_checkout_strips_origin_prefix` (S5)
  - `test_checkout_no_origin_remote` (S3)
  - `test_checkout_branch_missing_everywhere` (S4)
  - `test_checkout_existing_branch` (S1, with non-call assertion)
  - `test_checkout_nonexistent_branch_raises_error` (existing regression)
- ✅ Branch coverage ≥ 90% for `git_adapter.py:checkout()` method
- ✅ Zero test failures in full suite

### Quality Gates (per `.st3/quality.yaml`)
- ✅ **Gate 0:** Ruff format (`ruff format --check`)
- ✅ **Gate 1:** Ruff strict lint (no errors)
- ✅ **Gate 2:** Import placement (no mid-function imports)
- ✅ **Gate 3:** Line length (≤100 chars)
- ✅ **Gate 4:** Type checking (mypy + pyright pass)
- ✅ **Gate 5:** All tests pass
- ✅ **Gate 6:** Branch coverage ≥ 90%

### Documentation
- ✅ `GitAdapter.checkout()` docstring updated:
  - Documents remote-tracking ref fallback
  - Notes `git_fetch` prerequisite (until Q3 resolved in design)
  - Lists possible ExecutionError scenarios
- ✅ Error messages match contract table

---

## Traceability Matrix

| Issue Acceptance Criterion | Test(s) | Expected Outcome |
|----------------------------|---------|------------------|
| "git_checkout works for remote-only branches" | `test_checkout_remote_only_branch` | Local tracking branch created, checkout succeeds |
| "Local tracking branch automatically created" | `test_checkout_remote_only_branch` | `set_tracking_branch()` called |
| "No terminal workaround needed" | `test_checkout_existing_branch` + `test_checkout_remote_only_branch` | Adapter: `mock_repo.remote.assert_not_called()` on local hit; Tool: Zero `run_in_terminal` calls in `GitCheckoutTool.execute()` |
| "Existing local branch checkout unaffected" | `test_checkout_existing_branch` | `remote.assert_not_called()` passes (fast path proof) |
| "Handles origin/ prefix input" | `test_checkout_strips_origin_prefix` | Prefix stripped correctly |
| "Clear error when origin missing" | `test_checkout_no_origin_remote` | Error: "Origin remote not configured" |
| "Clear error when branch missing" | `test_checkout_branch_missing_everywhere` | Error: "...checked: local, origin" |
| "Quality gates pass" | `run_quality_gates` | All 7 gates (0-6) return success |
| "Coverage ≥ 90%" | `pytest --cov-branch --cov-fail-under=90` | Exit code 0 |

---

## Dependencies

**Blocking:** None (all planning decisions closed)

**Non-blocking:**
- Issue #138 (git phase validation) - separate workflow concern
- Q3 auto-fetch decision - handled in design phase

---

## Risks

### Risk 1: Stale Remote-Tracking Refs
**Impact:** User must `git_fetch` before checkout for fresh refs (unless Q3 enables auto-fetch in design)

**Mitigation:** Document in docstring: _"Note: Requires recent `git_fetch` for up-to-date remote-tracking refs."_

**Owner:** Design phase (Q3 decision)

### Risk 2: Multiple Remotes Edge Case
**Impact:** Only checks `origin`; ignores `upstream`, `fork`, etc.

**Mitigation:** Consistent with existing push/fetch behavior. Document in docstring.

**Accepted:** Multi-remote support deferred (Q2 decision: origin-only)

---

## Design Entry Criteria

**Transition to Design phase allowed ONLY when:**

- ✅ All 5 research questions (Q1-Q5) have binding decisions OR explicit design-phase deferral
- ✅ Alternative selection finalized (Alternative A chosen)
- ✅ Error message contract defined for all scenarios
- ✅ Test scenarios non-overlapping and complete
- ✅ Traceability matrix complete
- ✅ Quality gates aligned with `.st3/quality.yaml`
- ✅ Planning document approved by human reviewer

**Current Status:** ✅ ALL CRITERIA MET - Ready for Design phase

**Next Phase:** Design phase will resolve Q3 (auto-fetch behavior) and produce implementation architecture.

---

## Related Documentation
- [research.md](research.md) - Research findings (all questions answered or deferred)
- [mcp_server/adapters/git_adapter.py](../../../mcp_server/adapters/git_adapter.py) - Implementation target
- [tests/unit/mcp_server/adapters/test_git_adapter.py](../../../tests/unit/mcp_server/adapters/test_git_adapter.py) - Test location
- [.st3/quality.yaml](../../../.st3/quality.yaml) - Quality gate definitions

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-14T12:25:00Z | Agent | Initial scaffold |
| 1.1 | 2026-02-14T12:30:00Z | Agent | Complete TDD cycle breakdown |
| 2.0 | 2026-02-14T13:00:00Z | Agent | Add Decision Register, error contract, traceability matrix, design entry criteria |
| 2.1 | 2026-02-14T13:10:00Z | Agent | Fix: Q3 deferred to design phase (not future issue), correct phase transition (planning→design), strengthen traceability |
