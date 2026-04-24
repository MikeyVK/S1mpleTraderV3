# Template Inheritance Analysis: SCAFFOLD Metadata Strategy

**Date:** 2026-01-22  
**Issue:** #121 Pre-Phase 0 blocker  
**Discovery:** User insight on base template inheritance

---

## Key Insight

**Original analysis:** Update all 22 templates individually  
**User insight:** Use template inheritance - update base templates!  
**Reality:** Mixed approach needed (11 use extends, 11 standalone)

---

## Template Architecture

### Base Templates (3)

Templates that other templates inherit from via `{% extends %}`:

1. **`base/base_component.py.jinja2`**
   - Used by: generic.py, interface.py, resource.py, schema.py, service_*.py (3x), tool.py
   - **Child templates:** 9

2. **`base/base_document.md.jinja2`**
   - Used by: architecture.md, reference.md
   - **Child templates:** 2

3. **`base/base_test.py.jinja2`**
   - Used by: (none found - orphaned base?)
   - **Child templates:** 0

**Total children using extends:** 11 templates

### Standalone Templates (11)

Templates that DON'T use `{% extends %}` (inline everything):

**Components (5):**
- adapter.py
- dto.py ← HAS metadata already ✅
- worker.py
- dto_test.py
- worker_test.py

**Documents (5):**
- commit-message.txt ← HAS metadata already ✅
- design.md
- generic.md ← Used for research docs!
- tracking.md
- integration_test.py

**Tests (1):**
- integration_test.py

---

## Current State Matrix

| Template | Extends Base? | Has SCAFFOLD? | Needs Update? |
|----------|---------------|---------------|---------------|
| **BASE TEMPLATES** ||||
| base_component.py | N/A | ❌ | ✅ **YES** (affects 9 children) |
| base_document.md | N/A | ❌ | ✅ **YES** (affects 2 children) |
| base_test.py | N/A | ❌ | ⚠️ Orphaned (no children) |
| **EXTENDS BASE** ||||
| generic.py | ✅ base_component | ❌ | ❌ NO (inherits from base) |
| interface.py | ✅ base_component | ❌ | ❌ NO (inherits from base) |
| resource.py | ✅ base_component | ❌ | ❌ NO (inherits from base) |
| schema.py | ✅ base_component | ❌ | ❌ NO (inherits from base) |
| service_command.py | ✅ base_component | ❌ | ❌ NO (inherits from base) |
| service_orchestrator.py | ✅ base_component | ❌ | ❌ NO (inherits from base) |
| service_query.py | ✅ base_component | ❌ | ❌ NO (inherits from base) |
| tool.py | ✅ base_component | ❌ | ❌ NO (inherits from base) |
| architecture.md | ✅ base_document | ❌ | ❌ NO (inherits from base) |
| reference.md | ✅ base_document | ❌ | ❌ NO (inherits from base) |
| **STANDALONE** ||||
| dto.py | ❌ | ✅ | ❌ NO (done) |
| commit-message.txt | ❌ | ✅ | ❌ NO (done) |
| adapter.py | ❌ | ❌ | ✅ **YES** |
| worker.py | ❌ | ❌ | ✅ **YES** |
| dto_test.py | ❌ | ❌ | ✅ **YES** |
| worker_test.py | ❌ | ❌ | ✅ **YES** |
| design.md | ❌ | ❌ | ✅ **YES** |
| generic.md | ❌ | ❌ | ✅ **YES** |
| tracking.md | ❌ | ❌ | ✅ **YES** |
| integration_test.py | ❌ | ❌ | ✅ **YES** |

---

## Revised Fix Strategy

### Updates Required: 14 templates (not 22!)

**Phase 1: Base Templates (3 updates) → affects 11 children automatically**

1. ✅ `base/base_component.py.jinja2`
   - Add SCAFFOLD comment to line 1
   - All 9 children inherit automatically!

2. ✅ `base/base_document.md.jinja2`
   - Add SCAFFOLD comment to line 1
   - Both children (architecture, reference) inherit

3. ⚠️ `base/base_test.py.jinja2`
   - Add SCAFFOLD comment for consistency
   - No current children (orphaned base)

**Phase 2: Standalone Templates (9 updates)**

Standalone templates that don't use extends:
1. adapter.py
2. worker.py
3. dto_test.py
4. worker_test.py
5. design.md
6. generic.md
7. tracking.md
8. integration_test.py
9. (dto.py - ✅ done)
10. (commit-message.txt - ✅ done)

