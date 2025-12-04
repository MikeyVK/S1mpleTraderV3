# Documentation Maintenance Guide

## Overview

This guide ensures S1mpleTrader V3 documentation **stays modular, focused, and AI-friendly**.

**Last Updated:** November 2025

---

## Core Principles

### 1. Modular Over Monolithic

| Doc Type | Max Lines | Action When Exceeded |
|----------|-----------|---------------------|
| Standard | 300 | Split into sub-docs + create index |
| Architecture | 1000 | Split into sub-docs + create index |
| Templates | 150 | Keep focused, extract examples |

### 2. Single Source of Truth

Each concept has **ONE authoritative location**. Link to it, don't duplicate it.

- ✅ Link: `See [TDD_WORKFLOW.md](coding_standards/TDD_WORKFLOW.md)`
- ❌ Copy-paste: Same explanation in 5 files

### 3. Index-Driven Navigation

Every directory with >3 files **must have a README.md** with:
- Quick links section
- Brief description per document
- Common workflows

### 4. Iterative Documentation

Documentation is written **alongside code**, not as afterthought:
1. Write code (TDD cycle)
2. Immediately document new patterns
3. Commit docs with code changes

---

## Documentation Structure

```
docs/
├── DOCUMENTATION_MAINTENANCE.md    # ← This file (meta-rules)
├── TODO.md                         # Project roadmap
│
├── architecture/                   # System design (1000 line limit)
├── coding_standards/               # Development rules (300 line limit)
├── development/                    # Design documents
├── implementation/                 # Status tracking
└── reference/                      # Templates & examples
    ├── templates/                  # ⭐ Document templates
    │   ├── BASE_TEMPLATE.md
    │   ├── ARCHITECTURE_TEMPLATE.md
    │   ├── DESIGN_TEMPLATE.md
    │   ├── REFERENCE_TEMPLATE.md
    │   └── AI_DOC_PROMPTS.md       # AI-assisted doc prompts
    └── MAINTENANCE_SCRIPTS.md      # PowerShell maintenance scripts
```

### Directory Ownership

| Directory | Purpose | Max Lines | Update Trigger |
|-----------|---------|-----------|----------------|
| `architecture/` | System design | 1000 | New architectural pattern |
| `coding_standards/` | Development rules | 300 | New quality requirement |
| `development/` | Design documents | 300 | Design decisions |
| `implementation/` | Progress tracking | 500 | Module completion |
| `reference/` | Templates & examples | 600* | New component type |
| `reference/templates/` | Doc templates | 150 | Documentation standards change |

*Templates may exceed 300 lines due to code examples.

---

## Document Templates

**All new documentation must use templates from `docs/reference/templates/`.**

| Template | Use For | Key Features |
|----------|---------|--------------|
| [BASE_TEMPLATE.md] | Foundation | Status, Version History |
| [ARCHITECTURE_TEMPLATE.md] | `architecture/` | Numbered sections, Mermaid |
| [DESIGN_TEMPLATE.md] | `development/` | Design options, decisions |
| [REFERENCE_TEMPLATE.md] | `reference/` | API reference, examples |

**See:** [Template README](reference/templates/README.md) for decision tree.

---

## Documentation Language

**All documentation must be in English.**

- ✅ Write all `.md` files in English
- ✅ English for code comments and docstrings  
- ✅ Conversation with AI assistant: Dutch is acceptable

---

## Writing Guidelines

### First-Version Framing

Write docs as if this IS the first version. No "previously we did X" in content.

| Location | History Allowed? |
|----------|------------------|
| Content sections | ❌ No |
| Design Decisions section | ✅ "Chose A over B because..." |
| Version History (end) | ✅ Full changelog |

### Example

```markdown
## Content Section
The Origin DTO provides type-safe platform identification.

## Design Decisions
- **Enum over string:** Compiler-enforced correctness

## Version History
**v1.0 (2025-11-09):** Initial design - replaced V2 source_type strings
```

---

## Update Workflows

| Trigger | Action | Docs to Update |
|---------|--------|----------------|
| New feature | TDD cycle | IMPLEMENTATION_STATUS.md, reference doc if novel |
| Arch decision | Document decision | architecture/, link from related |
| Coding standard | Update rule | coding_standards/, update templates |
| Template improvement | Update template | reference/README.md notes change |
| Monthly cleanup | Audit sizes/duplicates | See [MAINTENANCE_SCRIPTS.md] |

**Detailed git workflow:** See [GIT_WORKFLOW.md](coding_standards/GIT_WORKFLOW.md)

---

## Decision Framework

### Should I Create a New Document?

```
NEW concept (not covered anywhere)?
├─ YES → Fits existing directory?
│   ├─ YES → Create + update README
│   └─ NO → Big enough for new dir? → Create dir + README
└─ NO → Existing doc < 250 lines?
    ├─ YES → Add section to existing
    └─ NO → Split existing, then add
```

