# Documentation Alignment Plan

**Status:** ACTIVE
**Version:** 1.0
**Created:** 2025-11-29
**Last Updated:** 2025-11-29

---

## 1. Purpose

This plan defines the phased approach to align all architecture documentation with:
- **First-Version Framing**: Write as if V3 IS the first version (no V2 references)
- **ARCHITECTURE_TEMPLATE**: Consistent structure across all docs
- **Line Limits**: Max 1000 lines for architecture docs
- **Single Source of Truth**: No duplication, proper cross-references

**Guiding Principle:** V3 is built from scratch. Documentation should describe the current architecture, not migration history.

---

## 2. Current State Analysis

### 2.1 Document Inventory (22 documents, ~12,000 lines)

| Document | Lines | Template | Status |
|----------|-------|----------|--------|
| `ARCHITECTURAL_SHIFTS.md` | 248 | ❌ | V2→V3 migration doc - **TO ARCHIVE** |
| `ARCHITECTURE_GAPS.md` | 3134 | ❌ | Over limit - **TO TRIAGE** |
| `ASYNC_IO_ARCHITECTURE.md` | 997 | ⚠️ | Near limit, needs review |
| `CONFIGURATION_LAYERS.md` | 416 | ❌ | Pre-template (2025-10-29) |
| `CORE_PRINCIPLES.md` | 222 | ❌ | Pre-template, minor update |
| `DATA_FLOW.md` | 496 | ❌ | Pre-template, TickCache terminology |
| `DTO_ARCHITECTURE.md` | 1423 | ❌ | **Over limit** - TO SPLIT |
| `EVENT_ARCHITECTURE.md` | 1163 | ⚠️ | Over limit |
| `EVENT_DRIVEN_WIRING.md` | 487 | ❌ | Pre-template, TickCache terminology |
| `EXECUTION_FLOW.md` | 385 | ✅ | Recently revised |
| `LAYERED_ARCHITECTURE.md` | 379 | ❌ | Pre-template |
| `LOGENRICHER_DESIGN.md` | 663 | ⚠️ | Preliminary design |
| `OBJECTIVE_DATA_PHILOSOPHY.md` | 325 | ❌ | Pre-template |
| `PIPELINE_FLOW.md` | 662 | ✅ | Recently revised |
| `PLATFORM_COMPONENTS.md` | 268 | ✅ | Recently revised |
| `PLUGIN_ANATOMY.md` | 538 | ❌ | Pre-template |
| `POINT_IN_TIME_MODEL.md` | 355 | ❌ | Pre-template, TickCache terminology |
| `README.md` | 138 | N/A | Index - needs update |
| `REVISION_PLAN.md` | 249 | N/A | Meta-tracking - **TO ARCHIVE** |
| `TRADE_LIFECYCLE.md` | 317 | ✅ | Recently revised |
| `TRIGGER_ARCHITECTURE.md` | 260 | ✅ | Recently created (DRAFT) |
| `WORKER_TAXONOMY.md` | 397 | ✅ | Recently revised |

### 2.2 Problem Categories

| Category | Documents | Issue |
|----------|-----------|-------|
| V2 Migration Content | `ARCHITECTURAL_SHIFTS.md` | Entire doc is "was/is" comparison |
| Meta-Tracking | `REVISION_PLAN.md` | Not architecture, tracking doc |
| Over Line Limit | `ARCHITECTURE_GAPS.md`, `DTO_ARCHITECTURE.md`, `EVENT_ARCHITECTURE.md` | >1000 lines |
| Pre-Template Format | 10 documents | Missing Status, Version, numbered sections |
| Stale Terminology | `DATA_FLOW.md`, `POINT_IN_TIME_MODEL.md`, `EVENT_DRIVEN_WIRING.md` | TickCache instead of StrategyCache |

---

## 3. Execution Phases

### Phase 1: Archive Migration Documents
**Goal:** Remove V2→V3 migration content from active architecture
**Effort:** 30 min
**Commit:** Single commit

| Task | Document | Action |
|------|----------|--------|
| 1.1 | `ARCHITECTURAL_SHIFTS.md` | Move to `docs/development/#Archief/` |
| 1.2 | `REVISION_PLAN.md` | Move to `docs/development/#Archief/` |
| 1.3 | `README.md` | Remove references to archived docs |
| 1.4 | All docs | Search & remove links to archived docs |

**Completion Criteria:**
- [ ] Both docs in `#Archief/` folder
- [ ] No broken links in architecture docs
- [ ] README.md reading order updated

---

### Phase 2: Triage ARCHITECTURE_GAPS.md
**Goal:** Extract actionable items, archive historical discussions
**Effort:** 1-2 hours
**Commit:** Single commit

| Task | Action |
|------|--------|
| 2.1 | Review all gaps - identify OPEN vs RESOLVED |
| 2.2 | Extract OPEN items → `docs/TODO.md` (new section) |
| 2.3 | Archive full document → `docs/development/#Archief/` |
| 2.4 | Update any docs referencing ARCHITECTURE_GAPS.md |

**Completion Criteria:**
- [ ] Open gaps tracked in TODO.md
- [ ] ARCHITECTURE_GAPS.md archived
- [ ] No broken links

---

### Phase 3: Split Over-Limit Documents
**Goal:** Bring all docs under 1000 line limit
**Effort:** 2-3 hours
**Commits:** One per document

#### 3.1 DTO_ARCHITECTURE.md (1423 lines)

