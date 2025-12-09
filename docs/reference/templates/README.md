# docs/reference/templates/README.md
# Documentation Templates

**Status:** DEFINITIVE  
**Version:** 1.0  
**Last Updated:** 2025-11-27  

---

## Purpose

This directory contains standardized templates for all S1mpleTraderV3 documentation. Using these templates ensures consistency, maintainability, and proper cross-referencing across all docs.

## Template Hierarchy

```
BASE_TEMPLATE.md          ← Foundation (static docs inherit from this)
    │
    ├── ARCHITECTURE_TEMPLATE.md   ← System design docs (docs/architecture/)
    │
    ├── DESIGN_TEMPLATE.md         ← Pre-implementation designs (docs/development/)
    │
    │
    └── REFERENCE_TEMPLATE.md      ← Post-implementation reference (docs/reference/)

TRACKING_TEMPLATE.md      ← Living documents (TODO, STATUS, INVENTORY)
                             Does NOT inherit from BASE (different lifecycle)

Specific Component Templates:
- [python_tool.md](python_tool.md)
- [python_resource.md](python_resource.md)
- [python_service.md](python_service.md)
- [python_schema.md](python_schema.md)
- [python_interface.md](python_interface.md)

```

## Quick Reference

| Template | Use For | Location | Sections Numbered |
|----------|---------|----------|-------------------|
| [BASE_TEMPLATE.md](BASE_TEMPLATE.md) | Foundation structure | - | - |
| [ARCHITECTURE_TEMPLATE.md](ARCHITECTURE_TEMPLATE.md) | Conceptual system design | `docs/architecture/` | ✅ Yes |
| [DESIGN_TEMPLATE.md](DESIGN_TEMPLATE.md) | Pre-implementation decisions | `docs/development/` | ✅ Yes |
| [REFERENCE_TEMPLATE.md](REFERENCE_TEMPLATE.md) | API & implementation docs | `docs/reference/` | ❌ No |
| [TRACKING_TEMPLATE.md](TRACKING_TEMPLATE.md) | Progress tracking, TODOs | `docs/`, `docs/implementation/` | ❌ No |
| [AI_DOC_PROMPTS.md](AI_DOC_PROMPTS.md) | AI-assisted doc prompts | - | ❌ No |

## When to Use Which Template

```
Creating new documentation?
│
├─ Is it TRACKING progress, status, or gaps?
│  └─ YES → TRACKING_TEMPLATE.md (living document with checkboxes)
│
├─ Is it about SYSTEM DESIGN or ARCHITECTURE?
│  └─ YES → ARCHITECTURE_TEMPLATE.md
│
├─ Is it a PRE-IMPLEMENTATION design decision?
│  └─ YES → DESIGN_TEMPLATE.md
│
├─ Is it documenting EXISTING implementation?
│  └─ YES → REFERENCE_TEMPLATE.md
│
└─ Not sure?
   └─ Start with BASE_TEMPLATE.md, refine later
```

## Required Sections by Template Type

### Static Documents (BASE, ARCHITECTURE, DESIGN, REFERENCE)

| Section | Purpose |
|---------|---------|
| **Filepath (line 1)** | `# docs/path/to/file.md` - identifies file location |
| **Header** | Status, Version, Last Updated |
| **Purpose** | What the document covers and why |
| **Scope** | In scope / Out of scope with cross-references |
| **Content** | Main documentation sections |
| **Related Documentation** | Links to related docs |
| **Link definitions** | Centralized link footer |
| **Version History** | Change tracking |

### Living Documents (TRACKING_TEMPLATE)

| Section | Purpose |
|---------|---------|
| **Header** | "LIVING DOCUMENT" status, Last Updated, Update Frequency |
| **Current Focus** | What's being worked on now |
| **Quick Links** | Related tracking docs |
| **Summary** | Completion table per category |
| **Categories** | Completed / In Progress / Backlog items |
| **Related Documents** | Links to detail docs |

**Key differences:**
- No Version History (too frequent updates)
- "LIVING DOCUMENT" status instead of DRAFT → DEFINITIVE lifecycle
- Checkboxes `[ ]` and `[x]` for task tracking
- Update Frequency explicitly stated

## Status Lifecycle

```
DRAFT → PRELIMINARY → APPROVED → DEFINITIVE
  │         │            │           │
  │         │            │           └── Reflects implemented reality
  │         │            └── Ready for implementation
  │         └── Complete, pending review
  └── Work in progress, may have [TODO] markers
```

## Link Footer Pattern

All templates use centralized link definitions:

```markdown
## Related Documentation

- **[Other Doc][other-doc]** - Description

<!-- Link definitions (hidden in preview) -->

[other-doc]: ./path/to/doc.md "Description"
```

**Benefits:**
- Single point of change when paths update
- Clean readable text
- All dependencies visible at document bottom

## Related Documentation

- **[DOCUMENTATION_MAINTENANCE.md][doc-maintenance]** - Meta-rules for documentation
- **[CODE_STYLE.md][code-style]** - Code documentation standards

<!-- Link definitions -->

[doc-maintenance]: ../../DOCUMENTATION_MAINTENANCE.md "Documentation maintenance guide"
[code-style]: ../../coding_standards/CODE_STYLE.md "Code style guide"

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-27 | AI | Initial template system |
