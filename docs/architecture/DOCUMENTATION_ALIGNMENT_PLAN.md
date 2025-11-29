# Documentation Alignment Plan

**Status:** COMPLETE
**Version:** 1.2
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
| `ASYNC_IO_ARCHITECTURE.md` | 997 | ⚠️ | NL doc, pre-design - **SPECIAL TREATMENT** |
| `CONFIGURATION_LAYERS.md` | 416 | ❌ | Pre-template (2025-10-29) |
| `CORE_PRINCIPLES.md` | 222 | ❌ | Pre-template, minor update |
| `DATA_FLOW.md` | 496 | ❌ | Pre-template, TickCache terminology |
| `DTO_ARCHITECTURE.md` | 1423 | ❌ | **Over limit** - DEDICATED PHASE |
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
| Special Cases | `ASYNC_IO_ARCHITECTURE.md` | NL language, pre-design status |
| DTO Technical Debt | `DTO_ARCHITECTURE.md` | Content out of sync with TODO.md items |

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

### Phase 3: ASYNC_IO_ARCHITECTURE.md - Special Treatment
**Goal:** Relocate pre-design document and translate to English
**Effort:** 1-2 hours
**Commit:** Single commit

**Issues:**
1. Written in Dutch (violates DOCUMENTATION_MAINTENANCE.md language rule)
2. Status is "Design" but content is preliminary/exploratory
3. Not yet validated architecture

| Task | Action |
|------|--------|
| 3.1 | Evaluate content - is this validated architecture or exploration? |
| 3.2 | If exploration → Move to `docs/development/ASYNC_IO_DESIGN.md` |
| 3.3 | If architecture → Translate to English, apply template |
| 3.4 | Update any cross-references |

**Completion Criteria:**
- [ ] Document in correct location (architecture/ or development/)
- [ ] Content in English
- [ ] Status reflects actual maturity

---

### Phase 4: EVENT_ARCHITECTURE.md Revision
**Goal:** Split by concern, not just size
**Effort:** 2-3 hours
**Commit:** Single commit

**Current Issues:**
1. 1163 lines - over limit
2. Mixes conceptual architecture with implementation details
3. Contains both "what/why" and "how" content

**Analysis of Current Sections:**
| Section | Lines (est) | Type | Destination |
|---------|-------------|------|-------------|
| Executive Summary | 20 | Architecture | EVENT_ARCHITECTURE.md |
| Event Producers/Consumers (A-F) | 300 | Architecture | EVENT_ARCHITECTURE.md |
| Event Scoping & Naming | 100 | Architecture | EVENT_ARCHITECTURE.md |
| Design Principles | 80 | Architecture | EVENT_ARCHITECTURE.md |
| EventStore Design | 150 | Implementation | EVENT_PERSISTENCE.md |
| EventQueue Design | 100 | Implementation | EVENT_PERSISTENCE.md |
| Delivery Guarantees | 80 | Implementation | EVENT_PERSISTENCE.md |
| Recovery Mechanism | 60 | Implementation | EVENT_PERSISTENCE.md |
| Dead Letter Queue | 80 | Implementation | EVENT_PERSISTENCE.md |
| Event Adapter Mapping | 80 | Reference | Move to PLATFORM_COMPONENTS.md or separate |
| Event Versioning | 100 | Implementation | EVENT_PERSISTENCE.md or DTO docs |
| Testing Strategy | 80 | Implementation | Remove (belongs in code/tests) |
| Implementation Components | 60 | Roadmap | Remove (belongs in TODO.md) |

**Proposed Split:**

| New Document | Purpose | Content | Lines (est) |
|--------------|---------|---------|-------------|
| `EVENT_ARCHITECTURE.md` | Conceptual model | Scoping, naming, producers/consumers, design principles | ~500 |
| `EVENT_PERSISTENCE.md` | Durability layer | EventStore, EventQueue, recovery, DLQ, delivery guarantees, versioning | ~450 |

