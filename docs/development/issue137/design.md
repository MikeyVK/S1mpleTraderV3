<!-- docs/development/issue137/design.md -->
<!-- template=design version=5827e841 created=2026-02-14T13:30:00Z updated=2026-02-14T14:00:00Z -->
# Issue #137: Design for Remote Branch Checkout with Config-Driven Error Handling

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-14T14:00:00Z

---

## Scope

**In Scope:**
- GitAdapter.checkout() implementation architecture
- Error code taxonomy (4 codes: NOT_CONFIGURED, NOT_FOUND, FAILED, INVALID_INPUT)
- Tool boundary error normalization pattern
- Message templates with MCP tool names
- Issue #136 alignment strategy and migration path
- API contracts for adapter and tool layers
- Data flow diagrams (normal + error flows)

**Out of Scope:**
- TDD cycle implementation details (covered in planning.md)
- Actual error_catalog.yaml file creation (Issue #136 scope)
- ErrorCatalogService implementation (Issue #136 scope)
- Orchestration layer for composite workflows (future work)
- Multi-remote support (deferred per Decision Q2)
- Auto-fetch feature (deferred per Decision Q3)

## Prerequisites

Read these first:
1. [research.md](research.md) - 3 alternatives analyzed
2. [planning.md](planning.md) - All decisions closed (v2.1)
3. Issue #136 - Error handling contract requirements
4. [Addendum 3.8](../../../docs/system/addendums/Addendum_%203.8%20Configuratie%20en%20Vertaal%20Filosofie.md) - Config First principle

---

## 1. Context & Requirements

### 1.1. Problem Statement

GitAdapter.checkout() only checks local branches (self.repo.heads), causing ExecutionError when attempting to checkout remote-only branches. Requires architectural solution that: 

1. Enables remote-tracking ref lookup without breaking local fast path
2. Provides agent-friendly error messages with explicit MCP tool names
3. Aligns with Issue #136 error handling contract and Config First principle

### 1.2. Requirements

**Functional:**
- ✅ git_checkout('feature/x') succeeds when only origin/feature/x exists (after git_fetch)
- ✅ Local tracking branch automatically created with upstream set to origin remote-tracking ref
- ✅ Input normalization: git_checkout('origin/feature/x') strips prefix and checks 'feature/x'
- ✅ Local branch checkout unaffected (fast path: no remote lookup)
- ✅ Error messages include explicit MCP tool names for agent recovery
- ✅ All errors raised as ExecutionError in adapter, normalized to ToolResult in tool

**Non-Functional:**
- ✅ Performance: Local checkout must NOT trigger remote lookup (fast path regression protection)
- ✅ SRP: Adapter handles git logic, tool handles MCP contract conversion
- ✅ Maintainability: Error handling pattern reusable for Issue #136 migration
- ✅ Agent-Friendly: Error hints must contain actionable MCP tool names (not UI instructions)
- ✅ Config First: Error codes and templates structured for future YAML migration
- ✅ Backward Compatibility: No API changes to checkout() signature

### 1.3. Constraints

- Only 'origin' remote supported (Decision Q2 from planning.md)
- Requires git_fetch pre-run for fresh remote-tracking refs (until Q3 auto-fetch decided)
- GitPython library constraints: origin.refs are local remote-tracking refs (no network call)
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
- ✅ Fast path preserved

**Cons:**
- ❌ Slightly more complex logic
- ❌ Two check operations

### 2.2. Option B: Parametric Control (REJECTED)

Add fetch: bool parameter to checkout method

**Pros:**
- ✅ Explicit control
- ✅ Clear semantics

**Cons:**
- ❌ API change breaks existing callers
- ❌ More complexity in tool layer

### 2.3. Option C: Dedicated Method (REJECTED)

New checkout_remote() method separate from checkout()

**Pros:**
- ✅ Cleanest separation
- ✅ No existing behavior changes

**Cons:**
- ❌ API proliferation
- ❌ Confusing for users (which method to use?)

---

## 3. Chosen Design

**Decision:** Implement Alternative A (Sequential Fallback) with tool boundary error normalization and config-ready message templates, preparing for Issue #136 error_catalog.yaml migration without premature abstraction.

**Rationale:** Sequential Fallback preserves backward compatibility and fast path performance. Tool boundary normalization aligns with SRP (adapters throw domain errors, tools convert to MCP contract). Config-ready templates follow Config First principle while deferring full catalog infrastructure to Issue #136's dedicated error handling focus.

### 3.1. Key Design Decisions

| Decision ID | Question | Decision | Rationale |
|-------------|----------|----------|-----------|
| **Q3** | Auto-fetch behavior | NO auto-fetch - primary tools maintain SRP | Aligns with Config First: tools are atomic, orchestration layer (future) handles composite workflows. Predictable behavior, no hidden network calls. |
| **D1** | Error normalization location | Tool boundary (GitCheckoutTool.execute()) | Issue #136 principle: adapters throw domain errors, tools convert to MCP contract. Clean separation, supports future error_catalog.yaml migration. |
| **D2** | error_catalog.yaml timing | Prepare for migration: use consistent pattern in code, defer catalog file to Issue #136 | Separation of concerns: #137 = adapter fix, #136 = error infrastructure. Aligned architecture without premature abstraction. |
| **D3** | Error hint format | Message templates with explicit MCP tool names | Config First preparation: hints readable now, easily migratable to template format ('{fetch_tool}') when error_catalog.yaml lands. |

---

## 4. Architecture Overview

### 4.1. Layered Responsibility

```
┌────────────────────────────────────────────────────────────┐
│ MCP Client (Agent or Human)                                │
│   - Receives ToolResult(success, error_code, hint)         │
│   - Parses hint for recovery tools ("git_fetch", ...)      │
└────────────────────────────────────────────────────────────┘
                            │
                            │ ToolResult
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ TOOL BOUNDARY: GitCheckoutTool.execute()                   │
│   RESPONSIBILITY: MCP Contract Conversion                  │
│   - Normalize ExecutionError → ToolResult                  │
│   - Classify error → error_code (GIT_*)                    │
│   - Format hint with MCP tool names                        │
└────────────────────────────────────────────────────────────┘
                            │
                            │ ExecutionError
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ ADAPTER LAYER: GitAdapter.checkout()                       │
│   RESPONSIBILITY: Git Operations (Domain Logic)            │
│   - Check local branches (fast path)                       │
│   - Check remote-tracking refs (fallback)                  │
│   - Create tracking branch                                 │
│   - Raise ExecutionError(descriptive_message) on failure   │
└────────────────────────────────────────────────────────────┘
```

**Key Principle:** Clean separation between domain logic (adapter) and MCP contract (tool).

### 4.2. Sequential Fallback Flow

```python
# Pseudo-code for GitAdapter.checkout()
def checkout(branch_name: str) -> None:
    # Step 1: Input normalization
    normalized = branch_name.removeprefix("origin/")
    
    # Step 2: Fast path - check local branches
    if normalized in self.repo.heads:
        self.repo.heads[normalized].checkout()  # ← NO remote access
        return
    
    # Step 3: Fallback - check remote-tracking refs
    try:
        origin = self.repo.remote("origin")  # May raise ValueError
    except ValueError:
        raise ExecutionError("Origin remote not configured")
    
    # Step 4: Search remote-tracking refs
    remote_ref_name = f"origin/{normalized}"
    remote_ref = next((ref for ref in origin.refs if ref.name == remote_ref_name), None)
    
    if remote_ref is None:
        raise ExecutionError(
            f"Branch {normalized} does not exist (checked: local, origin)"
        )
    
    # Step 5: Create local tracking branch
    local_branch = self.repo.create_head(normalized, remote_ref)
    local_branch.set_tracking_branch(remote_ref)
    local_branch.checkout()
```

---

## 5. Q3 Resolution: Auto-Fetch Decision

### 5.1. Decision: NO Auto-Fetch

**Rationale:**
- **SRP:** Primary tools stay atomic (single responsibility)
- **Config First:** Orchestration layer (future) handles composite workflows
- **Predictable:** No hidden network calls
- **Performance:** Avoids latency on every remote checkout

### 5.2. Implications

| Aspect | Impact |
|--------|--------|
| **User workflow** | Must run `git_fetch` before checkout for fresh refs |
| **Error handling** | Clear error message with explicit recovery tool name |
| **Future work** | Orchestration layer can auto-sequence `git_fetch` + `git_checkout` |
| **Documentation** | Docstring must document `git_fetch` prerequisite |

### 5.3. Error Message Strategy

❌ **Vague:** "Branch not found. Try fetching."

✅ **Agent-Friendly:** "Branch feature/x does not exist (checked: local, origin). Run 'git_fetch' tool to update remote-tracking refs."

**Why:** Agent can parse tool name and execute directly. No ambiguity.

---

## 6. Error Code Taxonomy

### 6.1. Error Codes (Ready for Issue #136 Migration)

| Error Code | Category | Severity | Trigger Scenario |
|------------|----------|----------|------------------|
| **GIT_REMOTE_NOT_CONFIGURED** | configuration | error | `origin` remote not in repo config |
| **GIT_BRANCH_NOT_FOUND** | not_found | error | Branch missing after checking local + remote |
| **GIT_CHECKOUT_FAILED** | execution | error | Unexpected Git error during checkout |
| **GIT_INVALID_BRANCH_NAME** | validation | error | Branch name contains invalid characters (future) |

### 6.2. Message Templates (Config-Ready)

**Pattern:** Each error has:
1. **Message template** - Human-readable error description
2. **Hint template** - Actionable recovery with explicit MCP tool names
3. **Recovery tools list** - Tool names for future orchestration

```python
# In-code structure (Issue #136 will move to YAML)
ERROR_SPECS = {
    "GIT_REMOTE_NOT_CONFIGURED": {
        "message_template": "Origin remote not configured",
        "hint_template": "Configure origin with: git remote add origin <url>",
        "recovery_tools": [],  # Manual intervention required
    },
    "GIT_BRANCH_NOT_FOUND": {
        "message_template": "Branch {branch_name} does not exist (checked: {checked_locations})",
        "hint_template": "Run 'git_fetch' tool to update remote-tracking refs, or use 'git_list_branches' tool to see available branches",
        "recovery_tools": ["git_fetch", "git_list_branches"],
    },
    "GIT_CHECKOUT_FAILED": {
        "message_template": "Failed to checkout {branch_name}: {error_detail}",
        "hint_template": "Check repository state with 'git_status' tool",
        "recovery_tools": ["git_status"],
    },
}
```

**Issue #136 Migration Path:** Replace dict with `error_catalog_service.get_error_spec(code)`.

---

## 7. Tool Boundary Implementation

**GitCheckoutTool.execute()** normalizes ExecutionError → ToolResult:

```python
def execute(self, branch: str) -> ToolResult:
    try:
        self.git_adapter.checkout(branch)
        return ToolResult(success=True, message=f"Checked out {branch}")
    except ExecutionError as e:
        error_code = self._classify_error(e)
        hint = ERROR_SPECS[error_code]["hint_template"]
        return ToolResult(success=False, error_code=error_code, message=str(e), hint=hint)
```

**SRP:** Adapter throws domain errors, tool converts to MCP contract.

---

## 8. Implementation Summary

**GitAdapter.checkout() changes:**
1. Normalize input (strip `origin/` prefix)
2. Fast path: check local first (NO remote call)
3. Fallback: check remote-tracking refs
4. Create tracking branch if found
5. Raise descriptive ExecutionError

**Tool boundary changes:**
1. Add ERROR_SPECS dict (migrate to YAML in Issue #136)
2. Implement _classify_error() method
3. Return ToolResult with error_code + hint

---

## 9. Issue #136 Alignment

✅ **Aligned:** Tool boundary normalization, error codes, MCP tool names in hints  
📝 **Deferred:** error_catalog.yaml file, ErrorCatalogService (Issue #136 scope)

**Migration:** When #136 lands, replace ERROR_SPECS dict with service call. Zero test changes.

---

## 10. Success Criteria

- ☐ All architecture patterns validated
- ☐ Error taxonomy complete
- ☐ Tool boundary SRP compliant
- ☐ #136 alignment verified
- ☐ Human reviewer approval

**Next:** TDD phase per planning.md (4 cycles)

---

## Related Documentation

- [research.md](research.md) - Alternatives analyzed
- [planning.md](planning.md) - TDD cycles with decisions
- Issue #136 - Error handling contract
- [Addendum 3.8](../../../docs/system/addendums/Addendum_%203.8%20Configuratie%20en%20Vertaal%20Filosofie.md) - Config First

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|  
| 1.0 | 2026-02-14 | Agent | Complete design: Q3 decision, error taxonomy, tool boundary, #136 alignment |
