<!-- D:\dev\SimpleTraderV3\test_renders\planning-task362-example.md -->
<!-- template=planning version=130ac5ea created=2026-02-05T22:06Z updated= -->
# task-362-template-composition-refactor

**Status:** COMPLETED  
**Version:** 1.0  
**Last Updated:** 2026-02-05

---

## Purpose

Plan de volledige refactoring van DOCUMENT-tak templates naar tier3 pattern compositie parity met CODE-tak. Alle templates moeten patterns gebruiken op ALLE merge-points in plaats van tier1 hardcoded defaults.

## Scope

**In Scope:**
Refactor 4 concrete templates (planning, research, design, architecture) om alle tier1 blocks te overriden met tier3 pattern macro calls. Update 4 tier3 patterns (related_docs, version_history, purpose_scope, prerequisites) naar tier1_base_document format. Fix 2 bugs (divider spacing, research link refs SSOT).

**Out of Scope:**
Geen wijzigingen aan reference.md (gebruikt custom header). Geen backward compatibility voor tier3 patterns (breaking changes v2.0.0 acceptabel). Geen structurele wijzigingen aan tier0/tier1/tier2 hierarchy.

## Prerequisites

Read these first:
1. docs/architecture/TEMPLATE_LIBRARY_ARCHITECTURE.md - 4-tier systeem
2. docs/design/TEMPLATE_COMPOSITION_DESIGN.md - pattern injection approach
3. mcp_server/scaffolding/templates/tier1_base_document.jinja2 - composable blocks
---

## Summary

Refactor 4 concrete DOCUMENT-tak templates (planning, research, design, architecture) to override ALL tier1 blocks with tier3 pattern macro calls, achieving compositie parity with CODE-tak. Fix bugs (divider spacing, research link refs SSOT).

---

## TDD Cycles


### Cycle 1: 

**Goal:** 

**Tests:**

**Success Criteria:**



### Cycle 2: 

**Goal:** 

**Tests:**

**Success Criteria:**



### Cycle 3: 

**Goal:** 

**Tests:**

**Success Criteria:**



### Cycle 4: 

**Goal:** 

**Tests:**

**Success Criteria:**


## Related Documentation
- **[TEMPLATE_LIBRARY_ARCHITECTURE.md][related-1]**
- **[TEMPLATE_COMPOSITION_DESIGN.md][related-2]**

<!-- Link definitions -->

[related-1]: TEMPLATE_LIBRARY_ARCHITECTURE.md
[related-2]: TEMPLATE_COMPOSITION_DESIGN.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-05 | Agent | Initial draft |