**What to Remove/Relocate:**
- Testing Strategy → Remove (tests document themselves)
- Implementation Components → TODO.md (roadmap, not architecture)
- Event Adapter Mapping table → PLATFORM_COMPONENTS.md (component reference)

**Completion Criteria:**
- [ ] Both docs under 1000 lines
- [ ] Clear separation: architecture vs implementation
- [ ] No duplicate content
- [ ] Proper cross-references
- [ ] Template compliance (English, headers, version history)

---

### Phase 5: DTO Architecture Revision
**Goal:** Comprehensive DTO documentation aligned with TODO.md technical debt
**Effort:** 3-4 hours (dedicated attention)
**Commit:** Single commit
**Dependencies:** Aligns with Week 0 Technical Debt items in TODO.md

**Context:**
The DTO documentation has significant technical debt that must be addressed alongside code changes. This phase synchronizes documentation with the planned DTO refactoring from TODO.md.

**TODO.md Technical Debt Items (DTO-related):**
| Item | Status | Impact on Docs |
|------|--------|----------------|
| Signal DTO: Remove causality field | Pending | Update Signal section |
| Risk DTO: Remove causality field | Pending | Update Risk section |
| Symbol field naming consistency | Pending | Update all DTOs with symbol fields |
| DirectiveScope terminology | Rejected | Document rejection rationale |
| StrategyDirective: target_trade_ids → target_plan_ids | Pending | Update StrategyDirective section |
| ExecutionGroup: metadata field review | Pending | Update ExecutionGroup section |
| ExecutionStrategyType: Remove DCA | Pending | Update enum documentation |
| ExecutionDirective → RoutingDirective rename | Pending | Update naming throughout |
| Asset format: BASE/QUOTE → BASE_QUOTE | Pending | Update validation patterns |

**Approach:**
1. **Review current DTO_ARCHITECTURE.md** against TODO.md items
2. **Split by pipeline phase** (aligns with PIPELINE_FLOW.md):
   - Core DTOs (Origin, RunAnchor, CausalityChain)
   - Context & Detection DTOs (PlatformDataDTO, Signal, Risk)
   - Planning DTOs (StrategyDirective, Plans)
   - Execution DTOs (TradePlan, ExecutionGroup, ExecutionDirective)
3. **Apply pending terminology changes** where documentation leads code
4. **Mark "PENDING CODE CHANGE"** for items awaiting implementation

| New Document | Content | Lines (est) |
|--------------|---------|-------------|
| `DTO_ARCHITECTURE.md` | Index, design principles, DTO categories | ~200 |
| `DTO_CORE.md` | Origin, RunAnchor, CausalityChain, DispositionEnvelope | ~300 |
| `DTO_PIPELINE.md` | PlatformDataDTO, Signal, Risk, StrategyDirective, Plans | ~400 |
| `DTO_EXECUTION.md` | TradePlan, ExecutionGroup, ExecutionDirective, Order, Fill | ~400 |

**Completion Criteria:**
- [ ] All DTO docs under 1000 lines
- [ ] Each TODO.md item reflected in documentation (or marked PENDING)
- [ ] Consistent terminology (symbol, RoutingDirective, target_plan_ids)
- [ ] Cross-references to TODO.md for pending changes
- [ ] Aligned with PIPELINE_FLOW.md phase structure

---

### Phase 6: Template Compliance
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

### Phase 7: README & Navigation Update
**Goal:** Clean navigation reflecting new structure
**Effort:** 1 hour
**Commit:** Single commit

