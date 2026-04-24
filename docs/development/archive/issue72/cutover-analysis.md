# Issue #72: Legacy Template Cutover Analysis

**Status:** Analysis Complete  
**Date:** 2026-01-23  
**Context:** Post-TDD implementation review  
**Related:** [planning.md](planning.md), [design.md](design.md)

---

## Executive Summary

**Finding:** Current TDD implementation (commits c0997a3..2ee9228) creates a **forceful cutover** that breaks all existing scaffolding functionality due to template path mismatch.

**Root Cause:** `TemplateScaffolder` now defaults to `mcp_server/scaffolding/templates/` but `artifacts.yaml` still references legacy paths like `"components/dto.py.jinja2"`.

**Impact:** All 24 legacy artifact types fail with `FileNotFoundError`.

**Proposed Solution:** Complete the cutover by creating concrete tier templates and removing legacy templates entirely.

---

## Problem Analysis

### Current State (commit 2ee9228)

**What EXISTS:**
```
mcp_server/templates/               ← LEGACY (24 templates)
├── components/dto.py.jinja2
├── components/worker.py.jinja2
└── documents/design.md.jinja2

mcp_server/scaffolding/templates/  ← NEW (6 base templates)
├── tier0_base_artifact.jinja2
├── tier1_base_code.jinja2
└── tier2_base_python.jinja2
```

**What BREAKS:**
```python
# TemplateScaffolder now uses:
template_root = get_template_root()  
# → Returns: mcp_server/scaffolding/templates/

# artifacts.yaml says:
template_path: "components/dto.py.jinja2"

# Result:
FileNotFoundError: components/dto.py.jinja2 not found in 
  mcp_server/scaffolding/templates/
```

**Affected Artifacts:** ALL 24 legacy types (dto, worker, adapter, tool, design, etc.)

### Why Tests Are Green

**Misleading Success:** The "5/5 tests passing" in commit 2ee9228 only validates:
1. `get_template_root()` configuration logic ✅
2. Environment variable override ✅
3. Fail-fast behavior ✅
4. No fallback to legacy ✅

**NOT tested:**
- ❌ Actual scaffolding of dto/worker/design
- ❌ End-to-end artifact generation
- ❌ Integration with artifacts.yaml

**Root Cause:** Unit tests use mocked renderers or hardcoded legacy paths, bypassing the new config system.

---

## Proposed Solution: Complete Cutover

### Strategy: Delete Legacy, Create Concrete Tier Templates

**Philosophy:** Embrace clean break - no backward compatibility, ground-up tier system.

**Rationale:**
- Aligns with user requirement: "GEEN LEGACY support"
- Simpler than dual-path maintenance
- Forces proper tier template design
- Eliminates technical debt immediately

### Minimal Viable Template Set

**Analysis of Test Coverage:**

**Unit Tests Use:**
- `dto` (Data Transfer Object)
- `worker` (async task processor)
- `design` (markdown document)
- `service` (service_command/query/orchestrator)
- `generic` (catch-all template)

**E2E Tests Use:**
- `dto`
- `design`

**Required Concrete Templates:** 5

```
mcp_server/scaffolding/templates/
├── tier0_base_artifact.jinja2        ✅ EXISTS
├── tier1_base_code.jinja2            ✅ EXISTS
├── tier1_base_document.jinja2        ✅ EXISTS
├── tier2_base_python.jinja2          ✅ EXISTS
├── tier2_base_markdown.jinja2        ✅ EXISTS
└── concrete/
    ├── dto.py.jinja2                 ❌ NEEDS CREATE
    ├── worker.py.jinja2              ❌ NEEDS CREATE
    ├── service_command.py.jinja2     ❌ NEEDS CREATE
    ├── generic.py.jinja2             ❌ NEEDS CREATE
    └── design.md.jinja2              ❌ NEEDS CREATE
```

---

## Work Breakdown

### Phase 1: Create Concrete Templates (5h)

**Template 1: `concrete/dto.py.jinja2`**
- **Extends:** `tier2_base_python.jinja2`
- **Content:** Pydantic BaseModel with frozen config
- **Variables:** name, description, fields[]
- **Effort:** 1h

**Template 2: `concrete/worker.py.jinja2`**
- **Extends:** `tier2_base_python.jinja2`
- **Content:** Async worker class with execute() method
- **Variables:** name, description
- **Effort:** 1h
- **Note:** Basic version without IWorkerLifecycle (matches current test usage)

**Template 3: `concrete/service_command.py.jinja2`**
- **Extends:** `tier2_base_python.jinja2`
- **Content:** Service command pattern
- **Variables:** name, description
- **Effort:** 1h

**Template 4: `concrete/generic.py.jinja2`**
- **Extends:** `tier2_base_python.jinja2`
- **Content:** Minimal class template
- **Variables:** name, description
- **Effort:** 30min

**Template 5: `concrete/design.md.jinja2`**
- **Extends:** `tier2_base_markdown.jinja2`
- **Content:** Design document structure
- **Variables:** title, issue_number, purpose, date
- **Effort:** 1h

