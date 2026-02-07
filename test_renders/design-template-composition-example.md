<!-- D:\dev\SimpleTraderV3\test_renders\design-template-composition-example.md -->
<!-- template=design version=5827e841 created=2026-02-05T22:07Z updated= -->
# template-composition-refactor-design

**Status:** APPROVED  
**Version:** 1.0  
**Created:** 2026-02-05  
**Last Updated:** 2026-02-05  
**Implementation Phase:** green

---

## Purpose

Design refactoring approach for CODE-tak compositie parity in DOCUMENT-tak templates.

## Scope

**In Scope:**
4 templates, 4 patterns, tier1 blocks, tier2 link_definitions, 2 bugfixes

**Out of Scope:**
No reference.md changes. No tier0/1/2 structural changes. No new patterns/blocks. No v2.0.0 backward compat.

## Prerequisites

Read these first:
1. jinja2-composition-research.md
2. template-library-architecture.md
3. tier1_base_document v4.0.0 understanding
---

## 1. Context & Requirements

### 1.1. Problem Statement

DOCUMENT-tak templates only use patterns for header, defaulting to tier1 hardcoded content for all other sections. CODE-tak uses pattern injection on ALL merge-points. Need compositie parity.

### 1.2. Requirements

**Functional:**
- [ ] Refactor 4 templates (planning, research, design, architecture)
- [ ] Override 5 blocks: purpose_section, scope_section, prerequisites_section, related_docs_section, version_history_section
- [ ] Update 4 tier3 patterns to match tier1 signatures
- [ ] Fix 2 bugs (divider spacing, research link refs SSOT)

**Non-Functional:**
- [ ] Clean markdown output (no double blank lines, correct divider spacing)
- [ ] SSOT for context variables (no bullets/link defs mismatches)
- [ ] Validation via test_task36_comprehensive_rendering.py
- [ ] Version bump tier3 patterns to v2.0.0 (breaking change)

### 1.3. Constraints

['Backward compatibility not required (v2.0.0 breaking changes OK)', 'No structural changes to tier0/tier1/tier2 hierarchy', 'Must maintain clean markdown output (whitespace control)', 'Must preserve SSOT for context variables']
---

## 2. Design Options

### 2.1. Option A: Optional Override

tier1 blocks remain empty. Concrete templates MUST override or error. Enforces discipline but breaks backward compatibility.

**Pros:**

**Cons:**

### 2.2. Option B: Mandatory Override (chosen)

tier1 blocks have defaults. Concrete templates SHOULD override with patterns. Backward compatible, pragmatic.

**Pros:**

**Cons:**

### 2.3. Option C: Empty Blocks

tier1 blocks completely empty (no default content). Concrete templates inject patterns or leave blank.

**Pros:**

**Cons:**
---

## 3. Chosen Design

**Decision:** Mandatory Override Pattern: All concrete templates MUST override all 5 major tier1 blocks (purpose, scope, prerequisites, related_docs, version_history) with tier3 pattern macro calls. tier1 blocks keep default content for backward compatibility with non-compositie templates.

**Rationale:** Mandatory Override balances enforcement with pragmatism. Concrete templates explicitly inject patterns while tier1 maintains backward compatible defaults.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Mandatory block override | Balances enforcement with backward compatibility. Concrete templates explicit about pattern usage. |
| tier3 patterns v2.0.0 alignment | Patterns must match tier1 block signatures for seamless injection. |
| Whitespace control discipline | Strip markers ({%- -%}) critical for clean markdown divider/section spacing. |
| SSOT for context variables | Patterns normalize variable choice (e.g., references vs related_docs) to prevent mismatches. |

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