| New Document | Content |
|--------------|---------|
| `DTO_ARCHITECTURE.md` | Index + Core DTOs (Origin, RunAnchor) |
| `DTO_CONTEXT.md` | Context-related DTOs |
| `DTO_EXECUTION.md` | Execution-related DTOs (TradePlan, ExecutionGroup, Order) |
| `DTO_STATE.md` | State/Ledger DTOs |

#### 3.2 EVENT_ARCHITECTURE.md (1163 lines)

| New Document | Content |
|--------------|---------|
| `EVENT_ARCHITECTURE.md` | Core event system (scoping, producers/consumers) |
| `EVENT_PERSISTENCE.md` | EventStore, durability, replay |

**Completion Criteria:**
- [ ] All docs under 1000 lines
- [ ] Each split doc has proper cross-references
- [ ] README.md updated with new docs

---

### Phase 4: Template Compliance
**Goal:** Update all pre-template docs to ARCHITECTURE_TEMPLATE format
**Effort:** 3-4 hours
**Commits:** Batch by priority

#### Priority 1: Core Concepts (read first by new developers)
| Document | Lines | Updates Needed |
|----------|-------|----------------|
| `CORE_PRINCIPLES.md` | 222 | Add Status, Version, numbered sections |
| `OBJECTIVE_DATA_PHILOSOPHY.md` | 325 | Add template header/footer |
| `POINT_IN_TIME_MODEL.md` | 355 | Template + TickCache→StrategyCache |

#### Priority 2: Data & Communication
| Document | Lines | Updates Needed |
|----------|-------|----------------|
| `DATA_FLOW.md` | 496 | Template + TickCache→StrategyCache |
| `EVENT_DRIVEN_WIRING.md` | 487 | Template + TickCache→StrategyCache |
| `CONFIGURATION_LAYERS.md` | 416 | Add template structure |

#### Priority 3: System Structure
| Document | Lines | Updates Needed |
|----------|-------|----------------|
| `LAYERED_ARCHITECTURE.md` | 379 | Add template structure |
| `PLUGIN_ANATOMY.md` | 538 | Add template structure |
| `ASYNC_IO_ARCHITECTURE.md` | 997 | Review, ensure under limit |

#### Priority 4: Preliminary/Design
| Document | Lines | Updates Needed |
|----------|-------|----------------|
| `LOGENRICHER_DESIGN.md` | 663 | Review status, may move to `development/` |

**Completion Criteria:**
- [ ] All docs have Status, Version, Last Updated
- [ ] All docs have numbered sections
- [ ] All docs have Version History at end
- [ ] TickCache→StrategyCache everywhere

---

### Phase 5: README & Navigation Update
**Goal:** Clean navigation reflecting new structure
**Effort:** 1 hour
**Commit:** Single commit

| Task | Action |
|------|--------|
| 5.1 | Update "Quick Start" reading order (no V2 references) |
| 5.2 | Update document tables with new/split docs |
| 5.3 | Update "Critical Path for New Developers" |
| 5.4 | Remove "Key Design Choices" V2 references |
| 5.5 | Verify all links work |

**New Reading Order (proposed):**
1. `CORE_PRINCIPLES.md` - Vision & Design Philosophy
2. `PIPELINE_FLOW.md` - Complete 6+1 phase pipeline
3. `POINT_IN_TIME_MODEL.md` - DTO-Centric data flow
4. `WORKER_TAXONOMY.md` - 6 worker categories
5. `PLATFORM_COMPONENTS.md` - Core infrastructure

**Completion Criteria:**
- [ ] No references to archived docs
- [ ] No V2 migration language
- [ ] All links valid

---

## 4. Progress Tracking

### Phase Status

| Phase | Status | Started | Completed | Commit(s) |
|-------|--------|---------|-----------|-----------|
| Phase 1: Archive Migration Docs | ⏳ Not Started | - | - | - |
| Phase 2: Triage ARCHITECTURE_GAPS | ⏳ Not Started | - | - | - |
| Phase 3: Split Over-Limit Docs | ⏳ Not Started | - | - | - |
| Phase 4: Template Compliance | ⏳ Not Started | - | - | - |
| Phase 5: README Update | ⏳ Not Started | - | - | - |

### Metrics

| Metric | Before | After Phase 1 | After Phase 2 | After Phase 3 | After Phase 4 | After Phase 5 |
|--------|--------|---------------|---------------|---------------|---------------|---------------|
| Total Docs | 22 | - | - | - | - | - |
| Archived Docs | 0 | - | - | - | - | - |
| Over Limit (>1000) | 3 | - | - | - | - | - |
| Template Compliant | 6 | - | - | - | - | - |
| V2 References | ~50 | - | - | - | - | - |

---

## 5. Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-29 | Archive ARCHITECTURAL_SHIFTS.md | V3 is first version, no migration history needed |
| 2025-11-29 | Archive REVISION_PLAN.md | Meta-tracking, not architecture content |
| 2025-11-29 | Split DTO_ARCHITECTURE.md | 1423 lines > 1000 limit |

---

## 6. Related Documents

- [DOCUMENTATION_MAINTENANCE.md](../DOCUMENTATION_MAINTENANCE.md) - Maintenance guidelines
- [ARCHITECTURE_TEMPLATE.md](../reference/templates/ARCHITECTURE_TEMPLATE.md) - Template to follow
- [TODO.md](../TODO.md) - Project roadmap (will receive open gaps)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-29 | AI Assistant | Initial plan based on documentation analysis |
