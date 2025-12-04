# SimpleTraderV3 - Implementation TODO

**Status:** LIVING DOCUMENT  
**Last Updated:** 2025-12-04  
**Update Frequency:** Daily (during active development)

---

## Current Focus

Week 1: Configuration Schemas (CRITICAL PATH - blocker for all subsequent work)

> **Quick Status:** 456 tests passing, Week 0 complete, Week 1 in progress

---

## Quick Links

| Document | Purpose |
|----------|---------|
| [IMPLEMENTATION_STATUS.md](implementation/IMPLEMENTATION_STATUS.md) | Quality metrics & test counts |
| [TODO_DOCUMENTATION.md](TODO_DOCUMENTATION.md) | Missing docs & broken links |
| [DOCUMENTATION_MAINTENANCE.md](DOCUMENTATION_MAINTENANCE.md) | Doc organization rules |
| [TODO_COMPLETED.md](archive/TODO_COMPLETED.md) | Archived completed tasks |

**Navigation:**
- **📖 Agent Instructions:** [../agent.md](../agent.md) - AI assistant guide
- **🏛️ Architecture:** [architecture/README.md](architecture/README.md) - System design
- **✨ Coding Standards:** [coding_standards/README.md](coding_standards/README.md) - TDD, quality gates
- **📋 Reference:** [reference/README.md](reference/README.md) - Templates

---

## Summary

| Phase | Done | Total | Status |
|-------|------|-------|--------|
| Week 0: Foundation | 14 | 15 | 🔄 93% (1 DTO pending) |
| Week 1: Config Schemas | 0 | 4 | 🔴 Not started |
| Week 2: Bootstrap | 0 | 3 | 🔴 Blocked |
| Week 3: Factories | 0 | 5 | 🔴 Blocked |
| Week 4: Platform | 0 | 4 | 🔴 Blocked |
| Technical Debt | 1 | 4 | 🔄 25% (3 open) |

---

## 🚀 IMPLEMENTATION ROADMAP

> **For test counts and quality metrics:** See [IMPLEMENTATION_STATUS.md](implementation/IMPLEMENTATION_STATUS.md)

### Week 0: Foundation - ✅ COMPLETE

**Status:** 93% complete (456 tests passing)  
**Archive:** See [TODO_COMPLETED.md](archive/TODO_COMPLETED.md) for details

**Remaining:**
- [ ] **ExecutionRequest DTO** - Payload for EXECUTION_INTENT_REQUESTED event
  - **Purpose:** Aggregated input for ExecutionIntentPlanner
  - **Location:** `backend/dtos/strategy/execution_request.py`

---

## 🔧 Technical Debt

### Open Items

- [ ] **ExecutionGroup: Review `metadata` field usage** (2025-11-27)
  - **Issue:** `metadata: dict[str, Any]` is a code smell
  - **Scope:** `backend/dtos/execution/execution_group.py`
  - **Priority:** Medium

- [ ] **ExecutionDirective: REMOVE iceberg_preference field** (2025-12-02) 🔴 HIGH
  - **Issue:** Violates layer responsibilities (ExecutionPlanner concern, not StrategyPlanner)
  - **Scope:** `backend/dtos/strategy/strategy_directive.py`
  - **Action:** Remove field, verify ExecutionPlan.visibility_preference exists

- [ ] **DTO_ARCHITECTURE.md: Review Discussion Points** (2025-12-04) 🔴 HIGH
  - **Context:** 21 architectural inconsistencies identified
  - **Status:** DISCUSSION REQUIRED
  
  <details>
  <summary>📋 Discussion Points (21 items)</summary>
  
  **ExecutionPlan Semantics (1-2)**
  1. ExecutionPlan output is concrete, not trade-offs
  2. ExecutionCommand definition needs clarification
  
  **Missing DTOs (3)**
  3. Order, Fill, TradePlan missing from DTO Taxonomy
  
  **StrategyDirective Issues (4-9)**
  4. WHY section cleanup (DRY, Routing→Execution, mutability)
  5. Confidence field rationale incorrect
  6. Rejected DTO needed for StrategyPlanner
  7. Enrichment (order_ids) violates SRP
  8. Lifecycle "referenced" is unclear
  9. MODIFY_EXISTING can apply to entry plans
  
  **PlanningAggregator (10-11)**
  10. Terminology still present (happens in BaseExecutionPlanner)
  11. Plan validation responsibility unclear
  
  **Dynamic Exit Logic (12)**
  12. Needs deeper explanation and flow implications
  
  **ExecutionPlan Overhaul (13-16)**
  13. Translation layer description wrong
  14. Field rationales need overhaul
  15. Translation examples table obsolete
  16. Architectural pattern incorrect
  
  **ExecutionCommandBatch (17-18)**
  17. Extra fields origin unclear
  18. DCA still in Execution Strategy Types table
  
  **CausalityChain (19-20)**
  19. Needs rejection variant
  20. Order/Fill IDs don't belong in StrategyJournal
  
  **Missing State DTOs (21)**
  21. TradePlan, Order, Fill need documentation
  
  </details>

---

### Week 1: Configuration Schemas - 🔥 IN PROGRESS (CRITICAL PATH)

