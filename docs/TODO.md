# SimpleTraderV3 - TODO List

**Huidige Focus (2025-11-09):** Configuration Schemas (Week 1)
> **Status:** FlowInitiator complete & merged (14/14 tests), CausalityChain enhanced (order_ids/fill_ids added, 28/28 tests), proceeding with Configuration Schemas (Week 1)

## 📚 Documentation Quick Links

- **📖 Agent Instructions:** [../agent.md](../agent.md) - AI assistant guide
- **🏛️ Architecture:** [architecture/README.md](architecture/README.md) - System design
- **✨ Coding Standards:** [coding_standards/README.md](coding_standards/README.md) - TDD, quality gates
- **📋 Reference:** [reference/README.md](reference/README.md) - Templates
- **📊 Implementation:** [implementation/IMPLEMENTATION_STATUS.md](implementation/IMPLEMENTATION_STATUS.md) - **Quality metrics & test counts**
- **🔧 Maintenance:** [DOCUMENTATION_MAINTENANCE.md](DOCUMENTATION_MAINTENANCE.md) - Doc organization

**Archived:** [development/#Archief/](development/#Archief/) - Session handovers, old agent versions

---

## 🚀 IMPLEMENTATIE ROADMAP (Chronologisch)

> **Voor test counts en quality metrics:** Zie [IMPLEMENTATION_STATUS.md](implementation/IMPLEMENTATION_STATUS.md)

### Week 0: Foundation - ✅ COMPLETE

**Data Contracts (DTOs):**
- [x] Shared Layer: DispositionEnvelope, CausalityChain (enhanced with order_ids/fill_ids), PlatformDataDTO
- [x] Signal/Risk Layer: Signal, Risk
- [x] Planning Layer: StrategyDirective, EntryPlan, SizePlan, ExitPlan, ExecutionPlan
- [ ] **ExecutionRequest DTO** - Payload for EXECUTION_INTENT_REQUESTED event
  - **Purpose:** Aggregated input for ExecutionIntentPlanner (3 parallel plans → execution plan)
  - **Fields:** trade_id, strategy_directive, entry_plan, size_plan, exit_plan, causality
  - **Location:** `backend/dtos/strategy/execution_request.py`
  - **Note:** Referenced in PIPELINE_FLOW.md but not yet implemented
- [x] Execution Layer: ExecutionDirective, ExecutionDirectiveBatch, ExecutionGroup

**Interface Protocols:**
- [x] IStrategyCache (protocol + implementation)
- [x] IEventBus (protocol + implementation)
- [x] IWorkerLifecycle (protocol)

**Metrics:** 368 tests passing (100% coverage) - See [IMPLEMENTATION_STATUS.md](implementation/IMPLEMENTATION_STATUS.md)

**Recent:** PlatformDataDTO refactored to minimal design (3 fields: source_type, timestamp, payload)

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
**Location:** `backend/config/` (ConfigLoader, ConfigValidator, ConfigTranslator)

**Components:**
- [ ] ConfigLoader (YAML → Pydantic models)
- [ ] ConfigValidator (handler validation, params, circular dependencies)
- [ ] ConfigTranslator (Config → BuildSpecs)

**Deliverable:** YAML → BuildSpecs pipeline working (target: 80+ tests)

---

### Week 3: Factories - Assembly Infrastructure

**Dependencies:** Week 1 (Schemas) + Week 2 (Bootstrap)  
**Location:** `backend/assembly/` or `backend/config/`

**Factories:**
- [ ] PluginRegistry (plugin discovery & loading)
- [ ] WorkerFactory (worker instantiation from BuildSpecs)
- [ ] EventWiringFactory (EventAdapter assembly from BuildSpecs)
- [ ] StrategyFactory (complete strategy orchestration)
- [ ] **WorkerMetadataRegistry** (runtime registry for manifest metadata)
  - **Purpose:** Enable StrategyCache DTO validation without manifest parsing at runtime
  - **Built during bootstrap:** PluginRegistry → ConfigTranslator → Factory → Registry
  - **Contains:** WorkerMetadata (produces_dtos, requires_dtos, scope) per worker
  - **Usage:** O(1) lookups for runtime validation (defense-in-depth)
  - **Design doc:** `docs/development/backend/core/WORKER_METADATA_REGISTRY_DESIGN.md`

**Deliverable:** Complete strategy assembly from BuildSpecs + runtime metadata registry (target: 70+ tests)

---

### Week 4: Platform Components - Event Infrastructure

**Dependencies:** Week 3 (Factories)  
**Location:** `backend/core/` and platform-specific modules

**Components:**
- [ ] EventAdapter (bus-agnostic worker wrapper)
- [ ] TickCacheManager (run lifecycle orchestration)
- [ ] PlanningAggregator (4-plan coordinator, mode-aware)
  - **Design doc:** `docs/development/backend/core/PLANNING_AGGREGATOR_DESIGN.md`
  - **Purpose:** Multi-input aggregator for Entry/Size/Exit/Execution plans
  - **Pattern:** Fan-in coordination (5 event handlers → 2 output events)
  - **State:** Per-trade tracking matrix with RunAnchor reentry guard
  - **Output:** EXECUTION_INTENT_REQUESTED, EXECUTION_DIRECTIVE_BATCH_READY
- [ ] **StrategyCache Runtime Validation** (optional defense-in-depth)
  - **Purpose:** Validate worker DTO contracts at runtime (catch implementation bugs)
  - **Dependencies:** WorkerMetadataRegistry (Week 3)
  - **Implementation:** Update `set_result_dto()` / `get_required_dtos()` with optional validation
  - **Strategy:** Fail-fast in dev, silent/logging in production
  - **Validation checks:** Worker produces expected DTOs, requests only declared DTOs

**Open Design Issues:**
- [ ] **Issue #5: Trade ID Propagation & Causality** (BLOCKER for PlanningAggregator)
  - **Question:** How to track which plans belong to which trade?
  - **Options:** 
    - A) Embed trade_id in directive_id ("EXE_..._TRD123_...")
    - B) Add trade_id field to ExecutionDirective
    - C) Extend CausalityChain with trade_id field
  - **Related:** How to represent ExecutionDirectiveBatch in CausalityChain?
  - **Decision needed:** Before PlanningAggregator implementation
  - **Note:** CausalityChain currently lacks trade/batch tracking mechanism

