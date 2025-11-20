# SimpleTraderV3 - TODO List

**Huidige Focus (2025-11-09):** Origin DTO Integration Complete ✅
> **Status:** Origin DTO (16 tests), PlatformDataDTO Origin integration (19 tests), CausalityChain Origin integration (33 tests) - All complete. Ready for next phase.

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
- [x] Shared Layer: DispositionEnvelope, CausalityChain (Origin integration complete), PlatformDataDTO (Origin integration complete), Origin (NEW - type-safe origin tracking)
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

**Platform Components:**
- [x] FlowInitiator - Per-strategy data ingestion and cache initialization (Phase 1.3)
  - **Implementation:** `backend/core/flow_initiator.py`
  - **Tests:** 14/14 passing (100% coverage)
  - **Quality:** Pylint 10/10
  - **Design:** [FLOW_INITIATOR_DESIGN.md](development/backend/core/FLOW_INITIATOR_DESIGN.md)
  - **Purpose:** Initialize StrategyCache before workers execute (race condition prevention)

**Metrics:** 395 tests passing (100% coverage) - See [IMPLEMENTATION_STATUS.md](implementation/IMPLEMENTATION_STATUS.md)

**Recent (2025-11-20):**
- **TradePlan DTO**: Implemented `TradePlan` (Execution Anchor) with `TPL_` prefix.
- **TradeStatus Enum**: Added `ACTIVE`/`CLOSED` status.
- **Quality**: 100% test coverage, 10/10 pylint.

**Recent (2025-11-09):**
- **Origin DTO complete** (16/16 tests) - Type-safe platform data origin tracking (TICK/NEWS/SCHEDULE)
- **PlatformDataDTO Origin integration** (19/19 tests, +5 tests) - Replaced source_type with origin field
- **CausalityChain Origin integration** (33/33 tests, +5 tests) - Replaced tick_id/news_id/schedule_id with origin field
- **Breaking changes:** PlatformDataDTO and CausalityChain consumers need updates
- CausalityChain execution tracking (order_ids/fill_ids) complete
- FlowInitiator implementation complete
- PlatformDataDTO refactored to minimal design (3 fields)

**Technical Debt:**
- [ ] **Signal DTO: Remove causality field** (2025-11-09)
  - **Issue:** Signal currently has causality field, but CausalityChain should only start at StrategyPlanner decision
  - **Rationale:** SignalDetector emits pure detection facts (pre-causality). StrategyPlanner creates first causal link (signal_id → strategy_directive_id)
  - **Impact:** BREAKING CHANGE - affects Signal constructor, all tests, SignalDetector implementations
  - **Scope:** backend/dtos/strategy/signal.py, tests/unit/dtos/strategy/test_signal.py, all SignalDetector plugins
  - **Priority:** High (architectural correctness - causality timing semantics)
  - **Documentation:** DTO_ARCHITECTURE.md already updated (Signal is pre-causality)

- [ ] **Risk DTO: Remove causality field** (2025-11-09)
  - **Issue:** Risk currently has causality field, but CausalityChain should only start at StrategyPlanner decision
  - **Rationale:** RiskMonitor emits pure detection facts (pre-causality). StrategyPlanner creates first causal link (risk_id → strategy_directive_id)
  - **Impact:** BREAKING CHANGE - affects Risk constructor, all tests, RiskMonitor implementations
  - **Scope:** backend/dtos/strategy/risk.py, tests/unit/dtos/strategy/test_risk.py, all RiskMonitor plugins
  - **Priority:** High (architectural correctness - causality timing semantics)
  - **Documentation:** DTO_ARCHITECTURE.md already updated (Risk is pre-causality)

- [ ] **Symbol field naming consistency** (2025-11-09)
  - **Issue:** Inconsistent naming across DTOs (asset vs affected_asset vs symbol)
  - **Solution:** Standardize on `symbol` (trading domain standard)
    - Signal: `asset` → `symbol`
    - Risk: `affected_asset` → `affected_symbol` (None = system-wide)
    - StrategyDirective.EntryDirective: `symbol` (already correct)
  - **Impact:** BREAKING CHANGE - affects Signal, Risk field names + all tests
  - **Scope:** backend/dtos/strategy/signal.py, backend/dtos/strategy/risk.py, all tests
  - **Priority:** High (consistency, before production)
  - **Documentation:** DTO_ARCHITECTURE.md will be updated

- [ ] **DirectiveScope: Align terminology with order-level operations** (2025-11-09)
  - **Issue:** MODIFY_EXISTING/CLOSE_EXISTING suggest position-level, but operations are order-level
  - **Solution:** Rename enum values to reflect order-level semantics:
    - `NEW_TRADE` → keep (correct - new position from signal)
    - `MODIFY_EXISTING` → `MODIFY_ORDER` (order-level adjustment)
    - `CLOSE_EXISTING` → `CLOSE_ORDER` (order-level closure)
  - **Impact:** BREAKING CHANGE - affects DirectiveScope enum, StrategyDirective validation, all StrategyPlanner implementations
  - **Scope:** backend/dtos/strategy/strategy_directive.py, tests, all StrategyPlanner plugins
  - **Priority:** High (terminological correctness)
  - **Documentation:** DTO_ARCHITECTURE.md will be updated

