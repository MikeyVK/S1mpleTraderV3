# Template Metadata Audit: Issue #120 Phase 0 Incomplete

**Date:** 2026-01-22  
**Discovered During:** Issue #121 research phase  
**Severity:** 🔴 **CRITICAL** - Blocks Issue #121 implementation

---

## Problem Statement

During Issue #121 research, we discovered that **Issue #120 Phase 0 is NOT fully implemented**. 

**Deliverable in #120 Phase 0:**
> "All scaffolded files have `template`, `version` in YAML frontmatter"

**Reality:**
- ❌ **22 of 24 templates MISSING metadata** (91% failure rate)
- ✅ Only `dto.py.jinja2` and `commit-message.txt.jinja2` have metadata
- ❌ Research docs, design docs, workers, services, tests = NO metadata

---

## Audit Results

**Templates WITH metadata (2/24):**
1. ✅ `dto.py.jinja2` - HAS SCAFFOLD metadata
2. ✅ `commit-message.txt.jinja2` - HAS SCAFFOLD metadata

**Templates MISSING metadata (22/24):**

**Components (10 templates):**
- ❌ `base_component.py.jinja2`
- ❌ `adapter.py.jinja2`
- ❌ `dto_test.py.jinja2`
- ❌ `generic.py.jinja2`
- ❌ `interface.py.jinja2`
- ❌ `resource.py.jinja2`
- ❌ `schema.py.jinja2`
- ❌ `service_command.py.jinja2`
- ❌ `service_orchestrator.py.jinja2`
- ❌ `service_query.py.jinja2`
- ❌ `tool.py.jinja2`
- ❌ `worker.py.jinja2`
- ❌ `worker_test.py.jinja2`

**Documents (6 templates):**
- ❌ `base_document.md.jinja2`
- ❌ `architecture.md.jinja2`
- ❌ `design.md.jinja2`
- ❌ `generic.md.jinja2` ← Used for research docs!
- ❌ `reference.md.jinja2`
- ❌ `tracking.md.jinja2`

**Tests (2 templates):**
- ❌ `base_test.py.jinja2`
- ❌ `integration_test.py.jinja2`
- ❌ `unit_test.py.jinja2`

---

## Impact Analysis

### Issue #120 Phase 0 Deliverable

**Claim:** "All scaffolded files have template metadata"  
**Reality:** Only 8% of templates implemented  
**Status:** ❌ **INCOMPLETE**

### Issue #121 Blocking Issues

**Pre-Phase 0: Discovery Tool**
- ✅ Can discover DTO files
- ❌ **CANNOT discover 91% of scaffolded files**
- ❌ query_file_schema() will return "non-scaffolded" for workers, services, docs, tests
- ❌ Unified architecture (#120 + #121) is broken at template level

**Use Case Failures:**

**Scenario: Agent wants to edit research document**
```python
# Agent query:
schema = query_file_schema("docs/development/issue121/research.md")

# Expected (if metadata present):
{
  "file_type": "scaffolded",
  "template_id": "research",
  "template_version": "1.0",
  "edit_capabilities": ["ScaffoldEdit", ...]
}

# Actual (metadata missing):
{
  "file_type": "non-scaffolded",  # ❌ Wrong!
  "edit_capabilities": ["TextEdit"]  # ❌ Misses scaffold capabilities!
}
```

**Ironic Problem:**
- The research document we just created to justify discovery tool
- Has NO metadata that discovery tool would use
- Document about discovery is not discoverable! 😅

---

## Root Cause Analysis

**Why only DTO and commit-message have metadata?**

Hypothesis: These were the first templates updated during Phase 0 implementation, but the rollout was incomplete.

**Evidence from template header (dto.py.jinja2):**
```jinja
# SCAFFOLD: template=dto version=1.0 created={{ created_at }} path={{ output_path }}
```

**Missing from generic.md.jinja2:**
```jinja
# {{ title }} - S1mpleTraderV3

<!--
GENERATED DOCUMENT  ← This is NOT the SCAFFOLD format!
Template: generic.md.jinja2
Type: {{ doc_type | default('Generic') }}
-->
```

**What should be:**
```jinja
<!-- SCAFFOLD: template=generic version=1.0 created={{ created_at }} path={{ output_path }} -->
```

---

## Required Fix

### Option A: Complete Issue #120 Phase 0 (RECOMMENDED)

**Scope:** Add SCAFFOLD metadata to ALL 22 templates

**For Python templates:**
```jinja
# SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created_at }} path={{ output_path }}
```

**For Markdown templates:**
```jinja
<!-- SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created_at }} path={{ output_path }} -->
```

**Effort:** ~2-3 hours (22 templates to update + tests)

**Benefit:**
- ✅ Issue #120 Phase 0 actually complete
- ✅ Issue #121 can proceed without blockers
- ✅ Unified architecture works as designed

### Option B: Reduce Issue #121 Scope

**Scope:** Only support discovery for DTO files

**Downside:**
- ❌ Limited value (only 1 artifact type)
- ❌ Breaks unified architecture vision
- ❌ Tech debt: partial implementation
- ❌ Doesn't solve agent editing workflows for docs, workers, services

**NOT RECOMMENDED**

---

## Decision Required

**Question:** Should we fix Issue #120 Phase 0 before proceeding with Issue #121?

**Recommendation:** ✅ **YES**

**Rationale:**
1. Issue #121 depends on #120 Phase 0 being complete
2. Current state blocks 91% of discovery tool use cases
3. Quick fix (2-3h) vs long-term tech debt
4. Validates #120 Phase 0 deliverable claim

**Action:**
1. Create mini-issue or subtask: "Complete Issue #120 Phase 0 - Add metadata to all templates"
2. Update all 22 templates with SCAFFOLD comment
3. Verify with audit script
4. THEN proceed with Issue #121 Pre-Phase 0

---

## Verification Script

```powershell
# Check all templates for SCAFFOLD metadata
Get-ChildItem -Recurse -Path mcp_server\templates -Filter "*.jinja2" | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -match 'SCAFFOLD:') {
        Write-Host "✅ $($_.Name): HAS metadata" -ForegroundColor Green
    } else {
        Write-Host "❌ $($_.Name): MISSING metadata" -ForegroundColor Red
    }
}

# Expected: All templates show ✅
```

---

## Conclusion

**Finding:** Issue #120 Phase 0 is only 8% complete (2/24 templates)

**Impact:** Blocks Issue #121 Pre-Phase 0 (discovery tool)

**Recommendation:** Complete #120 Phase 0 metadata rollout before starting #121

**Next Steps:**
1. User decision: Fix #120 Phase 0 now or defer?
2. If fix: Create task for 22 template updates
3. If defer: Reduce #121 scope to DTO-only discovery

**Status:** 🔴 BLOCKED - Waiting for decision