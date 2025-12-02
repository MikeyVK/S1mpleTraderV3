# docs/reference/templates/TRACKING_TEMPLATE.md

<!--
TRACKING TEMPLATE - For living project management documents
Version: 1.0

USAGE:
Use this template for documents that track progress, status, or gaps:
- TODO lists and roadmaps
- Implementation status dashboards  
- Gap analyses and inventory documents
- Backlog and debt tracking

KEY DIFFERENCES FROM OTHER TEMPLATES:
- No Version History (too frequent updates)
- "LIVING DOCUMENT" status (never "DEFINITIVE")
- Checkboxes and progress tables
- Current Focus section for quick orientation
- Update Frequency explicitly stated

EXAMPLES:
- docs/TODO.md
- docs/implementation/IMPLEMENTATION_STATUS.md
- docs/TODO_DOCUMENTATION.md (formerly DOCUMENTATION_INVENTORY.md)
-->

<!-- ═══════════════════════════════════════════════════════════════════════════
     HEADER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

**Status:** LIVING DOCUMENT  
**Last Updated:** {YYYY-MM-DD}  
**Update Frequency:** {Daily | Per Feature | Weekly | Monthly}

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     FOCUS SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Current Focus

{1-2 sentences describing what's currently being worked on or prioritized.
This helps readers quickly understand the current state.}

> **Quick Status:** {One-line summary with key metrics, e.g., "42/50 tests passing, 3 items in progress"}

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     NAVIGATION SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Quick Links

{Links to related tracking documents and key resources}

| Document | Purpose |
|----------|---------|
| [{RELATED_DOC_1}][doc-1] | {What it tracks} |
| [{RELATED_DOC_2}][doc-2] | {What it tracks} |

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     SUMMARY SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Summary

{High-level overview table showing completion status per category}

| Category | Done | Total | Status |
|----------|------|-------|--------|
| {Category 1} | {X} | {Y} | ✅ Complete |
| {Category 2} | {X} | {Y} | 🔄 In Progress |
| {Category 3} | {X} | {Y} | 🔴 Not Started |

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     TRACKING SECTIONS (REQUIRED - repeat for each category)
     ═══════════════════════════════════════════════════════════════════════════ -->

## {Category 1}

### ✅ Completed

- [x] {Completed item 1}
- [x] {Completed item 2}

### 🔄 In Progress

- [ ] **{In-progress item}** - {Brief context or blocker}
  - {Sub-task or detail}
  - {Another sub-task}

### 📋 Backlog

- [ ] {Future item 1}
- [ ] {Future item 2}

---

## {Category 2}

{Repeat pattern: Completed → In Progress → Backlog}

{Or use tables for metrics-focused tracking:}

| Component | Tests | Quality | Status |
|-----------|-------|---------|--------|
| {Name} | {X/Y} | {10/10} | ✅ |
| {Name} | {X/Y} | {10/10} | 🔄 |

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     RELATED DOCUMENTS SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Related Documents

- [{Detail doc 1}][detail-1] - {Relationship, e.g., "Full implementation details"}
- [{Detail doc 2}][detail-2] - {Relationship}

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     LINK DEFINITIONS
     ═══════════════════════════════════════════════════════════════════════════ -->

[doc-1]: path/to/doc1.md "Description"
[doc-2]: path/to/doc2.md "Description"
[detail-1]: path/to/detail1.md "Description"
[detail-2]: path/to/detail2.md "Description"
