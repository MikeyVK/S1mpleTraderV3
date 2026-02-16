# Migration Guide: v1.x → v2.0 (Workflow-First Commit Scopes)

**Issue:** #138  
**Date:** 2026-02-16  
**Breaking Changes:** Yes (but backward compatible until v3.0)

---

## Overview

Version 2.0 introduces **workflow-first commit scopes** to support all workflow phases (research, planning, design, tdd, integration, documentation), not just TDD phases (red/green/refactor/docs).

**Key Changes:**
- ✅ New `workflow_phase` parameter (replaces `phase`)
- ✅ Auto-detection from state.json (no parameters needed!)
- ✅ Scope encoding: `test(P_TDD_SP_RED):`, `docs(P_DOCUMENTATION):`
- ⚠️ `phase` parameter deprecated (but still works)

---

## Migration Paths

### Option 1: Zero-Change Migration (Recommended)

**Do nothing** - old syntax still works!

```python
# v1.x syntax (STILL WORKS in v2.0)
git_add_or_commit(phase="red", message="add test")
# Result: test: add test (legacy format)
```

**Backward compatibility guaranteed until v3.0.**

---

### Option 2: Auto-Detect Migration (Best Developer Experience)

**Remove phase parameter** - let auto-detection handle it!

```python
# v2.0 auto-detect (RECOMMENDED)
git_add_or_commit(message="add test")
# Result: test(P_TDD_SP_RED): add test
#         ^^^^^^^^^^^^^^^^^^^
#         Auto-detected from state.json current_phase=tdd
```

**Benefits:**
- ✅ Fewer parameters (simpler code)
- ✅ Always correct phase (synced with state.json)
- ✅ Works in ALL phases (research, planning, integration, etc.)

---

### Option 3: Explicit Migration (Maximum Control)

**Use workflow_phase parameter** for explicit control:

```python
# v2.0 explicit (FULL CONTROL)
git_add_or_commit(
    workflow_phase="tdd",
    sub_phase="red",
    message="add test"
)
# Result: test(P_TDD_SP_RED): add test
```

**Use when:**
- Running in different phase than state.json
- Override commit_type (e.g., `commit_type="fix"` instead of auto-determined "test")
- Multi-cycle TDD (use `cycle_number` parameter)

---

## Syntax Comparison

### TDD Phase Commits

| Scenario | v1.x (Deprecated) | v2.0 Auto-Detect | v2.0 Explicit |
|----------|-------------------|------------------|---------------|
| **RED** | `phase="red"` | (none) | `workflow_phase="tdd", sub_phase="red"` |
| **GREEN** | `phase="green"` | (none) | `workflow_phase="tdd", sub_phase="green"` |
| **REFACTOR** | `phase="refactor"` | (none) | `workflow_phase="tdd", sub_phase="refactor"` |
| **Output** | `test: add test` | `test(P_TDD_SP_RED): add test` | `test(P_TDD_SP_RED): add test` |

### Non-TDD Phase Commits

| Phase | v1.x | v2.0 Auto-Detect | Output |
|-------|------|------------------|--------|
| **Research** | ❌ Not supported | (none) | `docs(P_RESEARCH): document findings` |
| **Planning** | ❌ Not supported | (none) | `docs(P_PLANNING): create cycle breakdown` |
| **Design** | ❌ Not supported | (none) | `docs(P_DESIGN): add architecture diagram` |
| **Integration** | ❌ Not supported | (none) | `test(P_INTEGRATION): smoke tests` |
| **Documentation** | `phase="docs"` | (none) | `docs(P_DOCUMENTATION): update agent.md` |

**Key Insight:** v1.x only supported TDD phases. v2.0 supports **all workflow phases**.

---

## Migration Recipes

### Recipe 1: TDD Workflow

**Before (v1.x):**
```python
# RED
git_add_or_commit(phase="red", message="add test for X")

# GREEN
git_add_or_commit(phase="green", message="implement X")

# REFACTOR
git_add_or_commit(phase="refactor", message="clean up X")
```

**After (v2.0 Auto-Detect):**
```python
# RED
git_add_or_commit(message="add test for X")
# Auto-detects: workflow_phase=tdd, sub_phase inferred from commit_type

# GREEN
git_add_or_commit(message="implement X")

# REFACTOR
git_add_or_commit(message="clean up X")
```

**After (v2.0 Explicit):**
```python
# RED
git_add_or_commit(workflow_phase="tdd", sub_phase="red", message="add test for X")

# GREEN
git_add_or_commit(workflow_phase="tdd", sub_phase="green", message="implement X")

# REFACTOR
git_add_or_commit(workflow_phase="tdd", sub_phase="refactor", message="clean up X")
```

---

### Recipe 2: Documentation Workflow

**Before (v1.x):**
```python
git_add_or_commit(phase="docs", message="update README")
# Output: docs: update README
```

**After (v2.0 Auto-Detect):**
```python
git_add_or_commit(message="update README")
# Output: docs(P_DOCUMENTATION): update README
#         (when current_phase=documentation in state.json)
```

---

### Recipe 3: Research/Planning Phases

**Before (v1.x):**
```python
# ❌ NOT SUPPORTED - had to use phase="docs" (misleading)
git_add_or_commit(phase="docs", message="complete research findings")
```