**Phase 1 Total:** ~5h

### Phase 2: Update Configuration (30min)

**File: `.st3/artifacts.yaml`**

Update template paths for 5 artifact types:
```yaml
# BEFORE
- type_id: dto
  template_path: "components/dto.py.jinja2"

# AFTER
- type_id: dto
  template_path: "concrete/dto.py.jinja2"
```

**Changes:** 5 entries × 5min = 25min

### Phase 3: Fix Test Hardcoded Paths (1h)

**Files to update:**
```
tests/unit/scaffolders/test_template_scaffolder.py
tests/integration/mcp_server/test_scaffold_tool_execute_e2e.py
```

**Pattern:**
```python
# BEFORE (hardcoded legacy path)
template_dir = Path(__file__).parent.parent.parent / "mcp_server" / "templates"

# AFTER (use config)
from mcp_server.config.template_config import get_template_root
template_dir = get_template_root()
```

**Estimate:** 4-5 test files × 15min = 1h

### Phase 4: Delete Legacy Templates (5min)

```bash
git rm -r mcp_server/templates/
```

**Impact:** Removes 24 legacy templates (clean slate)

### Phase 5: Validation (30min)

```bash
pytest tests/unit/scaffolders/ -v
pytest tests/integration/ -k scaffold -v
```

**Fix any remaining issues** (estimate 30min buffer)

---

## Integration with Existing Planning

### Relationship to planning.md Tasks

**Current Planning Structure:**
- **Phase 1 (Foundation):** Tier 0-2 base templates ✅ **COMPLETE** (commits c0997a3..a34e8c8)
- **Phase 2 (Blockers):** Introspection, lifecycle audit, pattern inventory
- **Phase 3 (Tier 3):** Specialization templates (24h effort)
- **Phase 4 (Migration):** Refactor 24 legacy templates (24h effort)

**PROBLEM:** Phase 3 + Phase 4 assume **gradual migration** with legacy co-existence.

**NEW REALITY:** Forceful cutover already happened (commit 2ee9228) - legacy is unreachable!

### Revised Task Sequencing

**Insert NEW Phase 1.5: Concrete Template Creation**

**Position:** Between Phase 1 (base templates) and Phase 2 (blockers)

**Rationale:**
1. Phase 1 (base templates) is DONE ✅
2. Tests are broken until concrete templates exist
3. This work is INDEPENDENT of Phase 2 blockers
4. Enables test-driven validation of base templates

**Modified Critical Path:**
```
Phase 1: Base Templates (Tier 0-2)     ✅ COMPLETE
    ↓
Phase 1.5: Concrete Templates (5)      ← INSERT HERE (NEW)
    ↓
Phase 2: Blocker Resolution            ← Can proceed in parallel
    ↓
Phase 3: Tier 3 Specialization         ← Still valid (for advanced patterns)
```

### Task Mapping

**NEW Task 1.6: Create Minimal Concrete Templates**
- **Description:** Create 5 concrete templates to unblock testing
- **Input:** Test suite artifact type usage analysis
- **Output:** 5 concrete templates (dto, worker, service_command, generic, design)
- **Acceptance:** All existing unit and E2E tests pass with new templates
- **Effort:** 5h templates + 30min config + 1h test fixes + 30min validation = **7h**
- **Assignee:** Template Author
- **Priority:** **P0 (BLOCKER)** - tests currently broken
- **Dependency:** Phase 1 complete (Tier 0-2 bases exist)

**OBSOLETE Tasks (Removed):**
- ~~Task 4.1: Template Migration Script~~ (no legacy to migrate)
- ~~Task 4.2: Refactor Worker Template~~ (starts fresh with concrete template)
- ~~Task 4.3-4.5: Refactor Adapters/Tools/Services~~ (same rationale)

**Preserved Tasks (Still Valid):**
- Task 2.1: Inheritance Introspection ✅ (critical for multi-tier)
- Task 2.2: IWorkerLifecycle Audit (for future Tier 3 enhancement)
- Task 3.1-3.6: Tier 3 Specialization (advanced patterns, not MVP)

---

## Effort Recalculation

### Original Planning Estimate

```
Phase 1 (Foundation):       80h
Phase 2 (Blockers):         40h
Phase 3 (Tier 3):           60h
Phase 4 (Migration):        65h  ← OBSOLETE
Phase 5 (Integration):      16h
Phase 6 (Validation):       8h
Phase 7 (Documentation):    16h
---------------------------------------
TOTAL:                      285h (18 days)
```

### Revised Estimate

```
Phase 1 (Foundation):       80h   ✅ COMPLETE
Phase 1.5 (Concrete):       7h    ← NEW (unblock testing)
Phase 2 (Blockers):         40h   (unchanged)
Phase 3 (Tier 3):           60h   (optional - future enhancement)
Phase 4 (Migration):        0h    ← DELETED (no legacy to migrate)
Phase 5 (Integration):      8h    (reduced - simpler without dual-path)
Phase 6 (Validation):       8h    (unchanged)
Phase 7 (Documentation):    16h   (unchanged)
---------------------------------------
TOTAL:                      219h (14 days)
SAVINGS:                    -66h (-23% reduction)
```

