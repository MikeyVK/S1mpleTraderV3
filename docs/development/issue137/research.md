<!-- docs/development/issue137/research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-14T10:55:00Z updated=2026-02-14T12:10:00Z -->
# Issue #137: Remote Branch Checkout Research

**Status:** DRAFT  
**Version:** 1.2  
**Last Updated:** 2026-02-14T12:10:00Z

---

## Purpose

Investigate current limitations of git_checkout when branches exist only on remote, and explore implementation alternatives.

## Scope

**In Scope:**
- GitAdapter.checkout() current behavior
- GitPython remote reference API
- Existing test coverage patterns
- Alternative implementation strategies

**Out of Scope:**
- Branch creation workflows (separate concern)
- State management integration
- Multi-remote scenarios beyond origin

## Prerequisites

Read these first:
1. Issue #137 description
2. [mcp_server/adapters/git_adapter.py](../../mcp_server/adapters/git_adapter.py) (lines 148-157)
3. [tests/unit/mcp_server/adapters/test_git_adapter.py](../../tests/unit/mcp_server/adapters/test_git_adapter.py)

---

## Problem Statement

`GitAdapter.checkout()` only checks local branches (`self.repo.heads`), raising ExecutionError when branch exists solely on remote after `git fetch`. User workaround requires terminal: `git checkout -b local origin/remote`.

---

## Observations

### Current Implementation Behavior

**File:** `mcp_server/adapters/git_adapter.py` (lines 148-157)

```python
def checkout(self, branch_name: str) -> None:
    """Checkout to an existing branch."""
    try:
        if branch_name not in self.repo.heads:  # ⚠️ Only checks local
            raise ExecutionError(f"Branch {branch_name} does not exist")
        self.repo.heads[branch_name].checkout()
    except ExecutionError:
        raise
    except Exception as e:
        raise ExecutionError(f"Failed to checkout {branch_name}: {e}") from e
```

**Observation:** Method assumes all branches are local. No remote lookup attempted.

### GitPython API Patterns (from existing codebase)

**Remote access pattern** (lines 162, 205):
```python
origin = self.repo.remote("origin")  # May raise ValueError if not configured
```

**Remote references** (inferred from push/fetch):
```python
origin.refs  # List of RemoteReference objects (e.g., origin/main, origin/feature/x)
```

**Branch creation** (lines 85-95):
```python
self.repo.create_head(branch_name, base_ref)  # Creates local branch from ref
```

**Tracking branch setup** (line 240 - has_upstream check):
```python
self.repo.active_branch.tracking_branch()  # Returns RemoteReference or None
```

### Existing Test Coverage

**File:** `tests/unit/mcp_server/adapters/test_git_adapter.py` (lines 10-40)

**Covered scenarios:**
- ✅ Checkout existing local branch
- ✅ Checkout non-existent branch (error)

**Uncovered scenarios:**
- ❌ Remote-only branch (issue #137 gap)
- ❌ Input normalization (with/without `origin/` prefix)
- ❌ Missing origin remote
- ❌ Branch exists on remote but not locally

---

## Alternatives

### Alternative A: Two-Tier Fallback (Local → Remote)

**Hypothetical example:**
```python
def checkout(self, branch_name: str) -> None:
    # Check local first
    if branch_name in self.repo.heads:
        self.repo.heads[branch_name].checkout()
        return
    
    # Check remote second
    try:
        origin = self.repo.remote("origin")
        remote_ref = f"origin/{branch_name}"
        if remote_ref in [ref.name for ref in origin.refs]:
            local = self.repo.create_head(branch_name, origin.refs[branch_name])
            local.set_tracking_branch(origin.refs[branch_name])
            local.checkout()
            return
    except ValueError:  # No origin remote
        pass
    
    raise ExecutionError(f"Branch {branch_name} not found (local/remote)")
```

**Characteristics:**
- Preserves fast path for local branches
- Adds remote lookup on local miss
- Auto-creates tracking branch

### Alternative B: Explicit Remote Flag

**Hypothetical example:**
```python
def checkout(self, branch_name: str, check_remote: bool = True) -> None:
    # ... local check ...
    if not check_remote:
        raise ExecutionError("Local branch not found")
    # ... remote check ...
```

**Characteristics:**
- Explicit control over remote lookup
- Backward compatible via default parameter
- Requires API change

### Alternative C: Separate Method

**Hypothetical example:**
```python
def checkout_from_remote(self, branch_name: str, remote: str = "origin") -> None:
    """Checkout remote-only branch, creating local tracking branch."""
    # ... remote-specific logic ...
```

**Characteristics:**
- Clear separation of concerns
- Existing checkout() unchanged
- More methods to maintain

---

## Trade-offs

### Alternative A (Two-Tier Fallback)

**Pros:**
- ✅ No API changes (backward compatible)
- ✅ Matches user mental model (git checkout just works)
- ✅ Consistent with push/fetch (both use origin implicitly)
- ✅ Minimal performance impact (remote check only on miss)

**Cons:**
- ❌ Adds complexity to single method
- ❌ Silent remote lookup (less explicit)
- ❌ Network call on every local miss (if remote stale)

### Alternative B (Explicit Flag)

**Pros:**
- ✅ Explicit control
- ✅ Testable in isolation (flag=False disables remote)

**Cons:**
- ❌ API change (breaks existing calls if required param)
- ❌ Requires tool layer changes
- ❌ Less user-friendly (extra parameter)

### Alternative C (Separate Method)

**Pros:**
- ✅ SRP (Single Responsibility Principle)
- ✅ No existing logic modified

**Cons:**
- ❌ User must know which method to call
- ❌ Duplicates error handling logic
- ❌ More test surface area

---

## Risks

### Input Normalization Ambiguity
**Risk:** User provides `"origin/feature/x"` - should we:
- A) Strip prefix and checkout as `"feature/x"`?
- B) Treat as malformed input and error?
- C) Attempt both formats?