**Total work:** 3 base + 9 standalone = **12 templates** (vs original 22!)

---

## SCAFFOLD Metadata Format

### Python Templates

```jinja
# SCAFFOLD: template={{ template_id }} version={{ template_version }} created={{ scaffold_created }} path={{ output_path }}
```

**Variables needed:**
- `template_id`: From artifacts.yaml (e.g., "worker", "dto")
- `template_version`: From artifact definition
- `scaffold_created`: Timestamp when scaffolded
- `output_path`: Where file will be written

### Markdown Templates

```jinja
<!-- SCAFFOLD: template={{ template_id }} version={{ template_version }} created={{ scaffold_created }} path={{ output_path }} -->
```

**Note:** Must be FIRST line (or after frontmatter in base templates)

---

## Base Template Inheritance Flow

### Example: Worker Template (if it used extends)

**Child template:** `components/worker.py.jinja2`
```jinja
{% extends "base/base_component.py.jinja2" %}

{% block content %}
class {{ name }}(BaseWorker):
    # ...
{% endblock %}
```

**Base template:** `base/base_component.py.jinja2`
```jinja
# SCAFFOLD: template={{ template_id }} version={{ template_version }} created={{ scaffold_created }} path={{ output_path }}
"""
{% block module_name %}{{ name }}{% endblock %} - {% block description %}Component{% endblock %}.
"""

{% block content %}
# Component implementation
{% endblock %}
```

**Rendered output:**
```python
# SCAFFOLD: template=worker version=2.0 created=2026-01-22T16:00:00Z path=backend/workers/signal_worker.py
"""
SignalWorker - Detects trading signals.
"""

class SignalWorker(BaseWorker):
    # ...
```

✅ **Metadata inherited automatically!**

---

## Why Some Templates Don't Use Extends?

**Observation:** worker.py, adapter.py don't use `{% extends %}` despite base templates existing.

**Possible reasons:**
1. **Complexity:** Worker templates are highly customized (may conflict with base blocks)
2. **Legacy:** Written before base templates existed
3. **Performance:** Inline is faster than inheritance resolution
4. **Flexibility:** Easier to customize without block constraints

**Decision:** Accept mixed approach
- Use extends where beneficial (simple components, docs)
- Use standalone where needed (complex workers, adapters)
- Ensure SCAFFOLD metadata in BOTH cases

---

## Implementation Order

### Step 1: Update Base Templates (High Impact)

1. **base_component.py.jinja2** → fixes 9 templates
2. **base_document.md.jinja2** → fixes 2 templates

**Impact:** 11/22 templates fixed with 2 updates!

### Step 2: Update Standalone Templates (Completion)

1. adapter.py
2. worker.py
3. dto_test.py
4. worker_test.py
5. design.md
6. generic.md ← Urgent (used for research docs!)
7. tracking.md
8. integration_test.py
9. base_test.py (orphaned but for consistency)

**Impact:** All 22/22 templates complete

---

## Verification

### Test After Base Template Updates

```powershell
# Scaffold a tool (uses base_component)
scaffold_artifact tool name="TestTool"

# Check if SCAFFOLD metadata present
Select-String -Path "backend/tools/test_tool.py" -Pattern "SCAFFOLD:"

# Expected: SCAFFOLD metadata found
```

### Test After Standalone Updates

```powershell
# Scaffold a worker (standalone template)
scaffold_artifact worker name="TestWorker" input_dto="Input" output_dto="Output"

# Check if SCAFFOLD metadata present
Select-String -Path "backend/workers/test_worker.py" -Pattern "SCAFFOLD:"

# Expected: SCAFFOLD metadata found
```

---

## Benefit of User Insight

**Original plan:** Update 22 templates individually (~2-3h)  
**Revised plan:** Update 3 base + 9 standalone (~1-2h)  
**Savings:** 33% less work, more maintainable architecture

**Key learning:** Always check base template inheritance before mass updates!

---

## Conclusion

**User was 100% correct:** Use base templates where inheritance exists!

**Revised strategy:**
1. ✅ Update 3 base templates (affects 11 children automatically)
2. ✅ Update 9 standalone templates (no inheritance available)
3. ✅ Verify with scaffold + metadata check

**Result:** Issue #120 Phase 0 truly complete, Issue #121 unblocked