**Critical Path Impact:**
- **Before:** Phase 1 → Phase 2 → Phase 3 → Phase 4 (sequential)
- **After:** Phase 1 → Phase 1.5 → Phase 2 || Phase 3 (parallelizable)

---

## Risk Assessment

### Risk 1: Template Variable Mismatches (MEDIUM)
**Problem:** New tier templates may expect different context variables than legacy  
**Mitigation:** Copy variable sets from legacy templates during creation  
**Fallback:** Keep legacy templates in git history for reference  
**Likelihood:** MEDIUM (tier inheritance adds complexity)  
**Impact:** +1-2h debugging if mismatch found

### Risk 2: Hidden Template Dependencies (LOW)
**Problem:** Tests might use more artifact types than analysis found  
**Mitigation:** Run tests incrementally (dto → worker → design → service → generic)  
**Fallback:** Create additional templates as needed  
**Likelihood:** LOW (grep analysis was thorough)  
**Impact:** +1h per additional template

### Risk 3: SCAFFOLD Metadata Format (LOW)
**Problem:** Tests might expect old metadata format  
**Mitigation:** Issue #120 already standardized format  
**Validation:** Check test assertions for hardcoded metadata strings  
**Likelihood:** LOW (Issue #120 completed successfully)  
**Impact:** Minimal (format is backward compatible)

### Risk 4: Test Suite Coverage Gaps (LOW)
**Problem:** Tests may not exercise all template features  
**Mitigation:** Manual smoke testing of each artifact type  
**Fallback:** Iterate on templates based on failures  
**Likelihood:** LOW (tests are comprehensive)  
**Impact:** +30min per gap found

---

## Rollback Plan

### If Cutover Fails

**Option A: Revert to Pre-Cutover State**
```bash
git revert 2ee9228  # Revert "Clean break to tier-templates"
# TemplateScaffolder uses legacy default again
# Issue #72 work preserved (tier templates still exist)
```
**Cost:** 5 minutes  
**Impact:** Back to working state, lose cutover progress

**Option B: Emergency Dual-Path Fix**
```python
# Quick patch to template_config.py
def get_template_root(use_legacy: bool = True) -> Path:
    if use_legacy:
        return Path("mcp_server/templates")
    return Path("mcp_server/scaffolding/templates")
```
**Cost:** 15 minutes  
**Impact:** Both paths work, buys time for proper fix

---

## Recommendation

### Proceed with Complete Cutover

**Why:**
1. ✅ Aligns with user requirement: "CLEAN BREAK, GEEN LEGACY"
2. ✅ Simpler than maintaining dual-path system
3. ✅ Effort reduced by 23% (66h savings) vs gradual migration
4. ✅ Tests force validation of tier template quality
5. ✅ Technical debt eliminated immediately

**Next Steps:**
1. Create concrete templates (Phase 1.5, Task 1.6) - **7h**
2. Run test suite - validate greenfield implementation
3. Delete legacy templates - commit clean slate
4. Update planning.md with revised task structure

**Success Criteria:**
- ✅ All unit tests pass (dto, worker, service, generic)
- ✅ All E2E tests pass (dto, design)
- ✅ Zero legacy template references in codebase
- ✅ Documentation reflects new structure

---

## Appendix: Template Creation Guidelines

### Concrete Template Structure

**Pattern (Python code templates):**
```jinja2
{%- extends "tier2_base_python.jinja2" -%}

{%- block imports -%}
# Artifact-specific imports
from typing import Any
{%- endblock -%}

{%- block content -%}
class {{ name }}:
    """{{ description }}."""
    
    # Artifact-specific implementation
{%- endblock -%}
```

**Pattern (Markdown document templates):**
```jinja2
{%- extends "tier2_base_markdown.jinja2" -%}

{%- block content -%}
# {{ title }}

**Status:** DRAFT  
**Date:** {{ date }}

## Purpose

{{ purpose }}

## Content

{# Document-specific sections #}
{%- endblock -%}
```

### Variable Requirements

**Minimum Required Variables (from Tier 0):**
- `artifact_type` (auto-provided by scaffolder)
- `version_hash` (computed by registry)
- `timestamp` (auto-generated)
- `output_path` (provided by user or computed)
- `format` ("python" | "markdown" | "yaml" - determines comment syntax)

**Concrete Template Variables:**
- Define in TEMPLATE_METADATA `variables.required` section
- Inherit from parent tiers automatically
- User provides via `context={}` parameter

### Testing Strategy

**Per-Template Validation:**
1. Create template file
2. Update artifacts.yaml entry
3. Run unit test for that artifact type
4. Fix any variable mismatches
5. Repeat for next template

**Incremental Approach:** dto → worker → design → service → generic