**Evidence:** None found in codebase. Other git operations use branch names without `origin/` prefix.

### Missing Origin Remote
**Risk:** Repo has no origin configured.

**Current behavior:** `self.repo.remote("origin")` raises `ValueError`.

**Unclear:** Should we:
- A) Fail immediately with clear error?
- B) Check other remotes (upstream, etc.)?
- C) Proceed without remote check?

### Error Message Strategy
**Risk:** Poor error messages confuse users.

**Options:**
- Generic: "Branch not found"
- Detailed: "Branch not found (checked: local, origin)"
- Actionable: "Branch not found. Try: git_fetch first"

**Unclear:** What level of detail aids debugging without noise?

### Performance on Stale Remote
**Risk:** Remote refs stale after someone else pushes. User must `git_fetch` first.

**Unclear:** Should checkout auto-fetch? (Adds network latency)

---

## Open Questions

### Q1: Branch Name Normalization
**Question:** How should `"origin/feature/x"` input be handled?

**Options:**
- Strip prefix automatically (user-friendly)
- Reject as invalid input (strict)
- Document expected format (docs-based)

**Decision needed in:** Planning phase

### Q2: Remote Preference Order
**Question:** If multiple remotes exist (origin, upstream, fork), which to check?

**Current pattern:** All git operations use `"origin"` hardcoded.

**Options:**
- A) Only origin (consistent with existing)
- B) Configurable (adds complexity)
- C) Check all remotes (ambiguous if duplicate branch names)

**Decision needed in:** Planning phase

### Q3: Auto-Fetch Behavior
**Question:** Should checkout trigger fetch if remote branch not found locally?

**Trade-off:** Freshness vs performance.

**Decision needed in:** Planning phase

### Q4: Tracking Branch Setup
**Question:** Should local branch always track remote, or only on explicit creation?

**Current pattern:** `has_upstream()` check suggests tracking is expected.

**Decision needed in:** Planning phase

### Q5: Error Message Detail Level
**Question:** How verbose should "not found" errors be?

**Options:**
- Minimal: "Branch X not found"
- Descriptive: "Branch X not found (checked local + origin)"
- Actionable: "Branch X not found. Try: git_fetch, git_list_branches"

**Decision needed in:** Planning phase

---

## Evidence

### Existing Git Method Patterns

**push() method** (lines 161-175):
- Explicitly checks for `origin` remote
- Raises ExecutionError if missing
- No fallback to other remotes

**fetch() method** (lines 177-218):
- Accepts `remote` parameter (default: "origin")
- Explicit origin preference
- Clear error if remote not configured

**Pattern consistency:** All git operations prefer `origin` as default remote.

### Test Coverage Gaps

**File:** `tests/unit/mcp_server/adapters/test_git_adapter.py`

**Missing test scenarios:**
1. Remote-only branch checkout (primary gap)
2. Origin remote not configured
3. Branch name with `origin/` prefix
4. Branch exists on remote but outdated locally
5. Tracking branch relationship verification

**Regression risk:** Existing local checkout tests must remain passing.

### Related Issues

- **Issue #138:** git_add_or_commit phase validation (separate concern, doesn't block this issue)
- **Issue #24:** Missing git operations (this issue closes gap)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-14T10:55:00Z | Agent | Initial draft |
| 1.1 | 2026-02-14T11:00:00Z | Agent | Added implementation details (REMOVED in 1.2) |
| 1.2 | 2026-02-14T12:10:00Z | Agent | Refactor to pure research (observações, alternatives, trade-offs, risks, open questions) |
