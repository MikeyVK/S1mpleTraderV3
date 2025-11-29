# docs/architecture/DOCUMENTATION_ALIGNMENT_PLAN.md
# Documentation Alignment Plan - S1mpleTraderV3

**Status:** DRAFT
**Version:** 2.0
**Last Updated:** 2025-11-29

---

## Purpose

This plan defines the approach to bring all architecture documentation into full compliance with BASE_TEMPLATE.md and ARCHITECTURE_TEMPLATE.md. The previous alignment plan (v1) addressed content issues but missed structural template requirements.

**Target audience:** Documentation maintainers and AI assistants updating docs.

## Scope

**In Scope:**
- All 20 markdown files in `docs/architecture/` (excluding README.md)
- Full template compliance (BASE + ARCHITECTURE requirements)

**Out of Scope:**
- Reference documentation → See `docs/reference/`
- Design documents → See `docs/development/`

---

## 1. Template Requirements Analysis

### 1.1 BASE_TEMPLATE.md Requirements (All docs)

| # | Requirement | Description |
|---|-------------|-------------|
| B1 | **Path Line** | First line: `# docs/architecture/{FILENAME}.md` |
| B2 | **Title Line** | Second line: `# {Title} - S1mpleTraderV3` |
| B3 | **Status** | `**Status:** DRAFT\|PRELIMINARY\|APPROVED\|DEFINITIVE` |
| B4 | **Version** | `**Version:** X.Y` |
| B5 | **Last Updated** | `**Last Updated:** YYYY-MM-DD` |
| B6 | **Purpose** | `## Purpose` section (1 paragraph: what, why, who) |
| B7 | **Scope** | `## Scope` with In Scope / Out of Scope lists |
| B8 | **Prerequisites** | `## Prerequisites` (optional - delete if none) |
| B9 | **Related Docs** | `## Related Documentation` with link definitions |
| B10 | **Version History** | `## Version History` table at end |

### 1.2 ARCHITECTURE_TEMPLATE.md Additional Requirements

| # | Requirement | Description |
|---|-------------|-------------|
| A1 | **Numbered Sections** | `## 1. Concept`, `### 1.1 Detail` format |
| A2 | **Mermaid Diagrams** | Visual architecture representations |
| A3 | **No Implementation Code** | WHAT/WHY only, link to source for HOW |
| A4 | **Constraints Table** | Optional: `## N. Constraints & Decisions` |

---

## 2. Current Compliance Audit

### 2.1 Document-by-Document Status

| Document | B1 Path | B3 Status | B4 Ver | B6 Purpose | B7 Scope | A1 Numbered | B10 History |
|----------|---------|-----------|--------|------------|----------|-------------|-------------|
| CONFIGURATION_LAYERS.md | ❌ | ❌ `Arch Found` | ❌ | ❌ `Overview` | ❌ | ❌ | ❌ |
| CORE_PRINCIPLES.md | ❌ | ❌ `Arch Found` | ❌ | ❌ `Vision` | ❌ | ❌ | ❌ |
| DATA_FLOW.md | ❌ | ❌ `Arch Found` | ❌ | ❌ `Overview` | ❌ | ❌ | ❌ |
| DTO_ARCHITECTURE.md | ❌ | ⚠️ `Design` | ✅ 2.0 | ✅ | ❌ | ✅ | ✅ |
| DTO_CORE.md | ❌ | ⚠️ `Design` | ✅ 1.0 | ✅ | ❌ | ✅ | ✅ |
| DTO_EXECUTION.md | ❌ | ⚠️ `Design` | ✅ 1.0 | ✅ | ❌ | ✅ | ✅ |
| DTO_PIPELINE.md | ❌ | ⚠️ `Design` | ✅ 1.0 | ✅ | ❌ | ✅ | ✅ |
| EVENT_ARCHITECTURE.md | ❌ | ⚠️ `Design` | ✅ 2.0 | ⚠️ `Exec Sum` | ❌ | ✅ | ✅ |
| EVENT_DRIVEN_WIRING.md | ❌ | ❌ `Arch Found` | ❌ | ❌ `Overview` | ❌ | ❌ | ❌ |
| EVENT_PERSISTENCE.md | ❌ | ⚠️ `Design` | ✅ 1.0 | ✅ | ❌ | ✅ | ✅ |
| EXECUTION_FLOW.md | ❌ | ✅ `Definitive` | ✅ 2.0 | ❌ `Exec Sum` | ❌ | ❌ | ❌ |
| LAYERED_ARCHITECTURE.md | ❌ | ❌ `Arch Found` | ❌ | ❌ `Overview` | ❌ | ❌ | ❌ |
| OBJECTIVE_DATA_PHILOSOPHY.md | ❌ | ❌ `Arch Found` | ❌ | ❌ `Exec Sum` | ❌ | ❌ | ❌ |
| PIPELINE_FLOW.md | ❌ | ✅ `DEFINITIVE` | ✅ 3.2 | ✅ | ✅ | ✅ | ✅ |
| PLATFORM_COMPONENTS.md | ❌ | ✅ `DEFINITIVE` | ✅ 2.0 | ✅ | ✅ | ⚠️ | ✅ |
| PLUGIN_ANATOMY.md | ❌ | ❌ `Arch Found` | ❌ | ❌ `Overview` | ❌ | ❌ | ❌ |
| POINT_IN_TIME_MODEL.md | ❌ | ❌ `Arch Found` | ❌ | ❌ `Core Concept` | ❌ | ❌ | ❌ |
| TRADE_LIFECYCLE.md | ❌ | ✅ `Definitive` | ✅ 2.0 | ⚠️ `Goal:` | ❌ | ✅ | ✅ |
| TRIGGER_ARCHITECTURE.md | ❌ | ✅ `DRAFT` | ✅ 0.1 | ⚠️ `Doc Purpose` | ✅ | ✅ | ✅ |
| WORKER_TAXONOMY.md | ❌ | ❌ `Arch Found` | ✅ 2.0 | ❌ `Overview` | ❌ | ❌ | ✅ |