**Deliverable:** Core platform components implemented & integrated (target: 70+ tests)

---

### Week 5: Base Workers - Worker Foundation

**Dependencies:** Week 4 (Platform Components)  
**Location:** `backend/workers/base/`

**Workers:**
- [ ] BaseWorker (abstract foundation, IWorkerLifecycle implementation)
- [ ] ContextWorker, SignalDetector, RiskMonitor
- [ ] StrategyPlanner, PlanningWorker (Entry/Size/Exit/Execution)

**Deliverable:** Worker foundation with DispositionEnvelope integration (target: 40+ tests)

---

### Week 6: Orchestration - Execution Flow

**Dependencies:** Week 5 (Base Workers)  
**Location:** `backend/orchestration/` or `backend/core/`

**Components:**
- [ ] StrategyRunner (main execution loop, tick processing)

**Deliverable:** End-to-end tick processing working (target: 30+ tests)

---

### Week 7: Integration & Polish - Production Ready

**Dependencies:** Week 6 (Orchestration)

**Components:**
- [ ] OperationService (strategy lifecycle management)
- [ ] End-to-end integration tests (YAML → Execution → Results)
- [ ] Multi-strategy scenarios
- [ ] Error handling & edge cases

**Deliverable:** Production-ready platform, full bootstrap from YAML to execution

---

## 📋 Architectural Decisions & Design Notes

> **Voor complete design docs:** Zie `docs/development/` en `docs/architecture/`

### Key Decisions

**Config Schema Naming (2025-10-30):**
- ✅ `*_schema.py` files (NOT `*_dto.py`)
- ✅ Class names WITHOUT "DTO" suffix (WorkerManifest, not WorkerManifestDTO)
- ✅ Rationale: Config schemas are validation contracts, not runtime data DTOs
- ✅ Location: `backend/config/schemas/`

**Implementation Order (2025-10-30):**
- Config Schemas FIRST (Week 1) - critical blocker for everything
- Bootstrap & Factories depend on schemas
- Platform Components depend on Factories (EventWiringFactory needs BuildSpecs)
- Workers depend on Platform Components

**Documentation Responsibility (2025-10-30):**
- TODO.md: Task status, checkboxes, chronological roadmap (THIS FILE)
- IMPLEMENTATION_STATUS.md: Quality metrics, test counts, coverage stats (SRP)

### Design Documents

**Active Designs:**
- [EVENTADAPTER_DESIGN.md](development/EVENTADAPTER_DESIGN.md) - EventAdapter architecture
- [CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md](development/CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md) - Config pipeline
- [BASEWORKER_DESIGN_PRELIM.md](development/BASEWORKER_DESIGN_PRELIM.md) - Worker foundation
- [DATA_PROVIDER_DESIGN.md](development/backend/core/DATA_PROVIDER_DESIGN.md) - DataProvider architecture
- [FLOW_INITIATOR_DESIGN.md](development/backend/core/FLOW_INITIATOR_DESIGN.md) - FlowInitiator implementation
- **[WORKER_METADATA_REGISTRY_DESIGN.md](development/backend/core/WORKER_METADATA_REGISTRY_DESIGN.md)** - Runtime metadata registry (PENDING)

**Architecture Guides:**
- [LAYERED_ARCHITECTURE.md](architecture/LAYERED_ARCHITECTURE.md) - System layers
- [EVENT_DRIVEN_WIRING.md](architecture/EVENT_DRIVEN_WIRING.md) - Event orchestration
- [PLUGIN_ANATOMY.md](architecture/PLUGIN_ANATOMY.md) - Plugin structure
- [WORKER_TAXONOMY.md](architecture/WORKER_TAXONOMY.md) - Worker types & responsibilities

---

## 🎯 Next Actions

**Current Week:** Week 1 - Configuration Schemas

**Next Task:** Implement `worker_manifest_schema.py`
- Start feature branch: `feature/config-schemas-week1`
- TDD: Write 20+ tests first (RED phase)
- Implement WorkerManifest + SchemaReference (GREEN phase)
- Quality gates: Pylint 10/10, all tests passing
- See: [TDD_WORKFLOW.md](coding_standards/TDD_WORKFLOW.md)

**After Week 1:** ConfigLoader, ConfigValidator, ConfigTranslator (Week 2)

---

**Last Updated:** 2025-10-30  
**Maintained By:** Development Team  
**Review Frequency:** Weekly