| Task | Action |
|------|--------|
| 7.1 | Update "Quick Start" reading order (no V2 references) |
| 7.2 | Update document tables with new/split docs |
| 7.3 | Update "Critical Path for New Developers" |
| 7.4 | Remove "Key Design Choices" V2 references |
| 7.5 | Verify all links work |

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
| Phase 1: Archive Migration Docs | ✅ Complete | 2025-11-29 | 2025-11-29 | 7a73b40 |
| Phase 2: Triage ARCHITECTURE_GAPS | ✅ Complete | 2025-11-29 | 2025-11-29 | b03574a |
| Phase 3: ASYNC_IO Special Treatment | ✅ Complete | 2025-11-29 | 2025-11-29 | f259aef |
| Phase 4: EVENT_ARCHITECTURE Split | ✅ Complete | 2025-11-29 | 2025-11-29 | d02bc47 |
| Phase 5: DTO Architecture Revision | ✅ Complete | 2025-11-29 | 2025-11-29 | 3f30aad |
| Phase 6: Template Compliance | ✅ Complete | 2025-11-29 | 2025-11-29 | f93cc4c |
| Phase 7: README Update | ✅ Complete | 2025-11-29 | 2025-11-29 | TBD |

### Metrics

| Metric | Before | P1 | P2 | P3 | P4 | P5 | P6 | P7 |
|--------|--------|----|----|----|----|----|----|----| 
| Total Docs | 22 | 20 | 19 | 18 | 19 | 22 | 22 | 22 |
| Archived Docs | 0 | 2 | 3 | 3 | 3 | 3 | 3 | 3 |
| Over Limit (>1000) | 3 | 3 | 2 | 2 | 1 | 0 | 0 | 0 |
| Template Compliant | 6 | 6 | 6 | 6 | 8 | 12 | 20 | 22 |
| V2 References | ~50 | ~10 | ~10 | ~10 | ~10 | ~10 | ~5 | 0 |

---

## 5. Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-29 | Archive ARCHITECTURAL_SHIFTS.md | V3 is first version, no migration history needed |
| 2025-11-29 | Archive REVISION_PLAN.md | Meta-tracking, not architecture content |
| 2025-11-29 | Archive ARCHITECTURE_GAPS.md | GAP-001/002 resolved, GAP-003-012 already in TODO.md as Open Design Issues |
| 2025-11-29 | ASYNC_IO_ARCHITECTURE.md special treatment | NL language + pre-design status requires evaluation |
| 2025-11-29 | DTO Architecture as dedicated phase | Significant technical debt, align with TODO.md items |
| 2025-11-29 | Split by pipeline phase | Aligns DTO docs with PIPELINE_FLOW.md structure |
| 2025-11-29 | Move ASYNC_IO to development/ | Document is Status=Design (pre-architecture), in Dutch, exploratory content - not validated architecture |
| 2025-11-29 | Split EVENT_ARCHITECTURE by concern | 1163 lines split into: EVENT_ARCHITECTURE.md (conceptual ~480 lines) + EVENT_PERSISTENCE.md (durability ~420 lines), translated to English |
| 2025-11-29 | Split DTO_ARCHITECTURE by pipeline | 1424 lines split into: DTO_ARCHITECTURE.md (index ~200), DTO_CORE.md (~200), DTO_PIPELINE.md (~280), DTO_EXECUTION.md (~340) |
| 2025-11-29 | Phase 6 Template Compliance | Translated CORE_PRINCIPLES.md to English, added headers to POINT_IN_TIME_MODEL.md, moved LOGENRICHER_DESIGN.md to development/, all pre-template docs now have Status/Last Updated |
| 2025-11-29 | Phase 7 README Update | Fixed TickCache→StrategyCache terminology, updated worker count to 6, removed remaining V2 references, verified all links |

---

## 6. Related Documents

- [DOCUMENTATION_MAINTENANCE.md](../DOCUMENTATION_MAINTENANCE.md) - Maintenance guidelines
- [ARCHITECTURE_TEMPLATE.md](../reference/templates/ARCHITECTURE_TEMPLATE.md) - Template to follow
- [TODO.md](../TODO.md) - Project roadmap (DTO technical debt items)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-29 | AI Assistant | Initial plan based on documentation analysis |
| 1.1 | 2025-11-29 | AI Assistant | ASYNC_IO special treatment, DTO dedicated phase with TODO.md alignment |
