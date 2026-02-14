<!-- D:\dev\SimpleTraderV3-parallel\.st3\issue137-remote-branch-checkout.md -->
<!-- template=research version=8b7bb3ab created=2026-02-14T10:55:00Z updated=2026-02-14T11:00:00Z -->
# Issue #137: Remote Branch Checkout Research

**Status:** APPROVED  
**Version:** 1.1  
**Last Updated:** 2026-02-14T11:00:00Z

---

## Purpose

Investigate how to extend git_checkout to support remote-only branches

## Scope

**In Scope:**
GitAdapter.checkout() method, GitPython remote references, existing test coverage

**Out of Scope:**
Other git operations, branch creation logic, state management

## Prerequisites

Read these first:
1. Issue #137 description reviewed
2. GitAdapter code analyzed
---

## Problem Statement

GitAdapter.checkout() only checks local branches (self.repo.heads), failing when branch exists only on remote after git fetch

## Research Goals

- Understand GitPython remote reference model
- Design solution for remote branch checkout
- Identify test cases needed

## Related Documentation
- **[GitPython Documentation][related-1]**
- **[mcp_server/adapters/git_adapter.py][related-2]**
- **[tests/unit/mcp_server/adapters/test_git_adapter.py][related-3]**

<!-- Link definitions -->

[related-1]: https://gitpython.readthedocs.io/en/stable/reference.html#module-git.repo.base
[related-2]: file://./mcp_server/adapters/git_adapter.py#L148
[related-3]: file://./tests/unit/mcp_server/adapters/test_git_adapter.py

---

## Findings

### Current Implementation Analysis

**File:** `mcp_server/adapters/git_adapter.py` (lines 148-157)

```python
def checkout(self, branch_name: str) -> None:
    """Checkout to an existing branch."""
    try:
        if branch_name not in self.repo.heads:  # ❌ LOCAL ONLY
            raise ExecutionError(f"Branch {branch_name} does not exist")
        self.repo.heads[branch_name].checkout()
    except ExecutionError:
        raise
    except Exception as e:
        raise ExecutionError(f"Failed to checkout {branch_name}: {e}") from e
```

**Problem:** `self.repo.heads` only contains local branches. Remote-only branches are in `self.repo.remotes['origin'].refs`.

### GitPython Remote Reference Model

Based on analysis of existing code patterns:

1. **Access remote:** `origin = self.repo.remote("origin")` (used in push, fetch methods)
2. **Remote refs:** `origin.refs` contains all remote branches (e.g., `origin/main`, `origin/feature/x`)
3. **Create local tracking branch:** GitPython's `create_head()` method can create from remote ref
4. **Set upstream:** `branch.set_tracking_branch(remote_ref)` establishes tracking relationship

### Existing Test Coverage

**File:** `tests/unit/mcp_server/adapters/test_git_adapter.py`

Existing tests:
- ✅ `test_checkout_existing_branch` - validates local branch checkout
- ✅ `test_checkout_nonexistent_branch_raises_error` - validates error for missing branch

Missing tests:
- ❌ **Remote-only branch checkout** (main gap!)
- ❌ Branch name normalization (with/without 'origin/' prefix)
- ❌ Non-existent remote branch
- ❌ Remote not configured scenario

### Solution Design

**Three-Tier Fallback Strategy:**

```python
def checkout(self, branch_name: str) -> None:
    """Checkout to an existing branch (local or remote)."""
    # 1. Try local branch first
    if branch_name in self.repo.heads:
        self.repo.heads[branch_name].checkout()
        return
    
    # 2. Try remote branch  
    try:
        origin = self.repo.remote("origin")
        remote_ref_name = f"origin/{branch_name}"
        
        # Check if remote branch exists
        if remote_ref_name in [ref.name for ref in origin.refs]:
            # Create local tracking branch
            local_branch = self.repo.create_head(
                branch_name,
                origin.refs[branch_name]
            )
            local_branch.set_tracking_branch(origin.refs[branch_name])
            local_branch.checkout()
            return
    except ValueError:
        # No origin remote configured - fall through to error
        pass
    
    # 3. Branch not found
    raise ExecutionError(
        f"Branch {branch_name} does not exist (checked local and origin)"
    )
```

### Test Cases Required

**New test cases to add:**

1. **`test_checkout_remote_only_branch`**
   - Setup: Remote branch exists, no local branch
   - Action: `checkout("feature/test")`
   - Expected: Local tracking branch created, checked out
   
2. **`test_checkout_remote_only_branch_with_origin_prefix`**
   - Setup: Remote branch `origin/feature/test` exists
   - Action: `checkout("origin/feature/test")`
   - Expected: Strip `origin/` prefix, create `feature/test` locally

3. **`test_checkout_nonexistent_remote_branch`**
   - Setup: Branch doesn't exist locally OR remotely
   - Action: `checkout("missing")`
   - Expected: ExecutionError with message about checking both local and remote

4. **`test_checkout_no_remote_configured`**
   - Setup: No origin remote
   - Action: `checkout("feature/test")`
   - Expected: ExecutionError (no remote available)

### Implementation Considerations

**Edge Cases:**
- **Detached HEAD state:** Already handled by get_current_branch()
- **Multiple remotes:** Only check `origin` (consistent with push/fetch)
- **Name normalization:** Should `"origin/feature/x"` be stripped to `"feature/x"`?
- **Dirty working directory:** Git will handle (raise error if conflicts)

**Error Messages:**
- Clear distinction between "not found locally" vs "not found anywhere"
- Suggest `git_fetch` if remote might be stale

**Performance:**
- Remote check adds minimal overhead (list comprehension over refs)
- Only attempted if local branch not found (fast path unaffected)

---

## Recommendations

### Implementation Approach

**APPROVED:** Three-tier fallback (local → remote → error)

**Rationale:**
- ✅ Backward compatible (local branch checkout unchanged)
- ✅ Minimal performance impact (remote check only on local miss)
- ✅ Consistent with existing patterns (`origin` preference)
- ✅ Clear error messages for debugging

### Test Strategy

**TDD Sequence:**
1. RED: Add `test_checkout_remote_only_branch` (fails with current code)
2. GREEN: Implement remote branch support
3. REFACTOR: Extract helper methods if needed
4. Repeat for remaining 3 test cases

### Documentation Updates

**Files to update:**
- `mcp_server/adapters/git_adapter.py` - docstring update
- `agent.md` - note about automatic remote branch handling (if relevant)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-14T10:55:00Z | Agent | Initial draft |
| 1.1 | 2026-02-14T11:00:00Z | Agent | Complete research findings |