**Legend:** ✅ Compliant | ⚠️ Minor issue | ❌ Non-compliant

### 2.2 Summary Statistics

| Requirement | Compliant | Non-Compliant |
|-------------|-----------|---------------|
| B1: Path Line | 0 (0%) | 20 (100%) |
| B3: Valid Status | 5 (25%) | 15 (75%) |
| B4: Version | 12 (60%) | 8 (40%) |
| B6: Purpose section | 6 (30%) | 14 (70%) |
| B7: Scope section | 3 (15%) | 17 (85%) |
| A1: Numbered sections | 10 (50%) | 10 (50%) |
| B10: Version History | 11 (55%) | 9 (45%) |

---

## 3. Execution Strategy

### 3.1 Prioritization

**Priority 1 - Foundation (must fix first):**
- B1: Path line (all docs)
- B3: Valid Status values (replace "Architecture Foundation", "Design")

**Priority 2 - Structure (enables consistency):**
- B4: Version line where missing
- B6: Purpose section (rename Overview/Executive Summary)
- B7: Scope section (add In/Out of Scope)

**Priority 3 - Format (polish):**
- A1: Numbered sections
- B10: Version History table

### 3.2 Batch Execution Plan

| Batch | Documents | Changes | Est. Time |
|-------|-----------|---------|-----------|
| **Batch 1** | All 20 docs | Add path line, fix Status values | 1 hour |
| **Batch 2** | 8 docs without Version | Add Version line | 30 min |
| **Batch 3** | 14 docs | Rename to Purpose + add Scope | 2 hours |
| **Batch 4** | 10 docs | Add numbered sections | 2 hours |
| **Batch 5** | 9 docs | Add Version History | 1 hour |

---

## 4. Valid Status Values

Per BASE_TEMPLATE.md, these are the only valid Status values:

| Status | Meaning |
|--------|---------|
| `DRAFT` | Work in progress, may have [TODO] markers |
| `PRELIMINARY` | Complete, pending review |
| `APPROVED` | Ready for implementation |
| `DEFINITIVE` | Reflects implemented reality |

**Status Mapping for Current Docs:**

| Current Value | Correct Value | Rationale |
|---------------|---------------|-----------|
| `Architecture Foundation` | `APPROVED` | Established concepts, not yet fully implemented |
| `Design` | `PRELIMINARY` | Design complete, awaiting implementation review |
| `Definitive` | `DEFINITIVE` | Already correct (case normalization only) |

---

## 5. Document Classification

### 5.1 Definitive (Implemented)
Documents describing implemented reality:
- PIPELINE_FLOW.md
- PLATFORM_COMPONENTS.md
- EXECUTION_FLOW.md
- TRADE_LIFECYCLE.md

### 5.2 Approved (Ready for Implementation)
Established architectural concepts:
- CORE_PRINCIPLES.md
- CONFIGURATION_LAYERS.md
- DATA_FLOW.md
- EVENT_DRIVEN_WIRING.md
- LAYERED_ARCHITECTURE.md
- OBJECTIVE_DATA_PHILOSOPHY.md
- PLUGIN_ANATOMY.md
- POINT_IN_TIME_MODEL.md
- WORKER_TAXONOMY.md

### 5.3 Preliminary (Design Complete)
Design documents awaiting validation:
- DTO_ARCHITECTURE.md
- DTO_CORE.md
- DTO_EXECUTION.md
- DTO_PIPELINE.md
- EVENT_ARCHITECTURE.md
- EVENT_PERSISTENCE.md

### 5.4 Draft (Work in Progress)
Incomplete documents:
- TRIGGER_ARCHITECTURE.md

---

## 6. Standard Header Format

Every document should have this exact header structure:

```markdown
# docs/architecture/{FILENAME}.md
# {Document Title} - S1mpleTraderV3

**Status:** {DRAFT|PRELIMINARY|APPROVED|DEFINITIVE}
**Version:** {X.Y}
**Last Updated:** {YYYY-MM-DD}

---

## Purpose

{One paragraph describing what, why, and who}

## Scope

**In Scope:**
- {Topic 1}
- {Topic 2}

**Out of Scope:**
- {Topic} → See [{DOC}](DOC.md)

---
```

---

## Related Documentation

- **[BASE_TEMPLATE.md](../reference/templates/BASE_TEMPLATE.md)** - Foundation for all docs
- **[ARCHITECTURE_TEMPLATE.md](../reference/templates/ARCHITECTURE_TEMPLATE.md)** - Architecture-specific extensions
- **[DOCUMENTATION_MAINTENANCE.md](../DOCUMENTATION_MAINTENANCE.md)** - Maintenance guidelines

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2025-11-29 | AI Assistant | Complete rewrite based on template analysis, previous plan archived |
| 1.0 | 2025-11-29 | AI Assistant | Initial alignment plan (archived) |
