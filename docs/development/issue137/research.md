<!-- docs/development/issue137/research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-14T10:55:00Z updated=2026-02-14T12:20:00Z -->
# Issue #137: Remote Branch Checkout Research

**Status:** DRAFT  
**Version:** 1.4  
**Last Updated:** 2026-02-14T12:20:00Z

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
2. [mcp_server/adapters/git_adapter.py](../../../mcp_server/adapters/git_adapter.py) (lines 148-157)
3. [tests/unit/mcp_server/adapters/test_git_adapter.py](../../../tests/unit/mcp_server/adapters/test_git_adapter.py)

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
              # NOTE: These are LOCAL remote-tracking refs, not live network calls
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

### Alternative A: Sequential Fallback Strategy

**Conceptual flow:**
```
1. Check local branch collection
   → IF found: switch to local branch, RETURN
   
2. Check remote-tracking ref collection (origin remote)
   → IF found: create local tracking branch, switch to it, RETURN
   → IF origin missing: fall through
   
3. Raise error: branch not found in local or remote-tracking refs
```

**Characteristics:**
- Single method handles both scenarios
- Local branch checked first (fast path)
- Remote-tracking refs checked second (fallback)
- Automatic tracking branch creation on remote-only match
- No signature changes (backward compatible)

**Dependencies:**
- Requires prior fetch for fresh remote-tracking refs
- Assumes origin as default remote

---

### Alternative B: Parametric Control

**Conceptual flow:**
```
Parameters: branch_name, check_remote_refs (default: true)

1. Check local branch collection
   → IF found: switch, RETURN
   
2. IF check_remote_refs == false:
   → Raise error: local branch not found
   
3. Check remote-tracking refs
   → IF found: create local + switch
   → ELSE: raise error
```

**Characteristics:**
- Caller controls remote-tracking ref lookup
- Optional parameter (default preserves new behavior)
- Explicit separation of local vs remote-tracking scenarios
- API surface grows (new parameter)

**Dependencies:**
- Tool layer must pass parameter explicitly
- Testing must cover both flag states

---

### Alternative C: Dedicated Method

**Conceptual flow:**
```
Method A (existing): checkout(branch_name)
  → Only checks local branches
  → No changes to existing behavior

Method B (new): checkout_from_remote_ref(branch_name, remote="origin")
  → Only checks remote-tracking refs
  → Creates local tracking branch
  → Switches to new branch
```

**Characteristics:**
- Separation of concerns (SRP)
- No modifications to existing method
- User must explicitly choose which method
- Two code paths to maintain

**Dependencies:**
- Tool layer must route to correct method
- Documentation must explain when to use which

---

## Trade-offs

### Alternative A (Sequential Fallback)

**Pros:**
- ✅ No API changes (backward compatible)
- ✅ Matches user mental model (git checkout just works)
- ✅ Consistent with push/fetch (both use origin implicitly)
- ✅ No network overhead (reads local remote-tracking refs)

**Cons:**
- ❌ Adds complexity to single method
- ❌ Silent remote lookup (less explicit)
- ❌ Requires prior `git_fetch` to have fresh remote-tracking refs

### Alternative B (Parametric Control)

**Pros:**
- ✅ Explicit control
- ✅ Testable in isolation (flag=False disables remote)

**Cons:**
- ❌ API change (breaks existing calls if required param)
- ❌ Requires tool layer changes
- ❌ Less user-friendly (extra parameter)

### Alternative C (Dedicated Method)

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

### Stale Remote-Tracking Refs
**Risk:** Remote-tracking refs outdated if no recent fetch. Branch appears missing despite existing on server.

**Current dependency:** Assumes user ran `git_fetch` before `git_checkout`.

**Unclear:** Should checkout auto-fetch stale refs? (Adds network latency)

---

## Open Questions

### Q1: Branch Name Normalization
**Question:** How should `"origin/feature/x"` input be handled?

**Options:**
- Strip prefix automatically (user-friendly)
- Reject as invalid input (strict)
- Document expected format (docs-based)

### Q2: Remote Preference Order
**Question:** If multiple remotes exist (origin, upstream, fork), which to check?

**Current pattern:** All git operations use `"origin"` hardcoded.

**Options:**
- A) Only origin (consistent with existing)
- B) Configurable (adds complexity)
- C) Check all remotes (ambiguous if duplicate branch names)

### Q3: Auto-Fetch Behavior
**Question:** Should checkout trigger fetch if remote branch not found in local tracking refs?

**Trade-off:** Freshness vs performance.

### Q4: Tracking Branch Setup
**Question:** Should local branch always track remote, or only on explicit creation?

**Current pattern:** `has_upstream()` check suggests tracking is expected.

### Q5: Error Message Detail Level
**Question:** How verbose should "not found" errors be?

**Options:**
- Minimal: "Branch X not found"
- Descriptive: "Branch X not found (checked local + origin)"
- Actionable: "Branch X not found. Try: git_fetch, git_list_branches"

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

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-14T10:55:00Z | Agent | Initial draft |
| 1.1 | 2026-02-14T11:00:00Z | Agent | Added implementation details (REMOVED in 1.2) |
| 1.2 | 2026-02-14T12:10:00Z | Agent | Refactor to pure research (observations, alternatives, trade-offs, risks, open questions) |
| 1.3 | 2026-02-14T12:15:00Z | Agent | Fix: correct relative paths, remove network call claim, remove procedural references, remove unrelated issues |
| 1.4 | 2026-02-14T12:20:00Z | Agent | Neutralize alternatives with conceptual flow instead of concrete code |