- [ ] **StrategyDirective: target_trade_ids → target_order_ids** (2025-11-09)
  - **Issue:** Field name uses "trade" but tracks order IDs (terminological confusion)
  - **Solution:** Rename `target_trade_ids` → `target_order_ids`
  - **Impact:** BREAKING CHANGE - affects StrategyDirective field name, validation logic, all consumers
  - **Scope:** backend/dtos/strategy/strategy_directive.py, tests, StrategyPlanner/PlanningWorker implementations
  - **Priority:** High (follows DirectiveScope terminology alignment)
  - **Documentation:** DTO_ARCHITECTURE.md will be updated

- [ ] **StrategyDirective sub-directive: ExecutionDirective → RoutingDirective** (2025-11-09)
  - **Issue:** TWO classes named `ExecutionDirective` (naming conflict):
    1. `backend/dtos/strategy/strategy_directive.py` line 164 - Sub-directive (routing constraints for RoutingPlanner)
    2. `backend/dtos/execution/execution_directive.py` line 36 - Execution layer DTO (aggregated final instruction)
  - **Solution:** Rename strategy sub-directive class `ExecutionDirective` → `RoutingDirective`
    - Field name `routing_directive` already correct (no change)
    - Class docstring/descriptions: "Execution constraints" → "Routing constraints"
  - **Impact:** BREAKING CHANGE - affects class name, imports, all StrategyPlanner implementations that create this sub-directive
  - **Scope:** backend/dtos/strategy/strategy_directive.py (class rename line 164), all imports, tests
  - **Priority:** High (naming conflict resolution, clarity)
  - **Documentation:** DTO_ARCHITECTURE.md already updated (uses RoutingDirective)

- [ ] **Asset format: BASE/QUOTE → BASE_QUOTE** (2025-11-09)
  - **Issue:** Current BASE/QUOTE format with slash is problematic in filesystem paths, URLs, logs, database keys
  - **Solution:** Change to BASE_QUOTE with underscore separator (e.g., BTC_USD instead of BTC/USD)
  - **Impact:** BREAKING CHANGE - affects Signal, Risk, StrategyDirective validation + all tests
  - **Scope:** All DTOs with symbol field, validation patterns, test fixtures
  - **Priority:** High (before production - filesystem safety)
  - **Documentation:** DTO_ARCHITECTURE.md already updated (BASE_QUOTE format)

- [ ] **Enums Centralisatie** (2025-11-09)
  - **Issue:** Enums currently embedded in DTOs (e.g., OriginType in origin.py, DirectiveScope in strategy_directive.py)
  - **Impact:** Hard to discover all enums, tight coupling, difficult to add new implementations
  - **Solution:** Move all enums to `backend/core/enums.py` (centralized registry)
  - **Benefits:** Single source of truth, easy discovery, loose coupling, no DTO diving needed
  - **Scope:** OriginType, DirectiveScope, ExecutionMode, DispositionType, and all future enums
  - **Priority:** Medium (before Week 1 Config Schemas - config may reference enums)

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

- [ ] **Issue #6: ExecutionDirectiveBatch execution_mode Decision Logic** (2025-11-09)
  - **Problem:** PlanningAggregator currently hardcodes execution_mode=ATOMIC for ALL batches (SRP violation)
  - **Current State:** 
    - PlanningAggregator sets execution_mode, timeout_seconds, rollback_on_failure with hardcoded defaults
    - StrategyDirective contains execution signals (scope, confidence, routing_directive.execution_urgency)
    - No documented algorithm for WHEN to use SEQUENTIAL vs PARALLEL vs ATOMIC
  - **Field Duplication Issue:**
    - ExecutionPlan.max_execution_window_minutes (per-directive, from RoutingPlanner)
    - ExecutionDirectiveBatch.timeout_seconds (batch-level, from PlanningAggregator)
    - Potential conflict: directive wants 60min, batch allows 30s
  - **Use Cases Identified (from DTO examples):**
    - ATOMIC: Flash crash emergency exit (scope=CLOSE_EXISTING, urgency=1.0, rollback=True)
    - SEQUENTIAL: Hedged exit with ordering (close hedge FIRST, then main position, count=2)
    - PARALLEL: Bulk order modifications (scope=MODIFY_EXISTING, independent operations, best-effort)
  - **Research Questions:**
    1. WHO determines execution_mode? (StrategyPlanner vs PlanningAggregator vs derived from inputs)
    2. WHEN to use each mode? (document decision algorithm/triggers)
    3. Should StrategyDirective have execution_policy field? (batch coordination strategy)
    4. Field ownership: Keep both timeouts or consolidate? (relationship between plan and batch timeouts)
  - **Potential Solution:** Derive execution_mode from StrategyDirective fields:
    - `scope` (NEW_TRADE / MODIFY_EXISTING / CLOSE_EXISTING)
    - `confidence` [0.0-1.0]
    - `routing_directive.execution_urgency` [0.0-1.0]
    - Directive count (1 vs multiple)
  - **Impact:** Affects PlanningAggregator implementation, ExecutionDirectiveBatch field rationale
  - **Priority:** High (architectural correctness - SRP, field ownership clarity)
  - **Related Docs:** 
    - `docs/architecture/DTO_ARCHITECTURE.md` (ExecutionDirectiveBatch documentation)
    - `docs/development/backend/core/PLANNING_AGGREGATOR_DESIGN.md` (line 389: hardcoded defaults)
  - **Next Steps:** Research and document decision algorithm before PlanningAggregator implementation

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
- [ ] Error handling & edge cases

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
- [FLOW_INITIATOR_DESIGN.md](development/backend/core/FLOW_INITIATOR_DESIGN.md) - ✅ FlowInitiator implementation (Phase 1.3 Complete)
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

**Last Updated:** 2025-11-09  
**Maintained By:** Development Team  
**Review Frequency:** Weekly