### Link or Duplicate?

```
Information appears in multiple contexts?
├─ YES → More than 3 lines?
│   ├─ YES → Write once, link everywhere
│   └─ NO → Inline OK (e.g., "DTO must be Pydantic BaseModel")
└─ NO → Write once in most relevant location
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Copy-paste docs | Updates miss copies → conflicts | One source + links |
| Orphaned docs | Not in index → never found | Always update README |
| Stale status | Wrong test counts | Update status WITH code commits |
| Monolithic growth | 500+ lines → unusable | Split at 300 lines |
| Bare README | No guidance what to read | Add Quick Links + workflows |

---

## TODO.md Archiving

**Principle:** TODO.md stays focused on OPEN work. Completed items are archived.

### Archive Rules

| Item Status | Age | Action |
|-------------|-----|--------|
| `[ ]` Open | Any | Keep in TODO.md |
| `[x]` Completed | < 7 days | Keep in TODO.md (recent context) |
| `[x]` Completed | ≥ 7 days | Move to `docs/archive/TODO_COMPLETED.md` |
| `[-]` In Progress | Any | Keep in TODO.md |

### Archive Structure

```
docs/
├── TODO.md                         # OPEN + recent completed (7 days)
└── archive/
    └── TODO_COMPLETED.md           # All archived completed tasks
```

### Archive Format

When moving completed items to `TODO_COMPLETED.md`:

```markdown
## December 2025

- [x] **Task Name** (YYYY-MM-DD) ✅ COMPLETED
  - Commit: `abc1234`
  - Summary: Brief description of what was done
```

### Archive Trigger

Archive should be performed:
- **Weekly:** During regular maintenance
- **When TODO.md exceeds 400 lines:** Immediate archive of old completed items
- **Before major milestones:** Clean slate for new phase

### What NOT to Archive

- Open items `[ ]` - Never archive, still actionable
- Discussion items with `<details>` - Keep until resolved
- Blocked items - Keep visible until unblocked
- Items with unresolved sub-tasks - Keep until all sub-tasks complete

---

## AI-Assisted Documentation

**See:** [AI_DOC_PROMPTS.md](reference/templates/AI_DOC_PROMPTS.md)

**Workflow:**
1. **Human:** Capture intent (quick notes while coding)
2. **AI:** Expand notes using prompts
3. **Human:** Verify output against actual code
4. **Human:** Integrate with cross-references, commit

---

## Maintenance

**See:** [MAINTENANCE_SCRIPTS.md](reference/MAINTENANCE_SCRIPTS.md) for PowerShell scripts.

| Frequency | Tasks | Time |
|-----------|-------|------|
| Weekly | Status accuracy, link check | 5-10 min |
| Monthly | File sizes, duplicates, orphans | 30-45 min |
| Quarterly | Architecture alignment, templates | 2-3 hours |

---

## Emergency Fixes

**Symptoms of chaos:**
- 🔴 Multiple files > 400 lines
- 🔴 Can't find info without grep
- 🔴 Conflicting information
- 🔴 README indices outdated

**Action:** See [Emergency Cleanup Procedure](reference/MAINTENANCE_SCRIPTS.md#emergency-cleanup-procedure)

---

## Quick Reference

| Question | Answer |
|----------|--------|
| File getting large? | >300 lines → Split + update README |
| Found duplicate? | Keep ONE source, link from others |
| New component? | Update IMPLEMENTATION_STATUS.md |
| Major design change? | Document in architecture/ |
| Template improvement? | Update template, note in reference/README |
| AI writing docs? | Use [AI_DOC_PROMPTS.md], human verifies |

---

**Remember:** Documentation is CODE. Apply same standards (DRY, single source of truth, modular design).

---

## Lessons Learned

### October 2025: Initial Restructure

agent.md grew to 1657 lines → Split into 4 directories → 88% reduction (195 lines)

**Learning:** Establish 300-line limit BEFORE documents grow too large.

### November 2025: Template System

Created standardized templates (BASE → ARCHITECTURE/DESIGN/REFERENCE) for consistency.

**Learning:** Templates prevent style drift and enable predictable navigation.

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     LINK DEFINITIONS
     ═══════════════════════════════════════════════════════════════════════════ -->

[BASE_TEMPLATE.md]: reference/templates/BASE_TEMPLATE.md
[ARCHITECTURE_TEMPLATE.md]: reference/templates/ARCHITECTURE_TEMPLATE.md
[DESIGN_TEMPLATE.md]: reference/templates/DESIGN_TEMPLATE.md
[REFERENCE_TEMPLATE.md]: reference/templates/REFERENCE_TEMPLATE.md
[AI_DOC_PROMPTS.md]: reference/templates/AI_DOC_PROMPTS.md
[MAINTENANCE_SCRIPTS.md]: reference/MAINTENANCE_SCRIPTS.md