**Status:** BLOCKER voor ALLES  
**Location:** `backend/config/schemas/` + `tests/unit/config/`

**Config Schemas (Pydantic models, NOT DTOs):**
- [ ] worker_manifest_schema.py → WorkerManifest, SchemaReference
- [ ] wiring_config_schema.py → EventWiring, WiringConfig
- [ ] strategy_blueprint_schema.py → Workforce, StrategyBlueprint
- [ ] buildspec_schemas.py → WorkerBuildSpec, WiringBuildSpec, StrategyBuildSpec

**Deliverable:** Config schema contracts validated (target: 60+ tests)

---

### Week 2: Bootstrap Components - Config Pipeline

**Dependencies:** Week 1 Config Schemas  
**Location:** `backend/config/`

**Components:**
- [ ] ConfigLoader (YAML → Pydantic models)
- [ ] ConfigValidator (handler validation, params, circular dependencies)
- [ ] ConfigTranslator (Config → BuildSpecs)

**Deliverable:** YAML → BuildSpecs pipeline working (target: 80+ tests)

---

### Week 3: Factories - Assembly Infrastructure

**Dependencies:** Week 1 + Week 2  
**Location:** `backend/assembly/`

**Factories:**
- [ ] PluginRegistry (plugin discovery & loading)
- [ ] WorkerFactory (worker instantiation from BuildSpecs)
- [ ] EventWiringFactory (EventAdapter assembly from BuildSpecs)
- [ ] StrategyFactory (complete strategy orchestration)
- [ ] WorkerMetadataRegistry (runtime registry for manifest metadata)

**Deliverable:** Complete strategy assembly from BuildSpecs (target: 70+ tests)

---

### Week 4: Platform Components - Event Infrastructure

**Dependencies:** Week 3  
**Location:** `backend/core/`

**Components:**
- [ ] EventAdapter (bus-agnostic worker wrapper)
- [ ] FlowCoordinator (run lifecycle orchestration)
- [ ] PlanningAggregator (4-plan coordinator)
- [ ] StrategyCache Runtime Validation (optional)

**Open Design Issues:**
- [ ] **Issue #5: TradePlan in CausalityChain** - How/when included?
- [ ] **Issue #6: ExecutionCommandBatch execution_mode** - Decision algorithm needed
- [ ] **Issue #7: StrategyDirective Architecture Refactor** - Remaining: `position_size` → `target_position_size`

**Deliverable:** Core platform components (target: 70+ tests)

---

### Week 5: Base Workers - Worker Foundation

**Dependencies:** Week 4  
**Location:** `backend/workers/base/`

- [ ] BaseWorker (abstract foundation)
- [ ] ContextWorker, SignalDetector, RiskMonitor
- [ ] StrategyPlanner, PlanningWorker

**Deliverable:** Worker foundation (target: 40+ tests)

---

### Week 6: Orchestration - Execution Flow

**Dependencies:** Week 5  
**Location:** `backend/orchestration/`

- [ ] StrategyRunner (main execution loop)
- [ ] Error handling & edge cases

**Deliverable:** End-to-end tick processing (target: 30+ tests)

---

### Week 7: Integration & Polish - Production Ready

**Dependencies:** Week 6

- [ ] OperationService (strategy lifecycle)
- [ ] End-to-end integration tests
- [ ] Multi-strategy scenarios
- [ ] Error handling

**Deliverable:** Production-ready platform

---

## 📋 Architectural Decisions & Design Notes

> **Complete design docs:** See `docs/development/` and `docs/architecture/`

### Key Decisions

- **Config Schema Naming:** `*_schema.py` files, class names WITHOUT "DTO" suffix
- **Implementation Order:** Config Schemas → Bootstrap → Factories → Platform → Workers
- **Documentation:** TODO.md for tasks, IMPLEMENTATION_STATUS.md for metrics (SRP)

### Design Documents

**Active:**
- [EVENTADAPTER_DESIGN.md](development/EVENTADAPTER_DESIGN.md)
- [CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md](development/CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md)
- [BASEWORKER_DESIGN_PRELIM.md](development/BASEWORKER_DESIGN_PRELIM.md)
- [FLOW_INITIATOR_DESIGN.md](development/backend/core/FLOW_INITIATOR_DESIGN.md) ✅

**Architecture:**
- [LAYERED_ARCHITECTURE.md](architecture/LAYERED_ARCHITECTURE.md)
- [EVENT_DRIVEN_WIRING.md](architecture/EVENT_DRIVEN_WIRING.md)
- [WORKER_TAXONOMY.md](architecture/WORKER_TAXONOMY.md)

---

## 🎯 Next Actions

**Current:** Week 1 - Configuration Schemas

1. Start branch: `feature/config-schemas-week1`
2. TDD: Write 20+ tests first (RED)
3. Implement WorkerManifest + SchemaReference (GREEN)
4. Quality gates: Pylint 10/10

**See:** [TDD_WORKFLOW.md](coding_standards/TDD_WORKFLOW.md)

---

**Last Updated:** 2025-12-04  
**Archive Policy:** Completed items > 7 days → [TODO_COMPLETED.md](archive/TODO_COMPLETED.md)
