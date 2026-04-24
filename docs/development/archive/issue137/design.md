<!-- docs/development/issue137/design.md -->
<!-- template=design version=5827e841 created=2026-02-14T13:30:00Z updated=2026-02-14T15:00:00Z -->
# Issue #137: Design for Remote Branch Checkout

**Status:** DRAFT  
**Version:** 2.0  
**Last Updated:** 2026-02-14T15:00:00Z

---

## Scope

**In Scope:**
- GitAdapter.checkout() implementation to support remote-tracking refs
- Error handling aligned with existing ToolResult contract (tool_result.py)
- Backward compatibility with existing GitCheckoutTool behavior (phase sync + parent branch)
- Input normalization (strip 'origin/' prefix)

**Out of Scope (Non-Goals):**
- `.st3/error_catalog.yaml` file creation (Issue #136)
- `ErrorCatalogService` implementation (Issue #136)
- Cross-tool error taxonomy (Issue #136)
- Auto-fetch behavior (deferred per Q3)
- Multi-remote support (deferred per Q2)
- Template placeholder systems (Issue #136)

## Prerequisites

Read these first:
1. [research.md](research.md) - 3 alternatives analyzed
2. [planning.md](planning.md) - All decisions closed (v2.1), scenarios S1-S5
3. [mcp_server/tools/tool_result.py](../../../mcp_server/tools/tool_result.py) - ToolResult contract
4. [mcp_server/tools/git_tools.py](../../../mcp_server/tools/git_tools.py#L219) - Current GitCheckoutTool behavior

---

## 1. Context & Requirements

### 1.1. Problem Statement

GitAdapter.checkout() only checks local branches (self.repo.heads), causing ExecutionError when attempting to checkout remote-only branches (Scenario S2 from planning.md). 

**Acceptance:** Issue #137 is done when checkout works for remote-only branches WITHOUT breaking existing tool contract (phase sync + parent branch output).

### 1.2. Requirements

**Functional (Mapped to Planning Scenarios):**
- ✅ **S2:** git_checkout('feature/x') succeeds when only origin/feature/x exists
- ✅ **S5:** git_checkout('origin/feature/x') normalizes prefix to 'feature/x'
- ✅ **S1:** Local branch checkout unaffected (fast path preserved)
- ✅ **S3:** Clear error when origin remote not configured
- ✅ **S4:** Clear error when branch missing everywhere
- ✅ Existing GitCheckoutTool output preserved (phase + parent branch)

**Non-Functional:**
- ✅ **Performance Invariant:** Local checkout MUST NOT trigger remote lookup
- ✅ **Backward Compatibility:** No changes to public tool contract (input/output format)
- ✅ **Error Format:** Use existing `ToolResult.error(message, error_code, hints)` contract

### 1.3. Constraints

- Only 'origin' remote supported (Decision Q2 from planning.md)
- **Functional Preconditie:** Requires git_fetch pre-run for fresh remote-tracking refs (Decision Q3: no auto-fetch)
- GitPython library: origin.refs are local remote-tracking refs (no network call)
- Must pass all 7 quality gates (Gates 0-6 from .st3/quality.yaml)
- Branch coverage ≥90% requirement

---

## 2. Design Options

### 2.1. Option A: Sequential Fallback (CHOSEN)

Check local branches first (fast path), then check remote-tracking refs, then error

**Pros:**
- ✅ No API changes
- ✅ Backward compatible
- ✅ Matches git CLI mental model
- ✅ Fast path preserved (performance invariant)

**Cons:**
- ❌ Slightly more complex logic
- ❌ Two check operations

**Traceability:** Addresses scenarios S1 (local), S2 (remote-only), S5 (prefix normalization)

### 2.2. Option B: Parametric Control (REJECTED)

Add fetch: bool parameter to checkout method

**Rejected:** API change breaks existing callers, violates backward compatibility requirement

### 2.3. Option C: Dedicated Method (REJECTED)

New checkout_remote() method separate from checkout()

**Rejected:** API proliferation, confusing for users

---

## 3. Chosen Design

**Decision:** Implement Alternative A (Sequential Fallback) with adapter-level error messages and tool-level contract preservation.

**Rationale:** Preserves backward compatibility and fast path performance. Adapter stays focused on git operations (domain logic), tool maintains existing contract (phase sync + parent branch output).

### 3.1. Key Design Decisions

| ID | Question | Decision | Traceability |
|----|----------|----------|--------------|
| **Q3** | Auto-fetch behavior | NO auto-fetch (functional preconditie: user must run git_fetch) | Planning Q3, aligns with SRP |
| **Q2** | Multi-remote support | Only 'origin' (hardcoded) | Planning Q2, consistent with existing push/fetch |
| **D1** | Where to handle errors | Adapter raises ExecutionError, tool preserves existing contract | Tool hints optional (#136 scope) |
| **D2** | Input normalization | Strip 'origin/' prefix automatically | Planning S5, matches git CLI |
| **D3** | Fast path guarantee | Local checkout MUST NOT call remote() | Performance invariant S1, testable with mock.assert_not_called() |

**Note on D1:** Tool-level error normalization (error_code, hints) is a **compatibility guideline** for future Issue #136 work, not a required implementation for #137 acceptance. Issue #137 is done when adapter fix works, even if tool errors remain basic.

---

## 4. Architecture Overview

### 4.1. Layered Responsibility

```
┌────────────────────────────────────────────────────────────┐
│ GitCheckoutTool (git_tools.py:219)                         │
│   EXISTING BEHAVIOR (MUST PRESERVE):                       │
│   1. Call manager.checkout(branch) via anyio.to_thread    │
│   2. Sync PhaseStateEngine state                           │
│   3. Get current_phase and parent_branch from state       │
│   4. Return ToolResult.text("Switched to...\nPhase:...")  │
│                                                            │
│   ERROR CONTRACT:                                          │
│   - Use ToolResult.error(message, error_code, hints)      │
│   - hints = list[str] (MCP tool names for recovery)      │
└────────────────────────────────────────────────────────────┘
                            │
                            │ ExecutionError
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ GitAdapter.checkout() (IMPLEMENTATION TARGET)              │
│   RESPONSIBILITY: Git Operations                           │
│   1. Normalize input (strip 'origin/' prefix)             │
│   2. Fast path: Check local branches (NO remote access)   │
│   3. Fallback: Check remote-tracking refs                 │
│   4. Create tracking branch if found                       │
│   5. Raise ExecutionError(descriptive_message) on failure │
└────────────────────────────────────────────────────────────┘
```

**Critical:** Tool contract preservation is NON-NEGOTIABLE. Phase sync + parent branch output must work in all scenarios.

### 4.2. Sequential Fallback Flow

```python
# GitAdapter.checkout() implementation
def checkout(self, branch_name: str) -> None:
    # Step 1: Normalize (Planning S5)
    normalized = branch_name.removeprefix("origin/")
    
    # Step 2: Fast path (Planning S1 - performance invariant)
    if normalized in self.repo.heads:
        self.repo.heads[normalized].checkout()
        return  # ← NO remote access
    
    # Step 3: Check remote (Planning S2)
    try:
        origin = self.repo.remote("origin")
    except ValueError:
        raise ExecutionError("Origin remote not configured")  # Planning S3
    
    remote_ref = next(
        (ref for ref in origin.refs if ref.name == f"origin/{normalized}"),
        None
    )
    
    if remote_ref is None:
        raise ExecutionError(f"Branch {normalized} does not exist (checked: local, origin)")  # Planning S4
    
    # Step 4: Create tracking branch
    local_branch = self.repo.create_head(normalized, remote_ref)
    local_branch.set_tracking_branch(remote_ref)
    local_branch.checkout()
```

---

## 5. Error Handling

### 5.1. Error Contract (tool_result.py)

**Existing contract (MUST USE):**
```python
@classmethod
def error(
    cls,
    message: str,
    error_code: str | None = None,
    hints: list[str] | None = None,  # ← LIST of hints, not single string
    file_path: str | None = None,
) -> ToolResult
```

### 5.2. Error Scenarios (Issue #137 Only)

| Scenario | Adapter Error | Tool Error (Optional Enhancement) | Planning Ref |
|----------|---------------|-----------------------------------|--------------|
| **S3:** No origin | `ExecutionError("Origin remote not configured")` | `ToolResult.error(msg, hints=["Manual: git remote add origin <url>"])` | S3 |
| **S4:** Missing everywhere | `ExecutionError("Branch X does not exist (checked: local, origin)")` | `ToolResult.error(msg, hints=["git_fetch", "git_list_branches"])` | S4 |
| **Unexpected** | `ExecutionError("Failed to checkout X: {detail}")` | `ToolResult.error(msg, hints=["git_status"])` | General |

**Note:** Tool-level hints are **optional enhancements**. Issue #137 is done when adapter raises descriptive ExecutionError. Tool can catch and enhance later per #136 direction.

### 5.3. Hints Priority (MCP-Tool-First)

**Format:** `hints: list[str]`

```python
# MCP tool names FIRST (agent can call directly)
hints=["git_fetch", "git_list_branches"]

# CLI instructions ONLY for manual intervention
hints=["Manual: git remote add origin <url>"]
```

**Rationale:** Agents parse tool names from hints for recovery. CLI instructions only when no MCP tool exists.

---

## 6. Implementation Components

### 6.1. GitAdapter.checkout() - Complete Implementation

**File:** [mcp_server/adapters/git_adapter.py](../../../mcp_server/adapters/git_adapter.py) (lines 148-157)

**Changes:**
1. Input normalization (Decision D2)
2. Fast path check FIRST with early return (Decision D3 invariant)
3. Remote-tracking ref lookup (fallback)
4. Descriptive error messages (scenarios S3, S4)
5. Updated docstring

**New Implementation:**
```python
def checkout(self, branch_name: str) -> None:
    """Checkout branch (local or remote-tracking).
    
    Sequential fallback: checks local branches first (fast path), then
    remote-tracking refs. Creates local tracking branch for remote-only.
    
    Args:
        branch_name: Branch name with or without 'origin/' prefix.
                     Examples: "feature/x", "origin/feature/x"
    
    Returns:
        None: On successful checkout
    
    Raises:
        ExecutionError: In these scenarios:
            - "Origin remote not configured" (no origin remote)
            - "Branch {name} does not exist (checked: local, origin)" (missing)
            - "Failed to checkout {name}: {detail}" (unexpected git error)
    
    Precondition:
        Requires recent git_fetch() for up-to-date remote-tracking refs.
        Does NOT auto-fetch (Decision Q3).
    
    Performance:
        Local branch: O(1), NO remote access (Decision D3 invariant)
        Remote-only: O(n), n = count of remote refs
    """
    # Normalize input (Decision D2, Scenario S5)
    normalized_branch = branch_name.removeprefix("origin/")
    
    # Fast path: local branch exists (Scenario S1, Decision D3)
    if normalized_branch in self.repo.heads:
        self.repo.heads[normalized_branch].checkout()
        return  # ← Early return, NO remote access
    
    # Fallback: check remote-tracking refs (Scenario S2)
    try:
        origin = self.repo.remote("origin")
    except ValueError as e:
        raise ExecutionError("Origin remote not configured") from e  # Scenario S3
    
    # Search for remote-tracking ref
    remote_ref_name = f"origin/{normalized_branch}"
    remote_ref = next(
        (ref for ref in origin.refs if ref.name == remote_ref_name),
        None
    )
    
    if remote_ref is None:
        raise ExecutionError(
            f"Branch {normalized_branch} does not exist (checked: local, origin)"
        )  # Scenario S4
    
    # Create local tracking branch (Scenario S2)
    try:
        local_branch = self.repo.create_head(normalized_branch, remote_ref)
        local_branch.set_tracking_branch(remote_ref)
        local_branch.checkout()
    except Exception as e:
        raise ExecutionError(
            f"Failed to checkout {normalized_branch}: {e}"
        ) from e
```

### 6.2. GitCheckoutTool - Existing Behavior Preserved

**File:** [mcp_server/tools/git_tools.py](../../../mcp_server/tools/git_tools.py#L219)

**MUST PRESERVE (Lines 240-278):**
1. anyio.to_thread.run_sync for blocking git operations
2. PhaseStateEngine state synchronization after checkout
3. current_phase extraction from state
4. parent_branch extraction from state
5. Output format: "Switched to branch: X\nCurrent phase: Y\nParent branch: Z"

**Current Error Handling (Line 247):**
```python
except MCPError as exc:
    return ToolResult.error(f"Checkout failed for branch: {params.branch}")
```

**Optional Enhancement (Compatible with #136 direction):**
```python
except MCPError as exc:
    hints = []
    if "not configured" in str(exc).lower():
        hints = ["Manual: git remote add origin <url>"]
    elif "does not exist" in str(exc).lower():
        hints = ["git_fetch", "git_list_branches"]
    else:
        hints = ["git_status"]
    
    return ToolResult.error(
        f"Checkout failed for branch: {params.branch}",
        error_code="GIT_CHECKOUT_ERROR",  # Optional
        hints=hints
    )
```

**Note:** Tool-level enhancement is OPTIONAL for #137 acceptance. Adapter fix is sufficient.

---

## 7. Regression Protection

### 7.1. Performance Invariant (Testable)

**Requirement:** Local checkout MUST NOT access remote

**Test (planning.md Cycle 4):**
```python
def test_checkout_existing_branch_no_remote_call():
    """CRITICAL: Verify fast path does NOT access remote."""
    mock_repo.heads.__contains__ = lambda self, x: True  # Local exists
    
    adapter.checkout("main")
    
    # Performance invariant: NO remote access on local hit
    mock_repo.remote.assert_not_called()  # ← MUST PASS
```

### 7.2. Tool Contract Preservation (Testable)

**Requirement:** Phase sync + parent branch output unchanged

**Test:**
```python
def test_checkout_preserves_phase_sync():
    """Verify phase state synchronization works after adapter change."""
    # Setup: Remote-only branch exists
    # Execute: checkout
    # Assert: Output contains "Current phase:" and "Parent branch:"
    assert "Current phase:" in result.content[0]["text"]
```

---

## 8. Acceptance Criteria

Issue #137 is **DONE** when:

### 8.1. Functional (Planning Scenarios)
- ✅ **S1:** `test_checkout_existing_branch` passes (local fast path)
- ✅ **S2:** `test_checkout_remote_only_branch` passes (creates tracking branch)
- ✅ **S3:** `test_checkout_no_origin_remote` passes (clear error)
- ✅ **S4:** `test_checkout_branch_missing_everywhere` passes (clear error)
- ✅ **S5:** `test_checkout_strips_origin_prefix` passes (normalization)

### 8.2. Non-Functional
- ✅ Fast path regression test passes (mock.remote.assert_not_called)
- ✅ GitCheckoutTool output preserves phase + parent branch
- ✅ All 7 quality gates pass (Gates 0-6)
- ✅ Branch coverage ≥90%
- ✅ No changes to public tool contract (input/output schema)

### 8.3. Documentation
- ✅ GitAdapter.checkout() docstring updated (precondition, performance)
- ✅ Error messages match scenarios S3, S4

**Definition of Done:** Adapter fix works, tool contract unchanged, all tests pass.

---

## 9. Future Alignment with Issue #136

**Deferred to Issue #136 (Not Required for #137):**

### 9.1. What #136 Will Deliver

1. `.st3/error_catalog.yaml` - Centralized error configuration
2. `ErrorCatalogService` - Config loader with template substitution
3. Cross-tool error taxonomy - Consistent codes/categories
4. Contracttests for E2E error propagation

### 9.2. How #137 Enables #136

**Compatible design choices:**
- ✅ Descriptive adapter errors (easy to classify)
- ✅ Tool boundary as normalization point (architecture matches)
- ✅ MCP tool names in hints (migration-friendly format)

**When #136 lands, minimal changes needed:**
```python
# #137 (now): Basic tool error
except MCPError as exc:
    return ToolResult.error(f"Checkout failed: {params.branch}")

# #136 (future): Enhanced with catalog
except MCPError as exc:
    spec = error_catalog.classify(exc)
    hints = error_catalog.get_recovery_hints(spec.code)
    return ToolResult.error(str(exc), error_code=spec.code, hints=hints)
```

**Migration Impact:** Low - only tool layer changes, adapter untouched.

### 9.3. Non-Commitment

Issue #137 does NOT commit to:
- Specific error_code values (GIT_*, etc.)
- Error taxonomy structure
- Template placeholder format
- ErrorCatalogService API design

These are **#136 decisions**. Issue #137 stays compatible but doesn't pre-implement.

---

## 10. Traceability Matrix

| Planning Element | Design Decision | Implementation | Test |
|-----------------|-----------------|----------------|------|
| **Q3:** No auto-fetch | Functional precondition | Docstring note | N/A (functional req) |
| **Q2:** Origin-only | Q2: Origin-only | Line: `origin = self.repo.remote("origin")` | All tests use origin |
| **S1:** Local fast path | D3: Early return invariant | `if normalized in heads: return` | `assert_not_called()` |
| **S2:** Remote-only | Sequential fallback | `origin.refs` lookup + create_head | `test_checkout_remote_only_branch` |
| **S3:** No origin | Error message | `except ValueError: raise ExecutionError` | `test_checkout_no_origin_remote` |
| **S4:** Missing | Error message | `if remote_ref is None: raise` | `test_checkout_branch_missing_everywhere` |
| **S5:** Prefix strip | D2: Input normalization | `removeprefix("origin/")` | `test_checkout_strips_origin_prefix` |
| **Phase sync** | Tool contract preservation | No tool changes | `test_checkout_preserves_phase_sync` |
| **#136 compat** | D1: Descriptive errors | Adapter messages parseable | Future catalog migration |

---

## 11. Key Takeaways

### 11.1. What #137 Delivers

1. **Adapter Fix:** GitAdapter.checkout() supports remote-tracking refs
2. **Backward Compatible:** Tool contract unchanged (phase + parent output)
3. **Performance:** Fast path preserved (no remote lookup for local)
4. **Clear Errors:** Descriptive messages per scenario

### 11.2. What #137 Does NOT Deliver

1. ❌ Error catalog infrastructure (Issue #136)
2. ❌ Cross-tool error taxonomy (Issue #136)
3. ❌ ErrorCatalogService (Issue #136)
4. ❌ Auto-fetch feature (deferred Q3)
5. ❌ Multi-remote support (deferred Q2)

### 11.3. Success Criteria

Design QA passes when:
- ☐ No contract conflict with tool_result.py (ToolResult.error)
- ☐ No contract conflict with git_tools.py:219 (phase sync preserved)
- ☐ No scope creep into #136 implementation
- ☐ All decisions traceable to planning S1-S5
- ☐ Fast path invariant testable (mock.assert_not_called)
- ☐ Human reviewer approval

**Next Phase:** TDD implementation per planning.md (4 cycles)

---

## Related Documentation

- [research.md](research.md) - Alternatives analyzed
- [planning.md](planning.md) - TDD cycles, scenarios S1-S5, decisions Q2/Q3
- [tool_result.py](../../../mcp_server/tools/tool_result.py) - ToolResult contract
- [git_tools.py](../../../mcp_server/tools/git_tools.py#L219) - Current GitCheckoutTool

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|  
| 1.0 | 2026-02-14T14:00:00Z | Agent | Initial design with #136 alignment |
| 2.0 | 2026-02-14T15:00:00Z | Agent | QA fixes: ToolResult.error contract, scope clarity, #136 deferral, traceability to S1-S5, non-goals |