**After (v2.0 Auto-Detect):**
```python
# ✅ SUPPORTED - auto-detects research phase
git_add_or_commit(message="complete research findings")
# Output: docs(P_RESEARCH): complete research findings
```

---

## Advanced Features

### Multi-Cycle TDD (New in v2.0)

```python
# Cycle 1
git_add_or_commit(
    workflow_phase="tdd",
    sub_phase="red",
    cycle_number=1,
    message="add test for feature A"
)
# Output: test(P_TDD_C1_SP_RED): add test for feature A
#                     ^^
#                     Cycle number embedded in scope

# Cycle 2
git_add_or_commit(
    workflow_phase="tdd",
    sub_phase="red",
    cycle_number=2,
    message="add test for feature B"
)
# Output: test(P_TDD_C2_SP_RED): add test for feature B
```

### Commit Type Override

```python
# Auto-determined commit_type (from workphases.yaml)
git_add_or_commit(workflow_phase="research", message="document findings")
# Output: docs(P_RESEARCH): document findings
#         ^^^^
#         Auto-determined: research phase -> docs commit_type

# Override commit_type
git_add_or_commit(
    workflow_phase="research",
    commit_type="chore",
    message="reorganize notes"
)
# Output: chore(P_RESEARCH): reorganize notes
#         ^^^^^
#         Overridden: chore instead of docs
```

---

## Error Handling

### Error 1: Both phase and workflow_phase Specified

```python
# ❌ INVALID
git_add_or_commit(
    phase="red",
    workflow_phase="tdd",
    message="test"
)
```

**Error:**
```
ValueError: Cannot specify both 'phase' (deprecated) and 'workflow_phase'. 
Use workflow_phase only.
```

**Fix:** Remove `phase` parameter:
```python
# ✅ VALID
git_add_or_commit(workflow_phase="tdd", sub_phase="red", message="test")
```

---

### Error 2: Invalid sub_phase

```python
# ❌ INVALID
git_add_or_commit(workflow_phase="tdd", sub_phase="invalid", message="test")
```

**Error:**
```
ValueError: Invalid sub_phase 'invalid' for phase 'tdd'.
Valid subphases: red, green, refactor
```

**Fix:** Use valid sub_phase from workphases.yaml:
```python
# ✅ VALID
git_add_or_commit(workflow_phase="tdd", sub_phase="red", message="test")
```

---

## Timeline

| Version | Status | Notes |
|---------|--------|-------|
| **v1.x** | Legacy | Only TDD phases supported (red/green/refactor/docs) |
| **v2.0** | Current | workflow_phase parameter, auto-detect, backward compatible |
| **v2.x** | Maintenance | `phase` parameter still works (deprecated warnings) |
| **v3.0** | Future | `phase` parameter removed (breaking change) |

**Recommendation:** Migrate to auto-detect now for smoothest v3.0 transition.

---

## Testing Your Migration

### Verification Checklist

1. **Backward Compatibility Test:**
   ```python
   git_add_or_commit(phase="red", message="old syntax test")
   # Expected: test: old syntax test (legacy format)
   ```

2. **Auto-Detect Test:**
   ```python
   # In TDD phase (state.json current_phase=tdd)
   git_add_or_commit(message="auto-detect test")
   # Expected: test(P_TDD_*): auto-detect test
   ```

3. **Explicit Test:**
   ```python
   git_add_or_commit(workflow_phase="tdd", sub_phase="red", message="explicit test")
   # Expected: test(P_TDD_SP_RED): explicit test
   ```

4. **Error Test:**
   ```python
   git_add_or_commit(phase="red", workflow_phase="tdd", message="error test")
   # Expected: ValueError (both parameters)
   ```

---

## FAQ

### Q: Do I need to migrate immediately?
**A:** No - backward compatibility until v3.0. Migrate at your own pace.

### Q: What's the benefit of auto-detect?
**A:** 
- Fewer parameters (less typing)
- Always synced with state.json (no mismatches)
- Works in ALL phases (not just TDD)

### Q: When should I use explicit workflow_phase?
**A:**
- Overriding commit_type
- Multi-cycle TDD with cycle_number
- Running in different phase than state.json

### Q: Will my old commits break?
**A:** No - commit history unaffected. Only new commits use new format.

### Q: Can I mix old and new syntax?
**A:** Yes - they work side-by-side. Gradual migration supported.

---

## Support

For questions or issues:
- **Issue Tracker:** [GitHub Issues](https://github.com/mivdnber/SimpleTraderV3/issues)
- **Related:** Issue #138 (Workflow-First Commit Scopes)
- **Documentation:** [agent.md](../../agent.md) - Phase 5 Tool Priority Matrix

---

## Summary

**TL;DR:**
1. ✅ Old syntax still works (phase parameter)
2. ✅ New syntax recommended (workflow_phase or auto-detect)
3. ✅ Auto-detect = best developer experience
4. ⚠️ phase parameter deprecated (removal in v3.0)
5. 📅 Migrate at your own pace (no rush)

**Next Steps:**
1. Review examples above
2. Test auto-detect in your workflow
3. Update agent.md references (if needed)
4. Enjoy workflow-first commit scopes! 🎉
